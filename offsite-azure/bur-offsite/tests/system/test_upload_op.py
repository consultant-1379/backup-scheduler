##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=invalid-name

"""BUR system-wide 'Upload' operation testing."""

import unittest

import mock
from tests.system.scenario_simulator.constants import LAYOUT_DICT, SIM_PLAN_FILES
from tests.system.utils.base_test_case import SystemTestBaseClass
from tests.system.utils.constants import BUR_SIM_ENV_PATH, MOCK_BASE_PACKAGE
import tests.system.utils.helpers as helpers
from tests.system.utils.helpers import create_bur_env_layout, finish_test_module, \
    start_up_test_module
from tests.system.utils.system_test_assert import SystemTestAssertions

from backup.main import EXIT_CODES, main, SUCCESS_EXIT_CODE


def setUpModule():
    """Create custom BUR system log path once the process started."""
    start_up_test_module(__name__)


def tearDownModule():
    """Remove custom BUR system log path when finishing the process."""
    finish_test_module(__name__)


class TestValidBurUploadOperationSystemWide(SystemTestBaseClass, SystemTestAssertions):
    """System bur application Testing for upload operation."""

    CUSTOMER_NUMBER_IN_VALID_SCENARIO = 2

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        valid_scenario_layout = LAYOUT_DICT['valid_filesystem_layout']
        self.plan = create_bur_env_layout(self._testMethodName, valid_scenario_layout)

    def test_customer_name_should_succeed(self):
        """Upload operation should be successful under a valid scenario."""
        sut_customer_id = 0
        sut_return_code = helpers.default_upload_operation(str(sut_customer_id))

        self.assertEqual(SUCCESS_EXIT_CODE, sut_return_code)
        self.assert_files_on_azure_are_valid(BUR_SIM_ENV_PATH,
                                             self.plan[SIM_PLAN_FILES],
                                             sut_customer_id)

    def test_customer_name_should_upload_all(self):
        """Check if all customers files are uploaded when no customer name."""
        sut_return_code = helpers.upload_operation_no_customer()

        self.assertEqual(SUCCESS_EXIT_CODE, sut_return_code)
        for customer_id in range(0, self.CUSTOMER_NUMBER_IN_VALID_SCENARIO):
            self.assert_files_on_azure_are_valid(BUR_SIM_ENV_PATH,
                                                 self.plan[SIM_PLAN_FILES],
                                                 customer_id)


class TestInvalidBurUploadOperationSystemWide(SystemTestBaseClass, SystemTestAssertions):
    """System invalid bur application Testing for upload operation."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        invalid_scenario_layout = LAYOUT_DICT['invalid_filesystem_layout']
        self.plan = create_bur_env_layout(self._testMethodName, invalid_scenario_layout)

    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'sys', 'exit']))
    def test_wrong_customer_name_should_fail(self, mock_sys_exit):
        """Upload operation with not existing customer name should raise exception."""
        wrong_customer_name = 'CUSTOMER_3'
        mock_sys_exit.return_value = {}
        with self.assertRaises(KeyError):
            helpers.default_upload_operation(wrong_customer_name)

    def test_customer_empty_backup_should_succeed(self):
        """Upload operation when there is no backup should gracefully log issue."""
        sut_customer_id = '0'

        with self.assertRaises(SystemExit) as ex:
            helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(EXIT_CODES.FAILED_VALIDATION.value, ex.exception.code)

    def test_wrong_option_number_should_fail(self):
        """Check Exit code when wrong script code given in cli."""
        wrong_script_option = '655'
        argument_options = [
            '--script_option', wrong_script_option,
            '--customer_name', "CUSTOMER_0",
            '--rsync_ssh', 'True']

        sut_expected_exit_code = 0

        with self.assertRaises(SystemExit) as sut_exit_ex:
            main(argument_options)

        self.assertEqual(sut_expected_exit_code, sut_exit_ex.exception.code)


class TestBurRetentionAfterUploadValidBackups(SystemTestBaseClass, SystemTestAssertions):
    """Testing retention policy for a customer when all backups are valid on offsite."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        retention_scenario_layout = LAYOUT_DICT['retention_valid_filesystem_layout']
        self.plan = create_bur_env_layout(self._testMethodName, retention_scenario_layout)

    def test_offsite_retention_as_part_of_upload(self):
        """Check if the retention only preserves the last 4 backups."""
        sut_customer_id = '0'

        op_exit_code = helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)

        self.assert_retention_is_valid(sut_customer_id)

        expected_bkp_list = ['2018-12-04', '2018-12-05', '2018-12-06', '2018-12-07']

        self.assert_backups_exist(sut_customer_id, expected_bkp_list)


