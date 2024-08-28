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
# protected access (need to test all methods)
# too many arguments (need to mock various methods/functions)
# for error import (mock is being used properly)
# pylint: disable=C0103,W0212,R0913,E0401

"""
This module is for unit testing of the
scripts.python.backup_scheduler.backup_handlers.BackupStages class
"""
import datetime
import os
import unittest
import mock

from setup_test_backup_handlers import MOCK_BACKUP_STAGES, MOCK_LOG_WF,\
     MOCK_CMD, MOCK_WF_INSTANCE, MOCK_BOOLEAN_SEND_MAIL, MOCK_SEND_MAIL,\
     MOCK_GET_KEYSTONE_ENV, MOCK_PING, MOCK_CHECK_PRIVATE_KEY,\
     MOCK_GET_KEY_NAMES, MOCK_GET_PRIVATE_KEY, MOCK_CREATE_TEMP_KEY,\
     WORKFLOW_INSTANCE, MOCK_TIME_SLEEP, backup_stage, email

MOCK_ISFILE = "scripts.python.backup_scheduler.backup_handlers.os.path.isfile"

FILE_DIR = os.path.dirname(os.path.realpath(__file__))
FILE_DIR = FILE_DIR + '/../backup_utils'


class BackupStagesSendFailMailTestCase(unittest.TestCase):
    """
    Class for testing the _send_mail method
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the tests' constants
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()
        cls.message = "Test sending failure e-mail"
        fail, warn, res = email(cls.message)

        cls.failure_subject = fail
        cls.warning_subject = warn
        cls.result_message = res

    @mock.patch(MOCK_SEND_MAIL)
    def test_send_fail_mail(self, mock_send_mail):
        """
        Asserts if the method is called with the correct subject/message and
        if the return is True
        Param is a mock from the method/function on @mock.patch() annotation
        """
        mock_send_mail.return_value = True

        result = self.backup_stage._send_fail_mail(self.message)
        self.mock_mailer.assert_called_with(self.failure_subject,
                                            self.result_message)
        self.assertTrue(result)

    @mock.patch(MOCK_BOOLEAN_SEND_MAIL)
    def test_send_fail_mail_send_mail_false(self, mock_boolean_send_mail):
        """
        Asserts if the method is called, but doesn't return True when the
        e-mail is not sent
        Param is a mock from the method/function on @mock.patch() annotation
        """
        mock_boolean_send_mail.return_value = False

        result = self.backup_stage._send_fail_mail(self.message)

        self.mock_mailer.assert_called_with(self.failure_subject,
                                            self.result_message)
        self.assertIsNot(True, result)

    @mock.patch(MOCK_SEND_MAIL)
    def test_send_fail_mail_no_mail_fn(self, mock_send_mail):
        """
        Asserts if the run_backup_stages.mailer is not called within the method
        when it is not available
        Param is a mock from the method/function on @mock.patch() annotation
        """
        self.backup_stage.mail_fn = None
        mock_send_mail.return_value = False

        result = self.backup_stage._send_fail_mail(self.message)

        self.mock_mailer.assert_not_called()
        self.assertTrue(result)

    @mock.patch(MOCK_SEND_MAIL)
    def test_send_fail_mail_warning(self, mock_send_mail):
        """
        Asserts if the method is called with the correct subject/message and
        if the return is True
        Param is a mock from the method/function on @mock.patch() annotation
        """
        mock_send_mail.return_value = True

        result = self.backup_stage._send_fail_mail(self.message, warning=True)
        self.mock_mailer.assert_called_with(self.warning_subject,
                                            self.result_message)
        self.assertTrue(result)


class BackupStagesGetBackupWfTestCase(unittest.TestCase):
    """
    Class to test the _get_backup_wf method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()
        cls.wf_instance = dict(WORKFLOW_INSTANCE)

    @mock.patch(MOCK_WF_INSTANCE)
    def test_get_backup_wf(self, mock_workflows):
        """
        Asserts if a workflow is returned when the backup_id has a valid value
        Param is a mock from the method/function on @mock.patch() annotation
        """
        mock_workflows.return_value.get_wfs_from_lcm.return_value = True
        mock_workflows.get_wf_by_id = self.wf_instance
        call = mock.call("Backup workflow found")

        result = self.backup_stage._get_backup_wf()

        self.assertTrue(call in self.mock_log.mock_calls)
        self.assertIsNotNone(result)

    def test_get_backup_wf_no_backup_id(self):
        """
        Asserts if an error is logged when no backup_id is informed
        """
        self.backup_stage.backup_id = None
        expected_err = "No backup ID to check backup state"
        result = self.backup_stage._get_backup_wf()

        self.mock_log.error.assert_called_with(expected_err)
        self.assertIsNone(result)

    @mock.patch(MOCK_WF_INSTANCE)
    def test_get_backup_wf_no_workflows(self, mock_workflows):
        """
        Asserts if None is returned when WFInstances cannot retrieve all
        the workflows
        Param is a mock from the method/function on @mock.patch() annotation
        """
        mock_workflows.return_value.get_wfs_from_lcm.return_value = False
        expected_err = "Failed to retrieve workflows from LCM"
        result = self.backup_stage._get_backup_wf()

        self.mock_log.error.assert_called_with(expected_err)
        self.assertIsNone(result)

    @mock.patch(MOCK_WF_INSTANCE)
    def test_get_backup_wf_no_instance(self, mock_workflows):
        """
        Asserts if None is returned when the backup_id doesn't belong to a
        valid workflow, so no workflow should be returned
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_workflows.return_value.get_wfs_from_lcm.return_value = True
        mock_workflows.return_value.get_wf_by_id.return_value = None

        result = self.backup_stage._get_backup_wf()

        self.mock_log.error.assert_called_with("Backup not found")
        self.assertIsNone(result)


class BackupStagesWfHasProblemTestCase(unittest.TestCase):
    """
    Class to test the _wf_has_problem method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()
        cls.wf_instance = dict(WORKFLOW_INSTANCE)

    def test_wf_has_problem_false(self):
        """
        Asserts if the workflow has no problem, the return is False and the
        info is logged
        """
        result = self.backup_stage._wf_has_problem(self.wf_instance)

        self.mock_log.info.assert_called_with("Workflow has no problem")
        self.assertFalse(result)

    def test_wf_has_problem_incident(self):
        """
        Asserts if the workflow has an incident, the return is True and the
        error is logged
        """
        self.wf_instance['incidentActive'] = True
        result = self.backup_stage._wf_has_problem(self.wf_instance)

        self.mock_log.error.assert_called_with("Workflow has an incident")
        self.assertTrue(result)

    def test_wf_has_problem_aborted(self):
        """
        Asserts if the workflow was aborted, the return is True and the error
        is logged
        """
        self.wf_instance['aborted'] = True
        result = self.backup_stage._wf_has_problem(self.wf_instance)

        self.mock_log.error.assert_called_with("Workflow has been aborted")
        self.assertTrue(result)


