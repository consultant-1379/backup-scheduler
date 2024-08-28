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

"""
This module is for unit tests from the workflows.py script
"""

import unittest
import mock

import scripts.python.backup_scheduler.workflows as workflows

MOCK_PACKAGE = 'scripts.python.backup_scheduler.workflows.'
MOCK_WF_TYPES = MOCK_PACKAGE + 'WfTypes'
MOCK_LOG = MOCK_PACKAGE + 'logging.getLogger'
MOCK_GET_REQUEST = MOCK_PACKAGE + 'utils.get_http_request'
MOCK_POST_REQUEST = MOCK_PACKAGE + 'utils.post_http'
MOCK_DATETIME_NOW = MOCK_PACKAGE + 'datetime.datetime.now'

BACKUP_WORKFLOWS = [{"definitionId": "test_deployment.--.1.45.11."
                                     "--.BackupValidation__top"},
                    {"definitionId": "test_deployment.--.1.44.7.-"
                                     "-.BackupValidation__top"},
                    {"definitionId": "test_deployment.--.1.33.2.-"
                                     "-.BackupValidation__top"}]

OTHER_WORKFLOWS = [{"definitionId": "test_deployment.--.1.28.5.--"
                                    ".CleanupBackups__top"},
                   {"definitionId": "test_deployment.--.1.28.5.--"
                                    ".ShutdownVMs_1"},
                   {"definitionId": "test_deployment.--.1.28.5.--"
                                    ".DeleteVolumes"}]

WORKFLOW_INSTANCE = {"instanceId": "d8fdd15c-09c1-487a-a7d0-365863f814d3",
                     "businessKey": "Backup_20180918_201510",
                     "definitionId": "test_deployment.--.1.44.7.--"
                                     ".BackupDeployment__top",
                     "definitionName": "Backup Deployment"}

ACTIVE_WORKFLOWS = [{"instanceId": "c41f2879-b20f-11e8-898e-fa163eae81b2",
                     "businessKey": "ENM Upgrade",
                     "definitionId": "test_deployment.--.1.45.11.--"
                                     ".UpgradeGenerateReport_1",
                     "definitionName": "UpgradeGenerateReport",
                     "active": True},
                    {"instanceId": "060898ba-b342-11e8-898e-fa163eae81b2",
                     "businessKey": "staging01_20180908_0833_201809"
                                    "08093440716196",
                     "definitionId": "test_deployment.--.1.45.11.--"
                                     ".CreateCinderSnap_new__top",
                     "definitionName": "SnapVolume",
                     "active": True},
                    {"instanceId": "06ae74fa-b342-11e8-898e-fa163eae81b2",
                     "businessKey": "staging01_20180908_0833_201809"
                                    "08093440707902",
                     "definitionId": "test_deployment.--.1.45.11.--"
                                     ".ReadCloudConfigAndAuthenticate",
                     "definitionName": "ReadCloudConfigAndAuthenticate",
                     "active": True}]

INACTIVE_WORKFLOWS = [{"instanceId": "c41f2879-b20f-11e8-898e-fa163eae81b2",
                       "businessKey": "ENM Upgrade",
                       "definitionId": "test_deployment.--.1.45.11.--"
                                       ".UpgradeGenerateReport_1",
                       "definitionName": "UpgradeGenerateReport",
                       "active": False},
                      {"instanceId": "060898ba-b342-11e8-898e-fa163eae81b2",
                       "businessKey": "staging01_20180908_0833_201809"
                                      "08093440716196",
                       "definitionId": "test_deployment.--.1.45.11.--"
                                       ".CreateCinderSnap_new__top",
                       "definitionName": "SnapVolume",
                       "active": False},
                      {"instanceId": "06ae74fa-b342-11e8-898e-fa163eae81b2",
                       "businessKey": "staging01_20180908_0833_201809"
                                      "08093440707902",
                       "definitionId": "test_deployment.--.1.45.11.--"
                                       ".HandleServiceSnapShots_new",
                       "definitionName": "HandleServiceSnapShots",
                       "active": False}]

