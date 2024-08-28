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

# For invalid method name (too many chars)
# too many arguments (need to mock various methods/functions)
# for error import (mock is being used properly)
# pylint: disable=C0103,R0913,E0401

"""
This module is for unit testing of the
scripts.python.backup_scheduler.backup_handlers.BackupSequencer class
"""


import unittest
import mock
from setup_test_backup_handlers import MOCK_TIME_SLEEP, MOCK_BACKUP_SEQUENCER,\
    backup_sequencer, email, BreakInfiniteLoop


class BackupSequencerCheckForWfsTestCase(unittest.TestCase):
    """
    Class for unit testing of BackupSequencer.check_for_wfs method
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the tests variables
        """
        cls.sequencer, cls.mock_log, cls.mock_mailer = backup_sequencer()

    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.no_banned_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.no_wfs')
    def test_check_for_wfs(self, mock_no_wfs, mock_no_banned, mock_sleep):
        """
        Asserts True when no backup is running and the info is logged
        Params are mocks from the methods/fnns on @mock.patch() annotations
        """
        mock_no_banned.return_value = True
        mock_no_wfs.return_value = True
        mock_sleep.call_args = 1  # too long wait

        result = self.sequencer.check_for_wfs()
        log_info = "No workflows running on dummy_lcm"
        self.mock_log.info.assert_called_with(log_info)
        self.assertTrue(result)

    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.no_wfs')
    def test_check_for_wfs_skip_all_check(self, mock_no_wfs, mock_sleep):
        """
        Asserts if returns True and the info is logged when skip_all_check is
        True, so no workflows are checked weather they are running or not
        Param is mock from the method/function on @mock.patch() annotation
        """
        self.sequencer.skip_all_check = True
        mock_no_wfs.return_value = True
        mock_sleep.call_args = 1
        call = mock.call("Not checking other tenancies' workflows")

        result = self.sequencer.check_for_wfs()

        self.assertTrue(call in self.mock_log.info.mock_calls)
        log_info = "No workflows running on dummy_lcm"
        self.mock_log.info.assert_called_with(log_info)
        self.assertTrue(result)

    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.no_banned_wfs')
    def test_check_for_wfs_workflows_running(self, mock_no_banned,
                                             mock_sleep):
        """
        Asserts if returns False when there are workflows running and the
        retries finish before there is no workflow running
        Asserts if info about workflows running and time out error are logged
        Param is mock from the method/function on @mock.patch() annotation
        """
        mock_no_banned.return_value = False
        mock_sleep.call_args = 1
        call = mock.call("workflows are running")

        result = self.sequencer.check_for_wfs()

        self.assertTrue(call in self.mock_log.info.mock_calls)
        log_err = "Timed out waiting for no workflows"
        self.mock_log.error.assert_called_with(log_err)
        self.assertFalse(result)

    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.no_banned_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.no_wfs')
    def test_check_for_wfs_wf_instance_running(self, mock_no_wfs,
                                               mock_no_banned, mock_sleep):
        """
        Asserts if returns False when there is a backup workflow instance
        running, even though the check for workflows failed
        Asserts if the warning about failing to check all workflows
        Asserts if the error message is logged when timed out of checking if
        no workflow is running
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_no_banned.return_value = None
        mock_no_wfs.return_value = False
        mock_sleep.call_args = 1
        call = mock.call("WfInstances are running on dummy_lcm")

        result = self.sequencer.check_for_wfs()

        self.assertTrue(call in self.mock_log.info.mock_calls)
        log_warn = "Failed to check storage workflows"
        log_err = "Timed out waiting for no workflows"
        self.mock_log.warning.assert_called_with(log_warn)
        self.mock_log.error.assert_called_with(log_err)
        self.assertFalse(result)

    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.no_banned_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.no_wfs')
    def test_check_for_wfs_failed_check_wfs(self, mock_no_wfs, mock_no_banned,
                                            mock_sleep):
        """
        Asserts if returns False when fails to check if there is any workflow
        running and the retries time out
        Asserts if the info about failing is logged
        Asserts if the time out error is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_no_banned.return_value = None
        mock_no_wfs.return_value = None
        mock_sleep.call_args = 1
        calls = [mock.call("Failed to check storage workflows"),
                 mock.call("Failed to check workflows")]

        result = self.sequencer.check_for_wfs()

        self.mock_log.warning.assert_has_calls(calls)
        log_err = "Timed out waiting for no workflows"
        self.mock_log.error.assert_called_with(log_err)
        self.assertFalse(result)