class TestBurRetentionAfterUploadValidBackupsNoRemoval(SystemTestBaseClass, SystemTestAssertions):
    """Testing retention policy for a customer when it already complies with the retention."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        retention_scenario_layout = LAYOUT_DICT[
            'retention_valid_backups_no_delete_filesystem_layout']
        self.plan = create_bur_env_layout(self._testMethodName, retention_scenario_layout)

    def test_offsite_retention_as_part_of_upload(self):
        """Check if the retention preserves the last 4 backups without deleting anything."""
        sut_customer_id = '0'

        op_exit_code = helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)

        self.assert_retention_is_valid(sut_customer_id)

        expected_bkp_list = ['2018-12-03', '2018-12-04', '2018-12-05', '2018-12-06']

        self.assert_backups_exist(sut_customer_id, expected_bkp_list)


class TestBurRetentionAfterUploadEmptyBackup(SystemTestBaseClass, SystemTestAssertions):
    """Testing retention policy for a customer when at least one backup is empty on offsite."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        retention_scenario_layout = LAYOUT_DICT['retention_empty_backup_filesystem_layout']
        self.plan = create_bur_env_layout(self._testMethodName, retention_scenario_layout)

    def test_offsite_retention_as_part_of_upload(self):
        """Check if the retention only preserves the last not empty 4 backups."""
        sut_customer_id = '0'

        op_exit_code = helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)

        self.assert_retention_is_valid(sut_customer_id)

        expected_bkp_list = ['2018-12-04', '2018-12-05', '2018-12-06', '2018-12-07']

        self.assert_backups_exist(sut_customer_id, expected_bkp_list)


class TestBurRetentionAfterUploadAllEmptyBackup(SystemTestBaseClass, SystemTestAssertions):
    """Testing retention policy for a customer when all previous backups are empty on offsite."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        retention_scenario_layout = LAYOUT_DICT['retention_all_empty_backup_filesystem_layout']
        self.plan = create_bur_env_layout(self._testMethodName, retention_scenario_layout)

    def test_offsite_retention_as_part_of_upload(self):
        """Check if the retention preserves the last not empty backup."""
        sut_customer_id = '0'

        op_exit_code = helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)

        expected_num_bkp_offsite = 1

        self.assert_retention_is_valid(sut_customer_id, expected_num_bkp_offsite)

        expected_bkp_list = ['2018-12-06']

        self.assert_backups_exist(sut_customer_id, expected_bkp_list)


class TestBurRetentionAfterUploadIncompleteBackup(SystemTestBaseClass, SystemTestAssertions):
    """Testing retention policy for a customer when it has incomplete backups on offsite."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        retention_scenario_layout = LAYOUT_DICT['retention_incomplete_backup_filesystem_layout']
        self.plan = create_bur_env_layout(self._testMethodName, retention_scenario_layout)

    def test_offsite_retention_as_part_of_upload(self):
        """Check if the retention preserves the last 4 backups, one of them the last uploaded."""
        sut_customer_id = '0'

        op_exit_code = helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)

        self.assert_retention_is_valid(sut_customer_id)

        expected_bkp_list = ['2018-12-06']

        self.assert_backups_exist(sut_customer_id, expected_bkp_list)