CANDIDATES_WF = [{"instanceId": "d18d3b50-b341-11e8-898e-fa163eae81b2",
                  "businessKey": "Backup_20180908_083312",
                  "definitionId": "test_deployment.--.1.45.11.--"
                                  ".BackupDeployment__top",
                  "definitionName": "Backup Deployment", "active": True},
                 {"instanceId": "cfc9920a-b20e-11e8-898e-fa163eae81b2",
                  "businessKey": "ENM Upgrade_1536244512_Staging"
                                 "01_ENM1810IP2_06092018",
                  "definitionId": "test_deployment.--.1.45.11.--"
                                  ".deploy_stack__top",
                  "definitionName": "ENM Initial Install", "active": True},
                 {"instanceId": "2f5188db-47c2-11e8-9e8c-fa163e394bbb",
                  "businessKey": "Rollback Deployment_1524575935",
                  "definitionId": "test_deployment.--.1.33.2.--"
                                  ".RollbackDeployment__top",
                  "definitionName": "Rollback Deployment", "active": True},
                 {"instanceId": "7f8e7a1e-b1e9-11e8-898e-fa163eae81b2",
                  "businessKey": "Backup_1536244512_Staging01_EN"
                                 "M1810IP2_06092018",
                  "definitionId": "test_deployment.--.1.45.11.--"
                                  ".ReadSed_BuildDeployment_1",
                  "definitionName": "Restore Deployment", "active": True},
                 {"instanceId": "c41f2879-b20f-11e8-898e-fa163eae81b2",
                  "businessKey": "ENM Upgrade",
                  "definitionId": "test_deployment.--.1.45.11.--"
                                  ".UpgradeGenerateReport_1",
                  "definitionName": "UpgradeGenerateReport", "active": True},
                 {"instanceId": "060898ba-b342-11e8-898e-fa163eae81b2",
                  "businessKey": "staging01_20180908_0833_201809"
                                 "08093440716196",
                  "definitionId": "test_deployment.--.1.45.11.--"
                                  ".CreateCinderSnap_new__top",
                  "definitionName": "SnapVolume", "active": True},
                 {"instanceId": "06ae74fa-b342-11e8-898e-fa163eae81b2",
                  "businessKey": "staging01_20180908_0833_201809"
                                 "08093440707902",
                  "definitionId": "test_deployment.--.1.45.11.--"
                                  ".HandleServiceSnapShots_new",
                  "definitionName": "HandleServiceSnapShots", "active": True}]

OTHER_CANDIDATES = [{"instanceId": "cfc9920a-b20e-11e8-898e-fa163eae81b2",
                     "businessKey": "ENM Upgrade_1536244512_Staging"
                                    "01_ENM1810IP2_06092018",
                     "definitionId": "test_deployment.--.1.45.11.--"
                                     ".deploy_stack__top",
                     "definitionName": "ENM Initial Install", "active": True},
                    {"instanceId": "2f5188db-47c2-11e8-9e8c-fa163e394bbb",
                     "businessKey": "Rollback Deployment_1524575935",
                     "definitionId": "test_deployment.--.1.33.2.--"
                                     ".RollbackDeployment__top",
                     "definitionName": "Rollback Deployment", "active": True},
                    {"instanceId": "7f8e7a1e-b1e9-11e8-898e-fa163eae81b2",
                     "businessKey": "Backup_1536244512_Staging01_EN"
                                    "M1810IP2_06092018",
                     "definitionId": "test_deployment.--.1.45.11.--"
                                     ".ReadSed_BuildDeployment_1",
                     "definitionName": "Restore Deployment", "active": True}]