class BackupStagesTransferToNfsTestCase(unittest.TestCase):
    """
    Class to test the _transfer_to_nfs method from BackupStages
    Note: it doesn't have a failure scenario because that is covered by
    utils.cm unit test
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()

    @mock.patch(MOCK_CMD)
    def test_transfer_to_nfs(self, mock_cmd):
        """
        Asserts if the result from transfer_to_nfs was executed.
        Param is a mock from the method/function on @mock.patch() annotation
        """
        cmd_return = 200, 'ok', ''

        mock_cmd.return_value = cmd_return
        result = self.backup_stage._transfer_to_nfs('fake_file',
                                                    'fake_destination')

        self.assertEqual(cmd_return, result)


class BackupStagesSetupPrivateKeyTestCase(unittest.TestCase):
    """
    Class to test the setup_private_key method from BackupStages
    """
    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()

    @mock.patch(MOCK_PING)
    def test_setup_private_key_ping_fails(self, mock_ping):
        """
        Return False if the VNF-LCM cannot be pinged
        """
        mock_ping.return_value = False
        err_msg = "cannot contact the VNF-LCM, backup cannot start"
        result = self.backup_stage.setup_private_key()
        self.assertFalse(result)

        self.mock_log.error.assert_called_with(err_msg)

    @mock.patch(MOCK_CHECK_PRIVATE_KEY)
    @mock.patch(MOCK_PING)
    def test_setup_private_key_check_ok(self, mock_ping, mock_key):
        """
        Return True if ping is ok and the private key check is ok
        """
        mock_key.return_value = True
        mock_ping.return_value = True
        ok_msg = "Current key %s is good"
        result = self.backup_stage.setup_private_key()
        self.assertTrue(result)

        self.mock_log.info.assert_called_with(ok_msg, "dummy_enm_key")

    @mock.patch(MOCK_GET_KEYSTONE_ENV)
    @mock.patch(MOCK_CHECK_PRIVATE_KEY)
    @mock.patch(MOCK_PING)
    def test_setup_private_key_get_keystone_fail(self,
                                                 mock_ping,
                                                 mock_key,
                                                 mock_keystone_env):
        """
        Return False if ping is ok, private key check is false, and
        get_keystone_env returns empty dictionary
        """
        mock_key.return_value = False
        mock_ping.return_value = True
        mock_keystone_env.return_value = {}
        err_msg = "Unable to get keystone rc information"
        result = self.backup_stage.setup_private_key()
        self.assertFalse(result)
        self.mock_log.error.assert_called_with(err_msg)

    @mock.patch(MOCK_GET_KEY_NAMES)
    @mock.patch(MOCK_CHECK_PRIVATE_KEY)
    @mock.patch(MOCK_PING)
    def test_setup_private_key_get_key_names_fail(self,
                                                  mock_ping,
                                                  mock_key,
                                                  mock_key_names):
        """
        Return False if ping is ok, private key check is false,
        get_keystone_env returns env dict,  but get_key_names fails
        """
        env_dict = {'OS_USERNAME': 'edders',
                    'OS_IDENTITY_API_VERSION': '3',
                    'OS_PROJECT_ID': 'e28bd6d443989483949349300303403e',
                    'OS_REGION_NAME': 'regionOne',
                    'OS_USER_DOMAIN_NAME': 'Default',
                    'OS_AUTH_URL': 'https://10.2.63.251:13000/v3',
                    'OS_ENDPOINT_TYPE': 'internalURL',
                    'OS_INTERFACE': 'public',
                    'OS_PROJECT_NAME': 'test_project',
                    'OS_PASSWORD': 'test_pass'}

        mock_key.return_value = False
        mock_ping.return_value = True
        mock_key_names.return_value = []
        self.backup_stage.keystone = FILE_DIR + '/test_keystone.rc'

        err_msg = "Failed to get valid private key, backup cannot start"
        result = self.backup_stage.setup_private_key()
        self.assertFalse(result)
        self.mock_log.error.assert_called_with(err_msg)
        mock_key_names.assert_called_with(env_dict)

    @mock.patch(MOCK_GET_PRIVATE_KEY)
    @mock.patch(MOCK_GET_KEY_NAMES)
    @mock.patch(MOCK_CHECK_PRIVATE_KEY)
    @mock.patch(MOCK_PING)
    def test_setup_private_key_get_private_key_fail(self,
                                                    mock_ping,
                                                    mock_check_key,
                                                    mock_key_names,
                                                    mock_get_key):
        """
        Return False if ping is ok, private key check is false,
        get_keystone_env returns env dict, get_key_names succeeds,
        but get_private_key fails.
        """
        key_name = 'test_cu_key'
        mock_get_key.return_value = None
        mock_check_key.return_value = False
        mock_ping.return_value = True
        mock_key_names.return_value = [key_name]
        self.backup_stage.keystone = FILE_DIR + '/test_keystone.rc'

        warn_msg = "Could not get private key from %s"
        err_msg = "Failed to get valid private key, backup cannot start"

        result = self.backup_stage.setup_private_key()
        self.assertFalse(result)
        self.mock_log.warning.assert_called_with(warn_msg, key_name)
        self.mock_log.error.assert_called_with(err_msg)

    @mock.patch(MOCK_CREATE_TEMP_KEY)
    @mock.patch(MOCK_GET_PRIVATE_KEY)
    @mock.patch(MOCK_GET_KEY_NAMES)
    @mock.patch(MOCK_CHECK_PRIVATE_KEY)
    @mock.patch(MOCK_PING)
    def test_setup_private_key_check_key_fail(self,
                                              mock_ping,
                                              mock_check_key,
                                              mock_key_names,
                                              mock_get_key,
                                              mock_create_key):
        """
        Return False if ping is ok, private key check is false,
        get_keystone_env returns env dict, get_key_names and
        get_private_key and create_temp_key succeed, but check_key
        fails
        """
        key_name = 'test_cu_key'
        mock_get_key.return_value = "fake key contents"
        mock_check_key.return_value = False
        mock_ping.return_value = True
        mock_file = mock.call()
        mock_file.name = "key.pem"
        mock_create_key.return_value = mock_file
        mock_key_names.return_value = [key_name]
        self.backup_stage.keystone = FILE_DIR + '/test_keystone.rc'

        warn_msg = "Key %s does not work"
        err_msg = "Failed to get valid private key, backup cannot start"

        result = self.backup_stage.setup_private_key()
        self.assertFalse(result)
        self.mock_log.warning.assert_called_with(warn_msg, mock_file.name)
        self.mock_log.error.assert_called_with(err_msg)

    @mock.patch(MOCK_CMD)
    @mock.patch(MOCK_CREATE_TEMP_KEY)
    @mock.patch(MOCK_GET_PRIVATE_KEY)
    @mock.patch(MOCK_GET_KEY_NAMES)
    @mock.patch(MOCK_CHECK_PRIVATE_KEY)
    @mock.patch(MOCK_PING)
    def test_setup_private_key_succeeds(self,
                                        mock_ping,
                                        mock_check_key,
                                        mock_key_names,
                                        mock_get_key,
                                        mock_create_key,
                                        mock_cmd):
        """
        All called functions succeed, return True
        """
        key_name = 'test_cu_key'
        mock_cmd.return_value = (0, '', '')
        mock_get_key.return_value = "fake key contents"
        mock_check_key.side_effect = [False, True]
        mock_ping.return_value = True
        mock_file = mock.call()
        mock_file.name = "key.pem"
        mock_create_key.return_value = mock_file
        mock_key_names.return_value = [key_name]

        self.backup_stage.keystone = FILE_DIR + '/test_keystone.rc'

        result = self.backup_stage.setup_private_key()
        self.assertTrue(result)
        info_msg = "Key createed successfully"
        self.mock_log.info.assert_called_with(info_msg)


class BackupStagesNoStorageWfsTestCase(unittest.TestCase):
    """
    Class to test the no_banned_wfs method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()

    @mock.patch(MOCK_WF_INSTANCE)
    def test_no_banned_wfs(self, mock_workflows):
        """
        Asserts if there is no active storage workflow
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_workflows.return_value.get_wfs_from_lcm.return_value = True
        mock_workflows.return_value.active_storage_wfs.return_value = []

        result = self.backup_stage.no_banned_wfs()

        self.mock_log.info.assert_called_with("No workflows running")
        self.assertTrue(result)

    @mock.patch(MOCK_WF_INSTANCE)
    def test_no_banned_wfs_validate_customers_log(self, mock_workflows):
        """
        Asserts if the tenancy checked is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_workflows.return_value.get_wfs_from_lcm.return_value = True
        mock_workflows.return_value.active_storage_wfs.return_value = []

        calls = [mock.call('Stage >>> Check for Workflows on all tenancies'),
                 mock.call('%s has no workflows running', 'dummy'),
                 mock.call('No workflows running')]

        result = self.backup_stage.no_banned_wfs()

        self.mock_log.info.assert_has_calls(calls)
        self.assertTrue(result)

    @mock.patch(MOCK_WF_INSTANCE)
    def test_no_banned_wfs_validate_customers_no_wf(self, mock_workflows):
        """
        Asserts if None is returned when the workflows cannot be retrieved and
        logs the error
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_workflows.return_value.get_wfs_from_lcm.return_value = False
        mock_workflows.return_value.active_storage_wfs.return_value = []

        calls = [mock.call("Stage >>> Check for Workflows on all tenancies"),
                 mock.call('%s has no workflows running', 'dummy'),
                 mock.call('No workflows running')]

        result = self.backup_stage.no_banned_wfs()
        self.mock_log.info.assert_has_calls(calls)
        self.assertTrue(result)

    @mock.patch(MOCK_WF_INSTANCE)
    @mock.patch(MOCK_LOG_WF)
    def test_no_banned_wfs_wfs_running(self, mock_log_wf, mock_wfs):
        """
        Asserts if returns False when there is a workflow running and the info
        is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        wf_instance = dict(WORKFLOW_INSTANCE)
        wf_instance['active'] = True
        mock_wfs.return_value.get_wfs_from_lcm.return_value = True
        mock_wfs.return_value.active_storage_wfs.return_value = [wf_instance]

        calls = [mock.call('Stage >>> Check for Workflows on all tenancies'),
                 mock.call('%s has workflows running:', 'dummy'),
                 mock.call('Workflows running, checking against rules'),
                 mock.call('Checking workflow count against rule %s',
                           '1:backup'),
                 mock.call('%s %s workflows running.  Max allowed is %s',
                           1, 'backup', 1)]

        result = self.backup_stage.no_banned_wfs()

        mock_log_wf.assert_called_with(wf_instance, self.mock_log)
        self.mock_log.info.assert_has_calls(calls)
        self.assertFalse(result)


