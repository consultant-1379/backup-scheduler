#!/usr/bin/env python
##############################################################################
# COPYRIGHT Ericsson AB 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

""" Module contains classes to orchestrate backup"""

import logging
import os
import time

# pylint: disable=relative-import
from backup_utils import cmd, get_keystone_env, ping, check_private_key, \
     get_key_names_from_stack, get_private_key, create_temp_key_file, get_time
from workflows import WfInstances, log_wf
# pylint: enable=relative-import

SCRIPT_NAME = os.path.basename(__file__)
LOG = logging.getLogger(SCRIPT_NAME)


class BackupStages(object):  # pylint: disable=too-many-instance-attributes
    """ Class to encapsulate running different stages
        of the ENM BUR Backup Sequence.
    """
    def __init__(self):
        self.lcm = None
        self.max_delay = None
        self.max_time = None
        self.max_validation_time = None
        self.bkup_script = None
        self.metadata_script = None
        self.tenancies = []
        self.deployment_id = None
        self.tag = None
        self.enm_key = None
        self.keystone = None
        self.nfs = None
        self.nfs_user = None
        self.nfs_key = None
        self.nfs_path = None
        self.skip_all_check = None
        self.fail_long_backup = None
        self.retention = None
        self.log = None
        self.mail_fn = None
        self.backup_id = None
        self.blocking_wfs = None

    def _get_backup_tag(self):
        now = get_time().strftime('__%Y%m%d_%H%M')

        # get ENM and ISO version
        path = 'enm/deployment/enm_version'
        consul_cmd = 'consul kv get {}'.format(path)
        opt = ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
        ssh = 'ssh -i {} {} cloud-user@{} '.format(self.enm_key, opt, self.lcm)

        self.log.info("Getting ENM version from consul")
        result, stdout, _ = cmd(ssh + consul_cmd)

        tag = self.deployment_id + '_' + 'unknown_enm_version' + now

        if result == 0:
            try:
                outlist = stdout.split()
                enm = outlist[1]
                iso = outlist[4][:-1]
                tag = self.deployment_id + '_' + enm + '_iso_' + iso + now
                tag = tag.replace('.', '_')
            except IndexError:
                self.log.warning("Failed to extract ENM version from output")

        else:
            self.log.warning("Failed to get ENM version from consul")

        return tag

    def _send_fail_mail(self, message, warning=False):
        if warning:
            sub = "Backup warning: " + self.deployment_id
        else:
            sub = "Backup failure: " + self.deployment_id

        if self.lcm and self.backup_id:
            url = ("http://{}/index.html#workflows/workflow/"
                   "enmdeploymentworkflows.--.Backup%20Deployment/"
                   "workflowinstance/{}".format(self.lcm, self.backup_id))
        else:
            url = None

        message = "{}\n" \
                  "Customer: {}\n" \
                  "Tag:      {}\n" \
                  "ID:       {}\n" \
                  "WF URL:   {}".format(message,
                                        self.deployment_id,
                                        self.tag,
                                        self.backup_id,
                                        url)

        if self.mail_fn:
            return self.mail_fn(sub, message)  # pylint: disable=not-callable
        return True

    def _get_backup_wf(self):
        if not self.backup_id:
            self.log.error("No backup ID to check backup state")
            return None

        wfs = WfInstances(self.lcm, self.log)
        if not wfs.get_wfs_from_lcm():
            self.log.error("Failed to retrieve workflows from LCM")
            return None

        backup = wfs.get_wf_by_id(self.backup_id)
        if not backup:
            self.log.error("Backup not found")
            return None

        self.log.info("Backup workflow found")
        log_wf(backup, self.log)
        return backup

    def _wf_has_problem(self, wflow):
        if wflow[WfInstances.INCIDENT]:
            self.log.error("Workflow has an incident")
            return True

        if wflow[WfInstances.ABORTED]:
            self.log.error("Workflow has been aborted")
            return True

        self.log.info("Workflow has no problem")
        return False

    def _transfer_to_nfs(self, filename, dest):
        opts = ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
        scp = "scp -i %s %s %s %s@%s:%s " % (self.nfs_key,
                                             opts,
                                             filename,
                                             self.nfs_user,
                                             self.nfs,
                                             dest)
        return cmd(scp)

    def _wf_counts_ok(self, bkp=0, inst=0, rest=0, rbk=0, upg=0):
        wf_count = {'backup': bkp,
                    'install': inst,
                    'restore': rest,
                    'rollback': rbk,
                    'upgrade': upg}

        if not any(v > 0 for v in wf_count.itervalues()):
            self.log.info('No workflows running')
            return True

        self.log.info('Workflows running, checking against rules')
        for rule in self.blocking_wfs.split(','):
            count, wfs = rule.split(':')
            count = int(count)
            total = 0
            self.log.info('Checking workflow count against rule %s', rule)

            for wflow in wfs.split('|'):
                total += wf_count[wflow]
            if total >= count:
                self.log.info('%s %s workflows running.  Max allowed is %s',
                              total, wfs, count)
                return False
        self.log.info("Running workflows are not a problem, ok to continue")
        return True

    def setup_private_key(self):
        """Checks for existing private key for tenancy, if it doesn't exist
           or doesn't work then get key from OpenStack and test it.
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: False if no valid key can be used, True if key is ok

        Raises: Nothing (hopefully!)
        """

        if not ping(self.lcm):
            fail_msg = 'cannot contact the VNF-LCM, backup cannot start'
            self.log.error(fail_msg)
            self._send_fail_mail(fail_msg)
            return False

        if check_private_key('cloud-user', self.enm_key, self.lcm):
            self.log.info("Current key %s is good", self.enm_key)
            return True

        self.log.info("Need to retrieve key from OpenStack")

        keystone_env = get_keystone_env(self.keystone)
        if not keystone_env:
            self.log.error("Unable to get keystone rc information")
            return False

        key_names = get_key_names_from_stack(keystone_env)
        if not key_names:
            self.log.error("Failed to get key names from stack")

        for key_name in key_names:
            key_contents = get_private_key(key_name, keystone_env)
            if not key_contents:
                self.log.warning("Could not get private key from %s", key_name)
                continue

            self.log.info("Trying key %s", key_name)
            temp_key = create_temp_key_file(key_contents)
            if not temp_key:
                self.log.error("Failed to create temporary key file")
                continue

            if not check_private_key('cloud-user', temp_key.name, self.lcm):
                self.log.warning("Key %s does not work", temp_key.name)
                continue

            self.log.info("Key %s is good", key_name)

            ret, _, _ = cmd('cp -f %s %s' % (temp_key.name, self.enm_key))
            if ret != 0:
                self.log.warning("Failed to copy key to %s", self.enm_key)
                continue

            self.log.info("Key createed successfully")
            return True

        msg = "Failed to get valid private key, backup cannot start"
        self.log.error(msg)
        self._send_fail_mail(msg)
        return False

    def no_banned_wfs(self):
        """Check for running workflows that are storage intensive all tenancies
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: False if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """

        self.log.info("Stage >>> Check for Workflows on all tenancies")
        bkups = 0
        restrs = 0
        rbacks = 0
        upgrds = 0
        insts = 0

        for customer in self.tenancies:
            lcm = self.tenancies[customer]

            wfs = WfInstances(lcm, self.log)
            wfs.get_wfs_from_lcm()

            active = wfs.active_storage_wfs()
            if not active:
                self.log.info('%s has no workflows running', customer)
                continue

            self.log.info('%s has workflows running:', customer)
            for wflow in active:
                log_wf(wflow, self.log)

            if wfs.get_wf_by_type(WfInstances.BACKUP):
                bkups += 1
            elif wfs.get_wf_by_type(WfInstances.RESTORE):
                restrs += 1
            elif wfs.get_wf_by_type(WfInstances.INSTALL):
                insts += 1
            elif wfs.get_wf_by_type(WfInstances.UPGRADE):
                upgrds += 1
            elif wfs.get_wf_by_type(WfInstances.ROLLBACK):
                rbacks += 1

        if self._wf_counts_ok(bkups, insts, restrs, rbacks, upgrds):
            return True

        self.log.warning("Prohibited workflows are running, cannot proceed")
        return False

    def no_wfs(self):
        """Check for any workflows running on 'this' tenancy
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: False if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> Check for any workflows on %s" % self.lcm)
        deployment_quiet = True
        wfs = WfInstances(self.lcm, self.log)
        if wfs.get_wfs_from_lcm():
            active_wfs = wfs.active_wfs()

            if active_wfs:
                deployment_quiet = False
                self.log.info("There are workflows running:")

                for wflow in active_wfs:
                    log_wf(wflow, self.log)
            else:
                self.log.info("No active workflows")
        else:
            deployment_quiet = None
            self.log.warning("Failed to retrieve workflows")
        return deployment_quiet

    def set_retention(self):
        """Sets backup retention
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> Set retention")
        path = 'enm/applications/bur/services/backup/retention_value'
        consul_cmd = 'consul kv put %s %s' % (path, self.retention)
        opts = ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
        ssh = 'ssh -i %s %s cloud-user@%s ' % (self.enm_key, opts, self.lcm)
        result, _, _ = cmd(ssh + consul_cmd)

        if result != 0:
            self.log.error("Failed to set retention")
            msg = "Failed to set consul retention value on " + self.lcm
            self._send_fail_mail(msg)
            return False
        return True

    def start_backup(self):
        """Check for any workflows running on 'this' tenancy
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """

        if not self.tag:
            self.tag = self._get_backup_tag()

        self.log.info("Stage >>> start backup")
        backup_args = " --lcm=%s --tag=%s --stdout" % (self.lcm, self.tag)
        result, stdout, _ = cmd(self.bkup_script + backup_args)

        for line in stdout.split("\n"):
            if "Backup workflow requested with" in line:
                word_list = line.split()
                # get last word in list and remove last character '.'
                self.backup_id = word_list[-1][:-1]
                break

        if not self.backup_id:
            self.log.error("Failed to get backup id, assuming no backup")
            return False, "ID: None  TAG: %s" % self.tag

        info = "ID: %s  TAG: %s" % (self.backup_id, self.tag)
        if result == 0:
            msg = "Backup started with tag %s and id %s" % (
                self.tag, self.backup_id)

            self.log.info(msg)
            return True, info

        self.log.error("Starting backup failed")
        msg = "Failed to start backup on " + self.lcm
        self._send_fail_mail(msg)

        return False, info

    def is_backup_running(self):
        """Check if backup is running
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if backup is running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> Is Backup Running")
        backup = self._get_backup_wf()

        if not backup:
            self.log.error("Failed to find backup")
            return None

        if self._wf_has_problem(backup):
            self.log.error("Backup has a problem")
            log_wf(backup, self.log)
            return False

        if backup[WfInstances.ACTIVE]:
            self.log.info("Backup is running")
            return True

        self.log.info("Backup is NOT running")
        return False

    def backup_completed_ok(self):
        """Retrieve the backup information from the LCM workflows

        Args: None

        Returns:
            Bool: True if backup is finished
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> Checking if backup completed ok")
        backup = self._get_backup_wf()

        fail_msg = "Backup with tag %s and ID %s has failed" % (self.tag,
                                                                self.backup_id)

        if not backup:
            self.log.error("Backup could not be retrieved")
            self._send_fail_mail(fail_msg)
            return None

        log_wf(backup, self.log)

        if self._wf_has_problem(backup):
            self.log.error("Backup has a problem")
            log_wf(backup, self.log)
            self._send_fail_mail(fail_msg)
            return False

        if backup[WfInstances.ACTIVE]:
            self.log.info("Backup is running")
            return False

        if backup[WfInstances.END_NODE].endswith(
                WfInstances.BACKUP_SUCCESSFUL):
            self.log.info("Backup workflow completed ok")
            return True

        self.log.error("Backup has failed")
        self._send_fail_mail(fail_msg)
        return False

    def verify_backup_state(self):
        """Call verify backup workflow.

           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if backup is good
            Str: For script output

        Raises: Nothing (hopefully!)
        """

        self.log.info("Stage >>> Verify Backup State")
        wfs = WfInstances(self.lcm, self.log)
        wf_id = wfs.start_validate_backup_wf(self.tag)

        if not wf_id:
            self.log.error("Failed to start validation workflow")
            fail_msg = "Failed to start validation workflow"
            self._send_fail_mail(fail_msg)
            return False

        wait = 60
        retry_end = time.time() + self.max_validation_time - wait
        while time.time() < retry_end:
            self.log.info("Waiting %s s to check workflow" % (wait))
            time.sleep(wait)

            if not wfs.get_wfs_from_lcm():
                self.log.warning("Failed to retrieve workflows from LCM")
                continue

            val_wf = wfs.get_wf_by_id(wf_id)

            if not val_wf:
                self.log.warning("Did not get validation workflow")
                continue

            if val_wf[WfInstances.END_NODE] == WfInstances.BACKUP_VALID:
                self.log.info("Backup has been validated and is good")
                return True

            if val_wf[WfInstances.END_NODE] == WfInstances.BACKUP_INVALID:
                self.log.error("Backup has been validated and is NOT GOOD")
                fail_msg = "Backup is not good, validation failed"
                self._send_fail_mail(fail_msg)
                return False

            if self._wf_has_problem(val_wf):
                self.log.error("Backup validation has a problem")
                log_wf(val_wf, self.log)
                fail_msg = "Backup validation failed"
                self._send_fail_mail(fail_msg)
                return False

        self.log.error("Failed to run backup validation workflow")
        return None

    def backup_metadata(self):
        """Backup metadata.
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> get backup metadata")
        meta = 'backup.metadata'
        dest = "%s/%s/%s" % (self.nfs_path, self.tag, meta)

        cmd_args = ' export --filename %s --rcfile %s --tag %s' % (
            meta, self.keystone, self.tag)

        result, stdout, stderr = cmd(self.metadata_script + cmd_args)

        if result == 0 and os.path.isfile(meta):
            self.log.info("Metadata file created ok")
        else:
            self.log.error("Failed to generated metadata file")
            self.log.error("STDOUT: %s", stdout)
            self.log.error("STDERR: %s", stderr)
            fail_msg = "Failed to generate backup metadata"
            self._send_fail_mail(fail_msg)
            return False

        result, stdout, stderr = self._transfer_to_nfs(meta, dest)
        if result == 0:
            self.log.info("Metadata file transferred to nfs ok, %s" % dest)
            return True

        self.log.error("Failed to transfer metadata file")
        self.log.error("STDOUT: %s", stdout)
        self.log.error("STDERR: %s", stderr)
        fail_msg = "Failed to transfer metadata to backup server"
        self._send_fail_mail(fail_msg)
        return False

    def label_ok(self):
        """Create success flag in backup directory
           This is a 'stage' method.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("Stage >>> create success flag")
        ok_file = "%s/%s/%s" % (self.nfs_path, self.tag, 'BACKUP_OK')
        opts = ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        touch = 'ssh -i %s %s %s@%s touch %s' % (self.nfs_key,
                                                 opts,
                                                 self.nfs_user,
                                                 self.nfs,
                                                 ok_file)
        result, stdout, stderr = cmd(touch)

        if result == 0:
            self.log.info("Success flag created at %s" % ok_file)
            return True

        self.log.error("Failed to create success flag")
        self.log.error("STDOUT: " + stdout)
        self.log.error("STDERR: " + stderr)
        fail_msg = "Failed to create success flag on backup server"
        self._send_fail_mail(fail_msg)

        return False