WORKFLOWS = [{"instanceId": "c41f2879-b20f-11e8-898e-fa163eae81b2",
              "businessKey": "ENM Upgrade",
              "definitionId": "test_deployment.--.1.45.11.--"
                              ".UpgradeGenerateReport_1",
              "definitionName": "UpgradeGenerateReport", "active": False},
             {"instanceId": "060898ba-b342-11e8-898e-fa163eae81b2",
              "businessKey": "staging01_20180908_0833_20180908093440716196",
              "definitionId": "test_deployment.--.1.45.11.--"
                              ".CreateCinderSnap_new__top",
              "definitionName": "SnapVolume", "active": False},
             {"instanceId": "06ae74fa-b342-11e8-898e-fa163eae81b2",
              "businessKey": "staging01_20180908_0833_20180908093440707902",
              "definitionId": "test_deployment.--.1.45.11.--"
                              ".ReadCloudConfigAndAuthenticate",
              "definitionName": "ReadCloudConfigAndAuthenticate",
              "active": False},
             {"instanceId": "cfc9920a-b20e-11e8-898e-fa163eae81b2",
              "businessKey": "ENM Upgrade_1536244512_Staging"
                             "01_ENM1810IP2_06092018",
              "definitionId": "test_deployment.--.1.45.11.--"
                              ".deploy_stack__top",
              "definitionName": "ENM Initial Install", "active": False},
             {"instanceId": "2f5188db-47c2-11e8-9e8c-fa163e394bbb",
              "businessKey": "Rollback Deployment_1524575935",
              "definitionId": "test_deployment.--.1.33.2.--"
                              ".RollbackDeployment__top",
              "definitionName": "Rollback Deployment", "active": True}]

LOG_WORKFLOW_INSTANCE = {"instanceId": "d8fdd15c-09c1-487a-a7d0-365863f814d3",
                         "businessKey": "Backup_20180918_201510",
                         "definitionId": "test_deployment.--.1.44.7.--"
                                         ".BackupDeployment__top",
                         "definitionName": "Backup Deployment",
                         "startTime": "2018-09-08T09:38:51.878Z",
                         "endTime": "2018-09-08T09:39:10.721Z",
                         "active": False,
                         "incidentActive": False,
                         "startedByUser": None,
                         "lastPNodeId": None,
                         "endNodeId": "EndEvent_10213m5",
                         "endNodeType": "noneEndEvent",
                         "aborted": False,
                         "abortedByUser": None,
                         "incidentTime": None}


class WFTypesGetWorkflowsTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    def test_check_logging(self, mock_log):
        """
        Test checks if the info log is being submitted.
        :param mock_log: mocking the log object
        """
        wf_object = workflows.WfTypes('fake_lcm', mock_log)
        wf_object.get_backup_validation_wf_id()

        call = mock.call('Getting workflow ID from workflow URL: %s',
                         'http://fake_lcm/wfs/rest/definitions')

        self.assertTrue(call in mock_log.info.mock_calls)

    @mock.patch(MOCK_LOG)
    def test_failed_workflows(self, mock_log):
        """
        Test checks if the error log is being submitted when no workflow is
        returned.
        :param mock_log: mocking the log object
        """
        wf_object = workflows.WfTypes('fake_lcm', mock_log)
        wf_object.get_backup_validation_wf_id()

        call = mock.call("Failed to get workflows")

        self.assertTrue(call in mock_log.error.mock_calls)


class WFTypesCheckWorkflowsTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_validation_backups(self, mock_request, mock_log):
        """
        Test if the last valid backup workflow is returned
        :param mock_request: mocking the get request
        :param mock_log: mocking the log object
        """
        wf_object = workflows.WfTypes('fake_lcm', mock_log)

        mock_request.return_value = BACKUP_WORKFLOWS

        result = wf_object.get_backup_validation_wf_id()
        expected = 'test_deployment.--.1.45.11.--.BackupValidation__top'
        self.assertEqual(expected, result)


class WFTypesCheckValidationTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_no_validation_backups(self, mock_request, mock_log):
        """
        Test checks if None is returned when there is not a backup workflow
        and the error log is submitted
        :param mock_request: mocking the get request
        :param mock_log: mocking the log object
        """
        wf_object = workflows.WfTypes('fake_lcm', mock_log)

        mock_request.return_value = OTHER_WORKFLOWS
        call = mock.call("Failed to find backup validation workflow")

        result = wf_object.get_backup_validation_wf_id()

        self.assertTrue(call in mock_log.error.mock_calls)
        self.assertIsNone(result)


class WFInstancesGetWorkflowsTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_retrieve_workflows(self, mock_request, mock_log):
        """
        Test to check if the workflows are returned and if the correct info
        log is called
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        mock_request.return_value = BACKUP_WORKFLOWS

        call = mock.call("Retrieved workflows")

        result = wf_instance.get_wfs_from_lcm()

        self.assertTrue(call in mock_log.info.mock_calls)
        self.assertTrue(result)


class WFInstancesFailedGetWorkflowsTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    def test_fail_retrieve_workflows(self, mock_log):
        """
        Failure test to check if the error log is called
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        call = mock.call("Failed to get workflows from %s" % 'fake_lcm')

        result = wf_instance.get_wfs_from_lcm()

        self.assertTrue(call in mock_log.error.mock_calls)
        self.assertFalse(result)


class WFInstancesValidateBackupTestCase(unittest.TestCase):

    def setUp(self):
        """
        Set up test constants
        """
        self.backup_id = 'test_deployment.--.1.45.11.--.BackupValidation__top'
        self.instance_id = 'd8fdd15c-09c1-487a-a7d0-365863f814d3'

    @mock.patch(MOCK_WF_TYPES)
    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_POST_REQUEST)
    def test_validate_workflow_id(self, mock_request, mock_log, mock_wft):
        """
        Test to check if the workflow is being validated
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        :param mock_wft: mocking the WFType object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        ret = self.backup_id
        mock_wft.return_value.get_backup_validation_wf_id.return_value = ret
        mock_request.return_value = WORKFLOW_INSTANCE
        call = mock.call('Backup validation started with instance ID %s.',
                         self.instance_id)

        result = wf_instance.start_validate_backup_wf('fake_tag')

        self.assertEqual(self.instance_id, result)
        self.assertTrue(call in mock_log.info.mock_calls)


class WFInstancesValidateBackupNoIdTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    def test_no_workflow_id(self, mock_log):
        """
        Failure test to check if the right error log is called when no id is
        returned
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        call = mock.call("Failed to get workflow id")

        result = wf_instance.start_validate_backup_wf('fake_tag')

        self.assertIsNone(result)
        self.assertTrue(call in mock_log.error.mock_calls)


class WFInstancesBackupPostFailedTestCase(unittest.TestCase):

    def setUp(self):
        """
        Set up test constants
        """
        self.backup_id = 'test_deployment.--.1.45.11.--.BackupValidation__top'

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_WF_TYPES)
    def test_failed_post(self, mock_wft, mock_log):
        """
        Failure test to check if the error log is called when the validation
        cannot be started
        :param mock_wft:
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        ret = self.backup_id
        mock_wft.return_value.get_backup_validation_wf_id.return_value = ret
        call = mock.call("Failed to start backup validation workflow")

        result = wf_instance.start_validate_backup_wf('fake_tag')

        self.assertIsNone(result)
        self.assertTrue(call in mock_log.error.mock_calls)


class WFInstancesReturnActiveWorkflowsTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_return_actives_workflow(self, mock_request, mock_log):
        """
        Test to check if the active workflows are returned
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        mock_request.return_value = ACTIVE_WORKFLOWS

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.active_wfs()

        self.assertIsNotNone(result)


class WFInstancesNoActiveWorkflowsTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_no_active_workflow(self, mock_request, mock_log):
        """
        Test to check if no workflow is returned when they are all inactive
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        mock_request.return_value = INACTIVE_WORKFLOWS

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.active_wfs()

        self.assertTrue(len(result) == 0)


class WFInstancesReturnActiveStorageTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_return_actives_workflow(self, mock_request, mock_log):
        """
        Test to check if the active workflows that fits the criteria are
        returned
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        :return:
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        mock_request.return_value = CANDIDATES_WF

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.active_storage_wfs()

        self.assertTrue(len(result) == 4)


class WFInstanceReturnBackupActiveTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_active_backup_workflow(self, mock_request, mock_log):
        """
        Test to check if only the Backup workflow is returned
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        mock_request.return_value = CANDIDATES_WF

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.active_backup_wfs()

        self.assertTrue(len(result) == 1)


class WFInstanceNoReturnBackupActiveTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_return_no_workflow(self, mock_request, mock_log):
        """
        Test to check if no workflow is returned when there is no Backup
        workflow
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        mock_request.return_value = OTHER_CANDIDATES

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.active_backup_wfs()

        self.assertTrue(len(result) == 0)

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_return_inactive_workflow(self, mock_request, mock_log):
        """
        Test to check if no workflow is returned when there is no active
        Backup workflow
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        mock_request.return_value = INACTIVE_WORKFLOWS

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.active_backup_wfs()

        self.assertTrue(len(result) == 0)


class WFInstanceWorkflowByIdTestCase(unittest.TestCase):

    def setUp(self):
        """
        Set up the test constants
        """
        self.instance_id = '060898ba-b342-11e8-898e-fa163eae81b2'

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_return_workflow(self, mock_request, mock_log):
        """
        Test to check if the correct workflow is returned when checking the
        instance id
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        mock_request.return_value = WORKFLOWS

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.get_wf_by_id(self.instance_id)

        self.assertEqual(result[workflows.WfInstances.IID], self.instance_id)


class WFInstanceNoWorkflowByIdTestCase(unittest.TestCase):

    def setUp(self):
        """
        Set up the test constants
        """
        self.instance_id = '060898ba-b342-11e8-898e-fa163eae81asd'

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_return_no_workflow(self, mock_request, mock_log):
        """
        Test to check if None is returned when there isn't an workflow
        with the informed instance id
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)

        mock_request.return_value = WORKFLOWS

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.get_wf_by_id(self.instance_id)

        self.assertIsNone(result)


class WFInstanceGetWorkflowByTypeTestCase(unittest.TestCase):

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_get_active_workflow(self, mock_request, mock_log):
        """
        Test to check if None is returned when there isn't an workflow
        with the informed instance id
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)
        mock_request.return_value = WORKFLOWS

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.get_wf_by_type(workflows.WfInstances.ROLLBACK)

        self.assertEquals(result[0]['definitionName'],
                          workflows.WfInstances.ROLLBACK)
        self.assertEquals(result[0]['active'], True)
        self.assertEquals(len(result), 1)

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_GET_REQUEST)
    def test_get_inactive_workflow(self, mock_request, mock_log):
        """
        Test to check if None is returned when there isn't an workflow
        with the informed instance id
        :param mock_request: mocking the workflow return from get request
        :param mock_log: mocking the log object
        """
        wf_instance = workflows.WfInstances('fake_lcm', mock_log)
        mock_request.return_value = WORKFLOWS

        wf_instance.get_wfs_from_lcm()
        result = wf_instance.get_wf_by_type(workflows.WfInstances.INSTALL,
                                            active=False)

        self.assertEquals(result[0]['definitionName'],
                          workflows.WfInstances.INSTALL)
        self.assertEquals(result[0]['active'], False)
        self.assertEquals(len(result), 1)


class LogWorkflowTestCase(unittest.TestCase):

    def setUp(self):
        """
        Set up the test constants
        """
        self.workflow = LOG_WORKFLOW_INSTANCE

    @mock.patch(MOCK_PACKAGE + 'LOG')
    def test_log_workflow(self, mock_log):
        """
        Test to check if all the information asked by the log
        calls are being logged correctly
        :param mock_log: mocking the log object
        """
        call_1 = mock.call("Workflow: %s (%s)" % (
            self.workflow[workflows.WfInstances.NAME],
            self.workflow[workflows.WfInstances.IID]))

        call_2 = mock.call("Start:    %s  End: %s" % (
            self.workflow[workflows.WfInstances.START],
            self.workflow[workflows.WfInstances.END]))

        call_3 = mock.call("Active:   %s (Aborted: %s, Incident: %s)" % (
            self.workflow[workflows.WfInstances.ACTIVE],
            self.workflow[workflows.WfInstances.ABORTED],
            self.workflow[workflows.WfInstances.INCIDENT]))

        calls = [call_1, call_2, call_3]

        workflows.log_wf(self.workflow)
        mock_log.info.assert_has_calls(calls)


class LogWorkflowErrorTestCase(unittest.TestCase):

    def setUp(self):
        """
        Set up the test constants
        """
        self.workflow = WORKFLOW_INSTANCE

    def test_log_workflow(self):
        """
        Raise exception test when one of the information asked by
        the log object isn't within the workflow object
        """
        with self.assertRaises(KeyError):
            workflows.log_wf(self.workflow)