class TestBurRetentionAfterUploadNoBackup(SystemTestBaseClass, SystemTestAssertions):
    """Testing retention policy when there is no backup on offsite."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        retention_scenario_layout = LAYOUT_DICT['retention_no_backup_filesystem_layout']
        self.plan = create_bur_env_layout(self._testMethodName, retention_scenario_layout)

    def test_offsite_retention_standalone(self):
        """Check if the retention is not applied."""
        op_exit_code = helpers.retention_operation()

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)

        expected_num_bkp_offsite = 0

        sut_customer_id = '0'
        self.assert_retention_is_valid(sut_customer_id, expected_num_bkp_offsite)

        sut_customer_id = '1'
        self.assert_retention_is_valid(sut_customer_id, expected_num_bkp_offsite)


class TestRecoverFromInterruptionInUploadAllVolumesProcessed(SystemTestBaseClass,
                                                             SystemTestAssertions):
    """Testing capability of the BUR to recover from an interrupted upload operation."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        interrupted_scenario = LAYOUT_DICT['interrupted_upload_all_vols_processed_layout']
        self.plan = create_bur_env_layout(self._testMethodName, interrupted_scenario)

    def test_resume_interrupted_upload_all_volumes_processed(self):
        """Resume an interrupted upload when all volumes are already processed."""
        sut_customer_id = '0'

        sut_return_code = helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(SUCCESS_EXIT_CODE, sut_return_code)
        self.assert_backup_temp_is_empty(sut_customer_id)
        self.assert_files_on_azure_are_valid(BUR_SIM_ENV_PATH,
                                             self.plan[SIM_PLAN_FILES],
                                             int(sut_customer_id))


class TestRecoverFromInterruptionInUploadAllVolumesUnfinished(SystemTestBaseClass,
                                                              SystemTestAssertions):
    """Testing capability of the BUR to recover from an interrupted upload operation."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        interrupted_scenario = LAYOUT_DICT['interrupted_upload_all_vols_unfinished_layout']
        self.plan = create_bur_env_layout(self._testMethodName, interrupted_scenario)

    def test_resume_interrupted_upload_all_volumes_unfinished(self):
        """Resume an interrupted upload when all volumes are unfinished."""
        sut_customer_id = '0'

        sut_return_code = helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(SUCCESS_EXIT_CODE, sut_return_code)
        self.assert_backup_temp_is_empty(sut_customer_id)
        self.assert_files_on_azure_are_valid(BUR_SIM_ENV_PATH,
                                             self.plan[SIM_PLAN_FILES],
                                             int(sut_customer_id))


class TestRecoverFromInterruptionInUploadAllVolumesUploaded(SystemTestBaseClass,
                                                            SystemTestAssertions):
    """Testing capability of the BUR to recover from an interrupted upload operation."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        interrupted_scenario = LAYOUT_DICT['interrupted_upload_all_vols_uploaded_layout']
        self.plan = create_bur_env_layout(self._testMethodName, interrupted_scenario)

    def test_resume_interrupted_upload_all_volumes_uploaded(self):
        """Resume an interrupted upload when all volumes are already uploaded."""
        sut_customer_id = '0'

        sut_return_code = helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(SUCCESS_EXIT_CODE, sut_return_code)
        self.assert_backup_temp_is_empty(sut_customer_id)
        self.assert_files_on_azure_are_valid(BUR_SIM_ENV_PATH,
                                             self.plan[SIM_PLAN_FILES],
                                             int(sut_customer_id))


class TestRecoverFromInterruptionInUploadPendingVolumes(SystemTestBaseClass, SystemTestAssertions):
    """Testing capability of the BUR to recover from an interrupted upload operation."""

    def setUp(self):
        """Print test name before execution and create filesystem layout."""
        interrupted_scenario = LAYOUT_DICT['interrupted_upload_vols_up_proc_unf_layout']
        self.plan = create_bur_env_layout(self._testMethodName, interrupted_scenario)

    def test_resume_interrupted_upload_volumes_up_proc_unf(self):
        """Resume an upload when there are volumes uploaded, processed and unfinished."""
        sut_customer_id = '0'

        sut_return_code = helpers.default_upload_operation(sut_customer_id)

        self.assertEqual(SUCCESS_EXIT_CODE, sut_return_code)
        self.assert_backup_temp_is_empty(sut_customer_id)
        self.assert_files_on_azure_are_valid(BUR_SIM_ENV_PATH,
                                             self.plan[SIM_PLAN_FILES],
                                             int(sut_customer_id))


if __name__ == "__main__":
    unittest.main()