class BackupSequencer(BackupStages):
    """ Class derived from BackupStages adding functionality
        to run the full ENM BUR Backup Sequence.
    """
    def __init__(self):  # pylint: disable=useless-super-delegation
        super(BackupSequencer, self).__init__()

    def check_for_wfs(self):
        """Calls the two wfs methods using a timeout mechanism.

        Args: None

        Returns:
            Bool: False if timeout expires and workflows are running, else True

        Raises: Nothing (hopefully!)
        """
        self.log.info("wait for no workflows")
        retry_wait = 120
        retry_end = time.time() + self.max_delay - retry_wait
        self.log.info("Retry end: %s " % retry_end)
        self.log.info("Max delay: %s " % self.max_delay)
        self.log.info("Time %s" % time.time())
        while time.time() < retry_end:

            if self.skip_all_check:
                self.log.info("Not checking other tenancies' workflows")
                proceed_ok = True
            else:
                state = self.no_banned_wfs()

                if state is True:
                    self.log.info("No workflows running on any tenancy")
                    proceed_ok = True
                elif state is False:
                    self.log.info("workflows are running")
                    proceed_ok = False
                elif state is None:
                    self.log.warning("Failed to check storage workflows")
                    # Assume LAF or WFs are down so we can assume nothing
                    # running if problem is for 'this' tenancy then it will
                    # be caught in next check
                    proceed_ok = True

            if proceed_ok:
                state = self.no_wfs()

                if state is True:
                    self.log.info("No workflows running on %s" % self.lcm)
                    return True
                elif state is False:
                    self.log.info("WfInstances are running on %s" % self.lcm)
                elif state is None:
                    self.log.warning("Failed to check workflows")
            self.log.info("Waiting for %s before checking again" % retry_wait)
            time.sleep(retry_wait)

        self.log.error("Timed out waiting for no workflows")
        return False

    def wait_for_backup(self):
        """Checks for backup to finish using a timeout mechanism.

        Args: None

        Returns:
            Bool: True if backup not running, False if timeout

        Raises: Nothing (hopefully!)
        """
        self.log.info("wait for backup")
        # Wait for backup workflow to appear
        time.sleep(30)
        wait = 300

        fail_check_count = 0
        while True:
            wait_end = time.time() + self.max_time - wait

            while time.time() < wait_end:
                state = self.is_backup_running()
                if state:
                    self.log.info("Rechecking in %s" % wait)
                    time.sleep(wait)
                elif state is None:
                    self.log.error("Failed to retrieve backup")
                    fail_check_count += 1

                    if fail_check_count == 3:
                        return None
                    else:
                        time.sleep(wait)
                else:
                    self.log.info("Backup is not running")
                    return True

            if self.fail_long_backup:
                self.log.warning("Timed out waiting for backup to complete")
                return False

            self.log.warning("Backup is taking longer than expected")
            fail_msg = "Warning, the backup is taking longer than expected"
            self._send_fail_mail(fail_msg, warning=True)

    def run(self):  # pylint: disable=too-many-branches
        """Run the entire backup sequence
           This is a special 'stage' method that runs all stages in sequence,
           calling additional functions to wait and check for stage completion.

        Args: None

        Returns:
            Bool: True if workflows are running
            Str: For script output

        Raises: Nothing (hopefully!)
        """
        self.log.info("run backup sequence")

        backup_ok = True
        if not self.setup_private_key():
            msg = "Failed to get working private key, backup not started"
            self.log.error(msg)
            backup_ok = False

        if backup_ok and not self.check_for_wfs():
            msg = "Timed out waiting for workflows to stop, backup not started"
            self.log.error(msg)
            fail_msg = "Backup could not be started as workflows are running"
            self._send_fail_mail(fail_msg)
            backup_ok = False

        if backup_ok and not self.set_retention():
            self.log.error("Failed to set backup retention")
            backup_ok = False

        if backup_ok and not self.start_backup()[0]:
            self.log.error("Could not start backup")
            backup_ok = False

        if backup_ok:
            wait = self.wait_for_backup()
            if not wait:
                if wait is False:
                    msg = "Timed out waiting for backup (it is still running)"
                else:
                    msg = "Unable to retrieve backup info"

                self.log.error(msg)
                self._send_fail_mail(msg)
                backup_ok = False

        if backup_ok and not self.backup_completed_ok():
            self.log.error("Backup did not complete okay")
            backup_ok = False

        if backup_ok and not self.verify_backup_state():
            self.log.error("Verification of backup failed")
            backup_ok = False

        if backup_ok and not self.backup_metadata():
            self.log.error("Failed to get backup metadata")
            backup_ok = False

        if backup_ok and not self.label_ok():
            self.log.error("Failed to create ok flag")
            backup_ok = False

        if not backup_ok:
            return False

        self.log.info("Backup completed successfully")
        return True