class BackupStagesNoWfsTestCase(unittest.TestCase):
    """
    Class to test the no_wfs method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()

    @mock.patch(MOCK_WF_INSTANCE)
    def test_no_wfs(self, mock_workflows):
        """
        Asserts if there is no active workflow and the info is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_workflows.return_value.get_wfs_from_lcm.return_value = True
        mock_workflows.return_value.active_wfs.return_value = []

        calls = [mock.call("Stage >>> Check for any workflows on dummy_lcm"),
                 mock.call("No active workflows")]

        result = self.backup_stage.no_wfs()

        self.mock_log.info.assert_has_calls(calls)
        self.assertTrue(result)

    @mock.patch(MOCK_WF_INSTANCE)
    def test_no_wfs_failed_workflows(self, mock_workflows):
        """
        Asserts if returns None and a warning is logged when WFInstances
        fails to get workflows
        Param is a mock from the method/function on @mock.patch() annotation
        """
        mock_workflows.return_value.get_wfs_from_lcm.return_value = False
        expected_log = "Stage >>> Check for any workflows on dummy_lcm"
        expected_warn = "Failed to retrieve workflows"
        result = self.backup_stage.no_wfs()

        self.mock_log.info.assert_called_with(expected_log)
        self.mock_log.warning.assert_called_with(expected_warn)
        self.assertIsNone(result)

    @mock.patch(MOCK_WF_INSTANCE)
    @mock.patch(MOCK_LOG_WF)
    def test_no_wfs_workflows_running(self, mock_log_wf, mock_workflows):
        """
        Asserts if returns False when there are workflows running and the info
        is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        wf_instance = dict(WORKFLOW_INSTANCE)
        wf_instance['active'] = True

        mock_workflows.return_value.get_wfs_from_lcm.return_value = True
        mock_workflows.return_value.active_wfs.return_value = [wf_instance]

        calls = [mock.call("Stage >>> Check for any workflows on dummy_lcm"),
                 mock.call("There are workflows running:")]

        result = self.backup_stage.no_wfs()

        mock_log_wf.assert_called_with(wf_instance, self.mock_log)
        self.mock_log.info.assert_has_calls(calls)
        self.assertFalse(result)


class BackupStagesSetRetentionTestCase(unittest.TestCase):
    """
    Class to test the set_retention method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()

    @mock.patch(MOCK_CMD)
    def test_set_retention(self, mock_cmd):
        """
        Asserts if returns True and the info is logged
        Param is a mock from the method/function on @mock.patch() annotation
        """
        mock_cmd.return_value = 0, 'ok', ''

        result = self.backup_stage.set_retention()

        self.mock_log.info.assert_called_with("Stage >>> Set retention")
        self.assertTrue(result)

    @mock.patch(MOCK_CMD)
    def test_set_retention_failed(self, mock_cmd):
        """
        Asserts if returns False when fails to set retention, the error is
        logged and an error e-mail is sent
        Param is a mock from the method/fn on @mock.patch() annotation
        """
        msg = "Failed to set consul retention value on dummy_lcm"
        subject, _, message = email(msg)
        mock_cmd.return_value = 1, '', 'fail'

        result = self.backup_stage.set_retention()

        self.mock_log.info.assert_called_with("Stage >>> Set retention")
        self.mock_log.error.assert_called_with("Failed to set retention")
        self.mock_mailer.assert_called_with(subject, message)
        self.assertFalse(result)


