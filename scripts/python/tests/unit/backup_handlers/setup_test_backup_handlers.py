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

# for error import (mock is being used properly)
# pylint: disable=E0401

"""
This module for helping with common usages for test_backup_stage and
test_backup_sequencer
"""

import os
import mock

import scripts.python.backup_scheduler.backup_handlers as handlers
import scripts.python.backup_scheduler.backup_utils as utils

# backup_handlers mocks
SCRIPT_PATH = 'scripts.python.backup_scheduler.backup_handlers.'
MOCK_BACKUP_STAGES = SCRIPT_PATH + 'BackupStages'
MOCK_BACKUP_SEQUENCER = SCRIPT_PATH + 'BackupSequencer'
MOCK_LOG = SCRIPT_PATH + 'logging.getLogger'
MOCK_LOG_WF = SCRIPT_PATH + 'log_wf'
MOCK_CMD = SCRIPT_PATH + 'cmd'
MOCK_WF_INSTANCE = SCRIPT_PATH + 'WfInstances'
MOCK_TIME_SLEEP = SCRIPT_PATH + 'time.sleep'
MOCK_GET_KEYSTONE_ENV = SCRIPT_PATH + 'get_keystone_env'
MOCK_PING = SCRIPT_PATH + 'ping'
MOCK_CHECK_PRIVATE_KEY = SCRIPT_PATH + 'check_private_key'
MOCK_OPENSTACK = SCRIPT_PATH + 'openstack'
MOCK_GET_KEY_NAMES = SCRIPT_PATH + 'get_key_names_from_stack'
MOCK_GET_PRIVATE_KEY = SCRIPT_PATH + 'get_private_key'
MOCK_CREATE_TEMP_KEY = SCRIPT_PATH + 'create_temp_key_file'

# run_backup_stages mocks
MOCK_MAILER = 'scripts.python.backup_scheduler.run_backup_stages.mailer'
MOCK_BOOLEAN_SEND_MAIL = 'scripts.python.backup_scheduler.' \
                         'run_backup_stages.SEND_MAIL'

# backup_utils mocks
MOCK_SEND_MAIL = 'scripts.python.backup_scheduler.backup_utils.send_mail'

# customer info
TEST_CUSTOMER = 'dummy'
TEST_BACKUP_TAG = 'fake_tag'
TEST_BACKUP_ID = 'fake_id'

DIR = os.path.dirname(os.path.realpath(__file__))

CONFIG_FILE = DIR + '/backup_config_file.ini'

WORKFLOW_INSTANCE = {"instanceId": "d8fdd15c-09c1-487a-a7d0-365863f814d3",
                     "definitionName": "workflow1", "endNodeId": "EndEvent",
                     "startTime": "2018-09-08T09:38:51.878Z",
                     "endTime": "2018-09-08T09:39:10.721Z", "active": False,
                     "incidentActive": False, "aborted": False}


def _basic_backup_stage(stage=True):
    """
    This method is part of each class setup, making it easier to use
    the constructor of BackupStages class.
    :param stage: True if the function should create a BackupStages object
                  False if the function should create a BackupSequencer object
    :return: a BackupStages or BackupSequencer object with basic information
    """
    if stage:
        backup = handlers.BackupStages()
    else:
        backup = handlers.BackupSequencer()

    cfg = utils.Cfg()
    cfg.read_config(CONFIG_FILE)

    backup.deployment_id = TEST_CUSTOMER
    backup.tag = TEST_BACKUP_TAG
    backup.backup_id = TEST_BACKUP_ID

    backup.bkup_script = cfg.get("general.backup_script")
    backup.metadata_script = cfg.get("general.metadata_script")
    backup.skip_all_check = cfg.get_bool("general.skip_check_all")
    backup.fail_long_backup = cfg.get_bool("general.fail_long_backup")
    backup.retention = cfg.get_int("general.retention")

    backup.max_delay = utils.to_seconds(cfg.get("timers.max_start_delay"))
    backup.max_time = utils.to_seconds(cfg.get("timers.max_duration"))

    val_time = cfg.get("timers.max_validation_time")
    backup.max_validation_time = utils.to_seconds(val_time)

    backup.lcm = cfg.get(TEST_CUSTOMER + ".lcm")
    backup.enm_key = cfg.get(TEST_CUSTOMER + ".enm_key")
    backup.keystone = cfg.get(TEST_CUSTOMER + ".keystone_rc")

    backup.nfs = cfg.get("nfs.ip")
    backup.nfs_user = cfg.get("nfs.user")
    backup.nfs_key = cfg.get("nfs.key")
    backup.nfs_path = cfg.get("nfs.path") + '/' + \
        cfg.get(TEST_CUSTOMER + ".deployment_id")

    backup.tenancies = {TEST_CUSTOMER: backup.lcm}
    backup.blocking_wfs = cfg.get("general.blocking_wfs")
    with mock.patch(MOCK_LOG) as mock_log:
        backup.log = mock_log

    with mock.patch(MOCK_MAILER) as mock_mailer:
        backup.mail_fn = mock_mailer

    return backup, backup.log, backup.mail_fn


def email(message):
    """
    Creates a test e-mail message for when send_fail_mail is called
    :param message: The main error/warning message
    :return: failure and warning subject, formatted test e-mail message
    """
    failure_subject = "Backup failure: dummy"
    warning_subject = "Backup warning: dummy"

    url = "http://dummy_lcm/index.html#workflows/workflow/" \
          "enmdeploymentworkflows.--." \
          "Backup%20Deployment/workflowinstance/fake_id"

    message = "{}\n" \
              "Customer: dummy\n" \
              "Tag:      fake_tag\n" \
              "ID:       fake_id\n" \
              "WF URL:   {}".format(message, url)

    return failure_subject, warning_subject, message


def backup_stage():
    """
    Gets a BackupStage object
    """
    return _basic_backup_stage()


def backup_sequencer():
    """
    Gets a BackupSequencer object
    """
    return _basic_backup_stage(False)


class BreakInfiniteLoop(Exception):
    """
    Exception class to break infinite loop
    """
    pass