class BackupSequencerWaitForBackupTestCase(unittest.TestCase):
    """
    Class for unit testing BackupSequencer.wait_for_backup method
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the tests variables
        """
        cls.sequencer, cls.mock_log, cls.mock_mailer = backup_sequencer()
        mail_msg = "Warning, the backup is taking longer than expected"
        _, cls.subject, cls.message = email(mail_msg)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.is_backup_running')
    @mock.patch(MOCK_TIME_SLEEP)
    def test_wait_for_backup_not_running(self, mock_sleep, mock_bkp_running):
        """
        Asserts if returns True and the info is logged when the current backup
        is not running
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        self.sequencer.max_time = 305  # make wait_end > than time.time()
        mock_sleep.call_args = 1  # too long waiting 30 seconds
        mock_bkp_running.return_value = False

        result = self.sequencer.wait_for_backup()

        self.mock_log.info.assert_called_with("Backup is not running")
        self.assertTrue(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.is_backup_running')
    @mock.patch(MOCK_TIME_SLEEP)
    def test_wait_for_backup_is_running(self, mock_sleep, mock_bkp_running):
        """
        Has a warning logged and sent as e-mail when the current
        backup is still running after a recheck
        Params are mocks from the methods/fns on @mock.patch() annotations
        Code is an infinite loop so need to use exception side effect with
        mailer to escape.
        """
        self.sequencer.max_time = 305  # make wait_end > than time.time()
        mock_sleep.call_args = 1  # too long waiting 30 seconds
        self.mock_mailer.side_effect = BreakInfiniteLoop
        try:
            self.sequencer.wait_for_backup()
        except BreakInfiniteLoop:
            pass

        log_warn = "Backup is taking longer than expected"
        self.mock_log.warning.assert_called_with(log_warn)
        self.mock_mailer.assert_called_with(self.subject, self.message)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.is_backup_running')
    @mock.patch(MOCK_TIME_SLEEP)
    def test_wait_for_backup_is_running_longer(self, mock_sleep,
                                               mock_bkp_running):
        """
        Asserts if returns False and a warning is logged when the current
        backup is running longer than planned by config file
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        self.sequencer.fail_long_backup = True
        self.sequencer.max_time = 305  # make wait_end > than time.time()
        mock_sleep.call_args = 1  # too long waiting 30 seconds
        result = self.sequencer.wait_for_backup()

        log_warn = "Timed out waiting for backup to complete"
        self.mock_log.warning.assert_called_with(log_warn)
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.is_backup_running')
    @mock.patch(MOCK_TIME_SLEEP)
    def test_wait_for_backup_failed_to_retrieve(self, mock_sleep,
                                                mock_bkp_running):
        """
        Asserts if returns None and the error is logged when cannot check if
        the current backup is running or not
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        self.sequencer.max_time = 305  # make wait_end > than time.time()
        mock_sleep.call_args = 1  # too long waiting 30 seconds
        mock_bkp_running.return_value = None

        result = self.sequencer.wait_for_backup()

        self.mock_log.error.assert_called_with("Failed to retrieve backup")
        self.assertIsNone(result)


class BackupSequencerRunTestCase(unittest.TestCase):
    """
    Class for unit testing the BackupSequencer.run method
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the tests variables
        """
        cls.sequencer, cls.mock_log, cls.mock_mailer = backup_sequencer()

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.set_retention')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.start_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.wait_for_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.backup_completed_ok')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.verify_backup_state')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.backup_metadata')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.label_ok')
    def test_run(self, mock_label, mock_metadata, mock_verify, mock_completed,
                 mock_wait, mock_start, mock_retention, mock_check_for_wfs,
                 mock_key):
        """
        Asserts if returns True when all stages are run successfully and the
        info is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        Each one of them is a stage defined by BackupStages class
        """
        mock_check_for_wfs.return_value = True
        mock_retention.return_value = True
        mock_start.return_value = True, 'Backup started'
        mock_wait.return_value = True
        mock_completed.return_value = True
        mock_verify.return_value = True
        mock_metadata.return_value = True
        mock_label.return_value = True

        result = self.sequencer.run()

        self.mock_log.info.assert_called_with("Backup completed successfully")
        self.assertTrue(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    def test_run_check_for_wfs_failed(self, mock_check_for_wfs, mock_key):
        """
        Asserts if returns False and logs the error when there are other
        workflows running
        Param is mock from the method/function on @mock.patch() annotation
        Also is a stage defined by BackupStages class
        """
        mail_msg = "Backup could not be started as workflows are running"
        subject, _, message = email(mail_msg)
        mock_key.return_value = True
        mock_check_for_wfs.return_value = False

        result = self.sequencer.run()

        log_err = "Timed out waiting for workflows to stop, backup not started"

        self.mock_log.error.assert_called_with(log_err)
        self.mock_mailer.assert_called_with(subject, message)
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.set_retention')
    def test_run_set_retention_failed(self, mock_retention, mock_check_for_wfs,
                                      mock_key):
        """
        Asserts if returns False and logs the error when cannot set retention
        Params are mocks from the methods/fns on @mock.patch() annotations
        Each one of them is a stage defined by BackupStages class
        """
        mock_key.return_value = True
        mock_check_for_wfs.return_value = True
        mock_retention.return_value = False

        result = self.sequencer.run()

        log_err = "Failed to set backup retention"
        self.mock_log.error.assert_called_with(log_err)
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.set_retention')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.start_backup')
    def test_run_start_backup_failed(self, mock_start, mock_retention,
                                     mock_check_for_wfs, mock_key):
        """
        Asserts if returns False and logs the error when cannot start backup
        Params are mocks from the methods/fns on @mock.patch() annotations
        Each one of them is a stage defined by BackupStages class
        """
        mock_key.return_value = True
        mock_check_for_wfs.return_value = True
        mock_retention.return_value = True
        mock_start.return_value = False, 'Backup failed to start'

        result = self.sequencer.run()

        self.mock_log.error.assert_called_with("Could not start backup")
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.set_retention')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.start_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.wait_for_backup')
    def test_run_wait_for_backup_timeout(self, mock_wait, mock_start,
                                         mock_retention, mock_check_for_wfs,
                                         mock_key):
        """
        Asserts if returns False and logs the error when, while waiting for
        the backup, it gets a timeout
        Params are mocks from the methods/fns on @mock.patch() annotations
        Each one of them is a stage defined by BackupStages class
        """
        mail_msg = "Timed out waiting for backup (it is still running)"

        subject, _, message = email(mail_msg)
        mock_key.return_value = True
        mock_check_for_wfs.return_value = True
        mock_retention.return_value = True
        mock_start.return_value = True, 'Backup started'
        mock_wait.return_value = False

        result = self.sequencer.run()

        log_err = "Timed out waiting for backup (it is still running)"
        self.mock_log.error.assert_called_with(log_err)
        self.mock_mailer.assert_called_with(subject, message)
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.set_retention')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.start_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.wait_for_backup')
    def test_run_wait_for_backup_failed(self, mock_wait, mock_start,
                                        mock_retention, mock_check_for_wfs,
                                        mock_key):
        """
        Asserts if returns False and logs the error when, while waiting for
        the backup, it gets a timeout
        Params are mocks from the methods/fns on @mock.patch() annotations
        Each one of them is a stage defined by BackupStages class
        """
        subject, _, message = email("Unable to retrieve backup info")
        mock_key.return_value = True
        mock_check_for_wfs.return_value = True
        mock_retention.return_value = True
        mock_start.return_value = True, 'Backup started'
        # None is returned when sequencer.fail_long_backup is False
        mock_wait.return_value = None

        result = self.sequencer.run()

        log_err = "Unable to retrieve backup info"
        self.mock_log.error.assert_called_with(log_err)
        self.mock_mailer.assert_called_with(subject, message)
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.set_retention')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.start_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.wait_for_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.backup_completed_ok')
    def test_run_backup_completed_failed(self, mock_completed, mock_wait,
                                         mock_start, mock_retention,
                                         mock_check_for_wfs, mock_key):
        """
        Asserts if returns False and logs the error when backup didn't
        complete ok
        Params are mocks from the methods/fns on @mock.patch() annotations
        Each one of them is a stage defined by BackupStages class
        """
        mock_key.return_value = True
        mock_check_for_wfs.return_value = True
        mock_retention.return_value = True
        mock_start.return_value = True, 'Backup started'
        mock_wait.return_value = True
        mock_completed.return_value = False

        result = self.sequencer.run()

        self.mock_log.error.assert_called_with("Backup did not complete okay")
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.set_retention')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.start_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.wait_for_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.backup_completed_ok')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.verify_backup_state')
    def test_run_verify_backup_stage_failed(self, mock_verify, mock_completed,
                                            mock_wait, mock_start,
                                            mock_retention, mock_check_for_wfs,
                                            mock_key):
        """
        Asserts if returns False and the error is logged when backup is
        corrupted
        Params are mocks from the methods/fns on @mock.patch() annotations
        Each one of them is a stage defined by BackupStages class
        """
        mock_key.return_value = True
        mock_check_for_wfs.return_value = True
        mock_retention.return_value = True
        mock_start.return_value = True, 'Backup started'
        mock_wait.return_value = True
        mock_completed.return_value = True
        mock_verify.return_value = False

        result = self.sequencer.run()

        self.mock_log.error.assert_called_with("Verification of backup failed")
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.set_retention')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.start_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.wait_for_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.backup_completed_ok')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.verify_backup_state')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.backup_metadata')
    def test_run_backup_metadata_failed(self, mock_metadata, mock_verify,
                                        mock_completed, mock_wait, mock_start,
                                        mock_retention, mock_check_for_wfs,
                                        mock_key):
        """
        Asserts if returns False and log the error when backup metadata is
        not created
        Params are mocks from the methods/fns on @mock.patch() annotations
        Each one of them is a stage defined by BackupStages class
        """
        mock_key.return_value = True
        mock_check_for_wfs.return_value = True
        mock_retention.return_value = True
        mock_start.return_value = True, 'Backup started'
        mock_wait.return_value = True
        mock_completed.return_value = True
        mock_verify.return_value = True
        mock_metadata.return_value = False

        result = self.sequencer.run()

        self.mock_log.error.assert_called_with("Failed to get backup metadata")
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_SEQUENCER + '.setup_private_key')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.check_for_wfs')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.set_retention')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.start_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.wait_for_backup')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.backup_completed_ok')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.verify_backup_state')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.backup_metadata')
    @mock.patch(MOCK_BACKUP_SEQUENCER + '.label_ok')
    def test_run_label_ok_failed(self, mock_label, mock_metadata, mock_verify,
                                 mock_completed, mock_wait, mock_start,
                                 mock_retention, mock_check_for_wfs, mock_key):
        """
        Asserts if returns False and logs the error when success flag is not
        created
        Params are mocks from the methods/fns on @mock.patch() annotations
        Each one of them is a stage defined by BackupStages class
        """
        mock_key.return_value = True
        mock_check_for_wfs.return_value = True
        mock_retention.return_value = True
        mock_start.return_value = True, 'Backup started'
        mock_wait.return_value = True
        mock_completed.return_value = True
        mock_verify.return_value = True
        mock_metadata.return_value = True
        mock_label.return_value = False

        result = self.sequencer.run()

        self.mock_log.error.assert_called_with("Failed to create ok flag")
        self.assertFalse(result)