class BackupStagesStartBackupTestCase(unittest.TestCase):
    """
    Class to test the start_backup method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()

    @mock.patch(MOCK_CMD)
    def test_start_backup(self, mock_cmd):
        """
        Asserts if returns a tuple with True plus the info about the backup
        that was started and if the info is logged
        Param is a mock from the method/function on @mock.patch() annotation
        """
        info = True, "ID: fake_id  TAG: fake_tag"

        calls = [mock.call("Stage >>> start backup"),
                 mock.call("Backup started with tag fake_tag and id fake_id")]

        mock_cmd.return_value = 0, 'ok', ''

        result = self.backup_stage.start_backup()

        self.mock_log.info.assert_has_calls(calls)
        self.assertEqual(info, result)

    @mock.patch(MOCK_CMD)
    def test_start_backup_no_backup_id(self, mock_cmd):
        """
        Asserts if returns a tuple with False and the info about the failed
        backup and if the error is logged when there is no backup id within
        the BackupStages object
        Param is a mock from the method/function on @mock.patch() annotation
        """
        self.backup_stage.backup_id = None

        info = False, "ID: None  TAG: fake_tag"

        mock_cmd.return_value = 0, 'ok', ''
        expected_err = "Failed to get backup id, assuming no backup"
        result = self.backup_stage.start_backup()

        self.mock_log.info.assert_called_with("Stage >>> start backup")
        self.mock_log.error.assert_called_with(expected_err)
        self.assertEqual(info, result)

    @mock.patch(MOCK_CMD)
    def test_start_backup_no_result(self, mock_cmd):
        """
        Asserts if returns a tuple with False and the info about the failed
        backup and if the error is logged
        Param is a mock from the method/function on @mock.patch() annotation
        """
        failure, _, message = email("Failed to start backup on dummy_lcm")
        info = False, "ID: fake_id  TAG: fake_tag"

        mock_cmd.return_value = 1, '', 'fail'

        result = self.backup_stage.start_backup()

        self.mock_log.info.assert_called_with("Stage >>> start backup")
        self.mock_log.error.assert_called_with("Starting backup failed")
        self.mock_mailer.assert_called_with(failure, message)
        self.assertEqual(info, result)


class BackupStagesIsBackupRunningTestCase(unittest.TestCase):
    """
    Class to test the is_backup_running method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()

    @mock.patch(MOCK_BACKUP_STAGES + '._get_backup_wf')
    def test_is_backup_running(self, mock_backup_wf):
        """
        Asserts if backup is running and if the info is logged
        Param is a mock from the method/function on @mock.patch() annotation
        """
        wf_instance = dict(WORKFLOW_INSTANCE)
        wf_instance['active'] = True

        mock_backup_wf.return_value = wf_instance

        calls = [mock.call("Stage >>> Is Backup Running"),
                 mock.call("Workflow has no problem"),
                 mock.call("Backup is running")]

        result = self.backup_stage.is_backup_running()

        self.mock_log.info.assert_has_calls(calls)
        self.assertTrue(result)

    @mock.patch(MOCK_BACKUP_STAGES + '._get_backup_wf')
    def test_is_backup_running_no_backup(self, mock_backup_wf):
        """
        Asserts if None is returned when there is no backup found with backup
        id and the error is logged
        Param is a mock from the method/function on @mock.patch() annotation
        """
        mock_backup_wf.return_value = None

        result = self.backup_stage.is_backup_running()

        self.mock_log.info.assert_called_with("Stage >>> Is Backup Running")
        self.mock_log.error.assert_called_with("Failed to find backup")
        self.assertIsNone(result)

    @mock.patch(MOCK_LOG_WF)
    @mock.patch(MOCK_BACKUP_STAGES + '._get_backup_wf')
    def test_is_backup_running_bkup_problem(self, mock_backup_wf, mock_log_wf):
        """
        Asserts if the backup running has a problem (is aborted), the error is
        logged and sent as an e-mail and if the backup workflow is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        wf_instance = dict(WORKFLOW_INSTANCE)
        wf_instance['active'] = True
        wf_instance['incidentActive'] = True

        mock_backup_wf.return_value = wf_instance

        result = self.backup_stage.is_backup_running()

        self.mock_log.info.assert_called_with("Stage >>> Is Backup Running")
        self.mock_log.error.assert_called_with("Backup has a problem")
        mock_log_wf.assert_called_with(wf_instance, self.mock_log)
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_STAGES + '._get_backup_wf')
    def test_is_backup_running_not_running(self, mock_backup_wf):
        """
        Asserts if the backup is not running and if the info is logged
        Param is a mock from the method/function on @mock.patch() annotation
        """
        wf_instance = dict(WORKFLOW_INSTANCE)

        mock_backup_wf.return_value = wf_instance

        calls = [mock.call("Stage >>> Is Backup Running"),
                 mock.call("Workflow has no problem"),
                 mock.call("Backup is NOT running")]

        result = self.backup_stage.is_backup_running()

        self.mock_log.info.assert_has_calls(calls)
        self.assertFalse(result)


class BackupStagesBackupCompletedTestCase(unittest.TestCase):
    """
    Class to test the backup_completed_ok method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()
        msg = "Backup with tag fake_tag and ID fake_id has failed"
        cls.subject, _, cls.message = email(msg)
        cls.wf_instance = dict(WORKFLOW_INSTANCE)

    @mock.patch(MOCK_BACKUP_STAGES + '._get_backup_wf')
    def test_backup_completed_ok(self, mock_backup_wf):
        """
        Asserts if the endNodeId is valid for a completed backup and if the
        info is logged
        Param is a mock from the method/function on @mock.patch() annotation
        """
        self.wf_instance = dict(WORKFLOW_INSTANCE)
        self.wf_instance['endNodeId'] = "EndEvent_10213m5__prg__p100"
        mock_backup_wf.return_value = self.wf_instance

        result = self.backup_stage.backup_completed_ok()

        self.mock_log.info.assert_called_with("Backup workflow completed ok")
        self.assertTrue(result)

    @mock.patch(MOCK_BACKUP_STAGES + '._get_backup_wf')
    def test_backup_completed_ok_no_backup(self, mock_backup_wf):
        """
        Asserts if the the endNodeId is not valid for a completed backup and
        returns None, if the error is logged and sent as e-mail
        Param is a mock from the method/function on @mock.patch() annotation
        """

        mock_backup_wf.return_value = None
        log_msg = "Stage >>> Checking if backup completed ok"
        result = self.backup_stage.backup_completed_ok()

        self.mock_log.info.assert_called_with(log_msg)
        self.mock_log.error.assert_called_with("Backup could not be retrieved")
        self.mock_mailer.assert_called_with(self.subject, self.message)
        self.assertIsNone(result)

    @mock.patch(MOCK_BACKUP_STAGES + '._get_backup_wf')
    @mock.patch(MOCK_LOG_WF)
    def test_backup_completed_ok_has_prblem(self, mock_log_wf, mock_backup_wf):
        """
        Asserts if returns False when there is a problem with the backup and
        if the error is logged and sent as e-mail. The workflow also must
        be logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        self.wf_instance['incidentActive'] = True
        mock_backup_wf.return_value = self.wf_instance
        log_msg = "Stage >>> Checking if backup completed ok"
        result = self.backup_stage.backup_completed_ok()

        mock_log_wf.assert_called_with(self.wf_instance, self.mock_log)
        self.mock_log.info.assert_called_with(log_msg)
        self.mock_log.error.assert_called_with("Backup has a problem")
        self.mock_mailer.assert_called_with(self.subject, self.message)
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_STAGES + '._get_backup_wf')
    def test_backup_completed_ok_running(self, mock_backup_wf):
        """
        Asserts if returns False when the backup is still running and if the
        info is logged
        Param is a mock from the method/function on @mock.patch() annotation
        """
        self.wf_instance['active'] = True
        mock_backup_wf.return_value = self.wf_instance

        result = self.backup_stage.backup_completed_ok()

        self.mock_log.info.assert_called_with("Backup is running")
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_STAGES + '._get_backup_wf')
    def test_backup_completed_ok_failed(self, mock_backup_wf):
        """
        Asserts if return False when the endNodeId is invalid and if the error
        is logged and sent as e-mail
        Param is a mock from the method/function on @mock.patch() annotation
        """
        self.wf_instance['endNodeId'] = "EndEvent_10213m5__other"

        mock_backup_wf.return_value = self.wf_instance

        result = self.backup_stage.backup_completed_ok()

        self.mock_log.error.assert_called_with("Backup has failed")
        self.mock_mailer.assert_called_with(self.subject, self.message)
        self.assertFalse(result)


class BackupStagesVerifyBackupStateTestCase(unittest.TestCase):
    """
    Class to test the verify_backup_state method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()
        cls.wf_instance = dict(WORKFLOW_INSTANCE)

    @mock.patch(MOCK_WF_INSTANCE + '.get_wf_by_id')
    @mock.patch(MOCK_WF_INSTANCE + '.get_wfs_from_lcm')
    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_WF_INSTANCE + '.start_validate_backup_wf')
    def test_verify_backup_state(self, mock_validate, mock_sleep, mock_wfs,
                                 mock_workflow):
        """
        Asserts if return True when the endNodeId has a valid value and the
        backup is completed, and if the info is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        self.wf_instance["endNodeId"] = "ValidateBackupsEnd"
        log_msg = "Backup has been validated and is good"
        mock_validate.return_value = "d8fdd15c-09c1-487a-a7d0-365863f814d3"
        mock_sleep.call_args = 1  # too long waiting for 60 seconds
        mock_wfs.return_value = True
        mock_workflow.return_value = self.wf_instance

        result = self.backup_stage.verify_backup_state()

        self.mock_log.info.assert_called_with(log_msg)
        self.assertTrue(result)

    @mock.patch(MOCK_WF_INSTANCE + '.start_validate_backup_wf')
    def test_verify_backup_state_no_wf_id(self, mock_validate):
        """
        Asserts if returns False when the validation fails and if the error is
        logged and sent as e-mail
        Param is a mock from the methods on @mock.patch() annotation
        """
        subject, _, message = email("Failed to start validation workflow")
        mock_validate.return_value = None
        log_msg = "Failed to start validation workflow"
        result = self.backup_stage.verify_backup_state()

        self.mock_log.info.assert_called_with("Stage >>> Verify Backup State")
        self.mock_log.error.assert_called_with(log_msg)
        self.mock_mailer.assert_called_with(subject, message)
        self.assertFalse(result)

    @mock.patch(MOCK_WF_INSTANCE + '.get_wfs_from_lcm')
    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_WF_INSTANCE + '.start_validate_backup_wf')
    def test_verify_backup_state_no_wfs(self, mock_validate, mock_sleep,
                                        mock_wfs):
        """
        Asserts if returns False when the workflows couldn't be fetched from
        lcm and the error is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_validate.return_value = "d8fdd15c-09c1-487a-a7d0-365863f814d3"
        mock_sleep.call_args = 1  # too long waiting for 60 seconds
        mock_wfs.return_value = False
        log_warn = "Failed to retrieve workflows from LCM"
        log_err = "Failed to run backup validation workflow"
        result = self.backup_stage.verify_backup_state()

        self.mock_log.warning.assert_called_with(log_warn)
        self.mock_log.error.assert_called_with(log_err)

        self.assertFalse(result)

    @mock.patch(MOCK_WF_INSTANCE + '.get_wf_by_id')
    @mock.patch(MOCK_WF_INSTANCE + '.get_wfs_from_lcm')
    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_WF_INSTANCE + '.start_validate_backup_wf')
    def test_verify_backup_state_no_workflow(self, mock_validate, mock_sleep,
                                             mock_wfs, mock_workflow):
        """
        Asserts if returns False when no workflow is found with the informed id
        and if the error is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_validate.return_value = "d8fdd15c-09c1-487a-a7d0-365863f814d3"
        mock_sleep.call_args = 1  # too long waiting for 60 seconds
        mock_wfs.return_value = True
        mock_workflow.return_value = None

        result = self.backup_stage.verify_backup_state()

        warn_msg = "Did not get validation workflow"
        err_msg = "Failed to run backup validation workflow"
        self.mock_log.warning.assert_called_with(warn_msg)
        self.mock_log.error.assert_called_with(err_msg)

        self.assertFalse(result)

    @mock.patch(MOCK_WF_INSTANCE + '.get_wf_by_id')
    @mock.patch(MOCK_WF_INSTANCE + '.get_wfs_from_lcm')
    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_WF_INSTANCE + '.start_validate_backup_wf')
    def test_verify_backup_state_invalid_workflow(self, mock_validate,
                                                  mock_sleep, mock_wfs,
                                                  mock_workflow):
        """
        Asserts if returns False when endNodeId is a validation failed value
        and if the error is logged and sent as e-mail
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        subject, _, message = email("Backup is not good, validation failed")
        self.wf_instance["endNodeId"] = "BackupValidationFailed"

        mock_validate.return_value = "d8fdd15c-09c1-487a-a7d0-365863f814d3"
        mock_sleep.call_args = 1  # too long waiting for 60 seconds
        mock_wfs.return_value = True
        mock_workflow.return_value = self.wf_instance

        result = self.backup_stage.verify_backup_state()

        err_msg = "Backup has been validated and is NOT GOOD"
        self.mock_log.error.assert_called_with(err_msg)
        self.mock_mailer.assert_called_with(subject, message)

        self.assertFalse(result)

    @mock.patch(MOCK_LOG_WF)
    @mock.patch(MOCK_WF_INSTANCE + '.get_wf_by_id')
    @mock.patch(MOCK_WF_INSTANCE + '.get_wfs_from_lcm')
    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_WF_INSTANCE + '.start_validate_backup_wf')
    def test_verify_backup_state_workflow_problem(self, mock_validate,
                                                  mock_sleep, mock_wfs,
                                                  mock_workflow, mock_log_wf):
        """
        Asserts if returns False when backup has a problem (incidentActive),
        if the error was logged and sent as e-mail and if the backup was logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        subject, _, message = email("Backup validation failed")
        self.wf_instance["incidentActive"] = True

        mock_validate.return_value = "d8fdd15c-09c1-487a-a7d0-365863f814d3"
        mock_sleep.call_args = 1  # too long waiting for 60 seconds
        mock_wfs.return_value = True
        mock_workflow.return_value = self.wf_instance

        result = self.backup_stage.verify_backup_state()

        err_msg = "Backup validation has a problem"
        self.mock_log.error.assert_called_with(err_msg)
        mock_log_wf.assert_called_with(self.wf_instance, self.mock_log)
        self.mock_mailer.assert_called_with(subject, message)

        self.assertFalse(result)

    @mock.patch(MOCK_WF_INSTANCE + '.get_wf_by_id')
    @mock.patch(MOCK_WF_INSTANCE + '.get_wfs_from_lcm')
    @mock.patch(MOCK_TIME_SLEEP)
    @mock.patch(MOCK_WF_INSTANCE + '.start_validate_backup_wf')
    def test_verify_backup_state_failed(self, mock_validate, mock_sleep,
                                        mock_wfs, mock_workflow):
        """
        Asserts if returns None when the endNodeId is the only step not valid
        and if the error is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_validate.return_value = "d8fdd15c-09c1-487a-a7d0-365863f814d3"
        mock_sleep.call_args = 1  # too long waiting for 60 seconds
        mock_wfs.return_value = True
        mock_workflow.return_value = self.wf_instance

        result = self.backup_stage.verify_backup_state()

        err_msg = "Failed to run backup validation workflow"
        self.mock_log.error.assert_called_with(err_msg)

        self.assertIsNone(result)


class BackupStagesBackupMetadataTestCase(unittest.TestCase):
    """
    Class to test the backup_metadata method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()

    @mock.patch(MOCK_BACKUP_STAGES + '._transfer_to_nfs')
    @mock.patch(MOCK_ISFILE)
    @mock.patch(MOCK_CMD)
    def test_backup_metadata(self, mock_cmd, mock_isfile, mock_transfer):
        """
        Asserts if returns True when a metadata file is created and transferred
        successfully and the info is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_cmd.return_value = 0, 'ok', ''
        mock_isfile.return_value = True
        mock_transfer.return_value = 0, 'ok', ''

        calls = [mock.call("Stage >>> get backup metadata"),
                 mock.call("Metadata file created ok"),
                 mock.call("Metadata file transferred to nfs ok, "
                           "nfs_path/dummy_id/fake_tag/backup.metadata")]

        result = self.backup_stage.backup_metadata()

        self.mock_log.info.assert_has_calls(calls)
        self.assertTrue(result)

    @mock.patch(MOCK_ISFILE)
    @mock.patch(MOCK_CMD)
    def test_backup_metadata_generate_failed(self, mock_cmd, mock_isfile):
        """
        Asserts if returns False when the metadata file is not generated and
        the error is logged
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mock_cmd.return_value = 1, '', 'fail'
        mock_isfile.return_value = True

        calls = [mock.call("Failed to generated metadata file"),
                 mock.call('STDOUT: %s', ''),
                 mock.call('STDERR: %s', 'fail')]
        result = self.backup_stage.backup_metadata()

        self.mock_log.error.assert_has_calls(calls)
        self.assertFalse(result)

    @mock.patch(MOCK_BACKUP_STAGES + '._transfer_to_nfs')
    @mock.patch(MOCK_ISFILE)
    @mock.patch(MOCK_CMD)
    def test_backup_metadata_transfer_failed(self, mock_cmd, mock_isfile,
                                             mock_transfer):
        """
        Asserts if returns False when the metadata file is created, but cannot
        be sent, if the error is logged and sent as e-mail
        Params are mocks from the methods/fns on @mock.patch() annotations
        """
        mail_msg = "Failed to transfer metadata to backup server"
        subject, _, message = email(mail_msg)
        mock_cmd.return_value = 0, 'ok', ''
        mock_isfile.return_value = True
        mock_transfer.return_value = 1, '', 'fail'

        calls = [mock.call("Failed to transfer metadata file"),
                 mock.call('STDOUT: %s', ''),
                 mock.call('STDERR: %s', 'fail')]
        result = self.backup_stage.backup_metadata()

        self.mock_log.error.assert_has_calls(calls)
        self.mock_mailer.assert_called_with(subject, message)
        self.assertFalse(result)


class BackupStagesLabelOKTestCase(unittest.TestCase):
    """
    Class to test the label_ok method from BackupStages
    """

    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()

    @mock.patch(MOCK_CMD)
    def test_label_ok(self, mock_cmd):
        """
        Asserts if returns True when the success flag is created and the info
        is logged
        Param is a mock from the method/function on @mock.patch() annotation
        """
        mock_cmd.return_value = 0, 'ok', ''
        call1 = "Stage >>> create success flag"
        call2 = "Success flag created at nfs_path/dummy_id/fake_tag/BACKUP_OK"
        calls = [mock.call(call1),
                 mock.call(call2)]

        result = self.backup_stage.label_ok()

        self.mock_log.info.assert_has_calls(calls)
        self.assertTrue(result)

    @mock.patch(MOCK_CMD)
    def test_label_ok_failed(self, mock_cmd):
        """
        Asserts if returns False when the success flag cannot be created
        and the error is logged and sent as e-mail
        Param is a mock from the method/function on @mock.patch() annotation
        """
        email_msg = "Failed to create success flag on backup server"
        subject, _, message = email(email_msg)
        mock_cmd.return_value = 1, '', 'fail'

        calls = [mock.call("Failed to create success flag"),
                 mock.call("STDOUT: "),
                 mock.call("STDERR: fail")]

        result = self.backup_stage.label_ok()

        self.mock_log.error.assert_has_calls(calls)
        self.mock_mailer.assert_called_with(subject, message)
        self.assertFalse(result)


class BackupStagesBackupTagTestCase(unittest.TestCase):
    """
    Class to test the label_ok method from BackupStages
    """
    @classmethod
    def setUp(cls):
        """
        Setting up the test variables
        """
        cls.backup_stage, cls.mock_log, cls.mock_mailer = backup_stage()
        cls.now = datetime.datetime(2018, 11, 7, 15, 41, 33, 156080)

    @mock.patch('scripts.python.backup_scheduler.backup_handlers.get_time')
    @mock.patch(MOCK_CMD)
    def test_get_backup_tag_ok(self, mock_cmd, mock_now):
        """
        Test parsing backup tag works
        """
        expected_tag = 'dummy_18_15_iso_1_64_121__20181107_1541'

        ver_string = 'ENM 18.15 (ISO Version: 1.64.121) AOM 901 151 R1CC'
        cmd_return = 0, ver_string, ''
        mock_cmd.return_value = cmd_return
        mock_now.return_value = self.now

        result = self.backup_stage._get_backup_tag()
        self.assertEquals(result, expected_tag)

    @mock.patch('scripts.python.backup_scheduler.backup_handlers.get_time')
    @mock.patch(MOCK_CMD)
    def test_get_backup_tag_cmd_fails(self, mock_cmd, mock_now):
        """
        Test parsing backup tag fails
        """
        expected_tag = 'dummy_unknown_enm_version__20181107_1541'

        cmd_return = 1, '', ''
        mock_cmd.return_value = cmd_return
        mock_now.return_value = self.now

        result = self.backup_stage._get_backup_tag()
        self.assertEquals(result, expected_tag)

    @mock.patch('scripts.python.backup_scheduler.backup_handlers.get_time')
    @mock.patch(MOCK_CMD)
    def test_get_backup_tag_parse_ok(self, mock_cmd, mock_now):
        """
        Test parsing backup tag ok with unkown enm version
        """
        expected_tag = 'dummy_unknown_enm_version__20181107_1541'

        cmd_return = 0, 'ENM', ''
        mock_cmd.return_value = cmd_return
        mock_now.return_value = self.now

        result = self.backup_stage._get_backup_tag()
        self.assertEquals(result, expected_tag)
