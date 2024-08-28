##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=invalid-name,no-name-in-module

"""BUR system-wide 'Download' operation testing."""

import os
import unittest

from tests.system.scenario_simulator.constants import LAYOUT_DICT
from tests.system.utils.base_test_case import SystemTestBaseClass
from tests.system.utils.constants import BUR_SIM_ENV_PATH, CUSTOMER_FOLDER_PREFIX, \
    CUSTOMER_FOLDER_PREFIX_NFS, MOCK_OFFSITE_RELATIVE_PATH, NFS_FOLDER_NAME, RESTORE_FOLDER_NAME
import tests.system.utils.helpers as helpers
from tests.system.utils.helpers import create_bur_env_layout, find_file, finish_test_module, \
    start_up_test_module
from tests.system.utils.system_test_assert import SystemTestAssertions

from backup.constants import BUR_FILE_LIST_DESCRIPTOR_FILE_NAME, \
    BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME, SUCCESS_FLAG_FILE
from backup.main import EXIT_CODES, SUCCESS_EXIT_CODE


def setUpModule():
    """Create custom BUR system log path once the process started."""
    start_up_test_module(__name__)


def tearDownModule():
    """Remove custom BUR system log path when finishing the process."""
    finish_test_module(__name__)


class TestBurDownloadOperationSystemWide(SystemTestBaseClass, SystemTestAssertions):
    """System bur application Testing for upload operation."""

    def setUp(self):
        """
        Set up the environment.

        Print test name, create filesystem layout and perform an upload of the customer under test.
        """
        valid_scenario_layout = LAYOUT_DICT['valid_filesystem_layout']
        self.plan = create_bur_env_layout(self._testMethodName, valid_scenario_layout)

        self.env_customer_id = '0'
        helpers.default_upload_operation(self.env_customer_id)

    def test_valid_scenario_should_succeed(self):
        """Download operation should be successful under a valid scenario."""
        sut_backup_tag = '2018-12-04'
        download_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        op_exit_code = helpers.download_operation(self.env_customer_id, sut_backup_tag,
                                                  download_path)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)

        backup_path = os.path.join(BUR_SIM_ENV_PATH,
                                   NFS_FOLDER_NAME,
                                   CUSTOMER_FOLDER_PREFIX_NFS +
                                   self.env_customer_id,
                                   sut_backup_tag)

        self.assert_downloaded_backup_is_valid(backup_path, download_path,
                                               sut_backup_tag, self.env_customer_id)

    def test_no_tag_in_backup_should_log_issue(self):
        """Check log message to find issue related to tag."""
        sut_backup_tag = '2018-12-05'

        download_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        with self.assertRaises(SystemExit) as sut_exit_code:
            helpers.download_operation(self.env_customer_id, sut_backup_tag, download_path)

        self.assertEqual(EXIT_CODES.FAILED_DOWNLOAD.value, sut_exit_code.exception.code)

    def test_empty_tag_specific_customer_should_search_backups(self):
        """Check if it gets the list of backups of one customer when no backup tag is informed."""
        download_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        ret = helpers.download_operation(self.env_customer_id, "", download_path)

        self.assertEqual(SUCCESS_EXIT_CODE, ret)

    def test_empty_tag_and_customer_should_search_backups(self):
        """Check if it gets the list of backups of all customers when no tag/customer are given."""
        download_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        ret = helpers.download_operation("", "", download_path)

        self.assertEqual(SUCCESS_EXIT_CODE, ret)

    def test_without_bur_file_list_descriptor_should_exit(self):
        """Download operation on bur file list descriptor missing should raise exception."""
        sut_backup_tag = '2018-12-04'

        azure_mock_path_to_customer_folder = os.path.join(BUR_SIM_ENV_PATH,
                                                          MOCK_OFFSITE_RELATIVE_PATH,
                                                          CUSTOMER_FOLDER_PREFIX +
                                                          self.env_customer_id, sut_backup_tag)

        descriptor = find_file(azure_mock_path_to_customer_folder,
                               BUR_FILE_LIST_DESCRIPTOR_FILE_NAME)
        os.remove(descriptor)

        download_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        with self.assertRaises(SystemExit) as sut_exit_code:
            helpers.download_operation(self.env_customer_id, sut_backup_tag, download_path)

        self.assertEqual(EXIT_CODES.FAILED_DOWNLOAD.value, sut_exit_code.exception.code)

    def test_without_vol_file_list_descriptor_should_exit(self):
        """Download operation on vol file list descriptor missing should raise exception."""
        sut_backup_tag = '2018-12-04'

        azure_mock_path_to_customer_folder = os.path.join(BUR_SIM_ENV_PATH,
                                                          MOCK_OFFSITE_RELATIVE_PATH,
                                                          CUSTOMER_FOLDER_PREFIX +
                                                          self.env_customer_id, sut_backup_tag)

        descriptor = find_file(azure_mock_path_to_customer_folder,
                               BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME)
        os.remove(descriptor)

        download_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        with self.assertRaises(SystemExit) as sut_exit_code:
            helpers.download_operation(self.env_customer_id, sut_backup_tag, download_path)

        self.assertEqual(EXIT_CODES.FAILED_DOWNLOAD.value, sut_exit_code.exception.code)

    def test_without_ok_file_list_descriptor_should_exit(self):
        """Download operation on backup_ok file list descriptor missing should raise exception."""
        sut_backup_tag = '2018-12-04'

        azure_mock_path_to_customer_folder = os.path.join(BUR_SIM_ENV_PATH,
                                                          MOCK_OFFSITE_RELATIVE_PATH,
                                                          CUSTOMER_FOLDER_PREFIX +
                                                          self.env_customer_id, sut_backup_tag)

        success_flag_file = find_file(azure_mock_path_to_customer_folder,
                                      SUCCESS_FLAG_FILE)
        os.remove(success_flag_file)

        download_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        with self.assertRaises(SystemExit) as sut_exit_code:
            helpers.download_operation(self.env_customer_id, sut_backup_tag, download_path)

        self.assertEqual(EXIT_CODES.FAILED_DOWNLOAD.value, sut_exit_code.exception.code)


class TestRecoverFromInterruptionInDownloadAllVolumesDownloaded(SystemTestBaseClass,
                                                                SystemTestAssertions):
    """Testing capability of the BUR to recover from an interrupted download operation."""

    def setUp(self):
        """
        Set up the environment.

        Print test name, create filesystem layout and perform an upload of the customer under test.
        """
        interrupted_scenario = LAYOUT_DICT['interrupted_download_all_vols_downloaded_layout']
        create_bur_env_layout(self._testMethodName, interrupted_scenario)

        self.env_customer_id = '0'
        helpers.default_upload_operation(self.env_customer_id)

    def test_resume_interrupted_upload_should_recover(self):
        """
        Recover from an interrupted download.

        In this case all volumes were already downloaded.
        """
        sut_backup_tag = '2018-12-03'
        restore_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        op_exit_code = helpers.download_operation(self.env_customer_id, sut_backup_tag,
                                                  restore_path)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)


class TestRecoverFromInterruptionInDownloadAllVolumesFinished(SystemTestBaseClass,
                                                              SystemTestAssertions):
    """Testing capability of the BUR to recover from an interrupted download operation."""

    def setUp(self):
        """
        Set up the environment.

        Print test name, create filesystem layout and perform an upload of the customer under test.
        """
        interrupted_scenario = LAYOUT_DICT['interrupted_download_all_vols_finished_layout']
        create_bur_env_layout(self._testMethodName, interrupted_scenario)

        self.env_customer_id = '0'
        helpers.default_upload_operation(self.env_customer_id)

    def test_resume_interrupted_download_all_vols_finished(self):
        """
        Recover from an interrupted download.

        In this case all volumes were already downloaded and processed.
        """
        sut_backup_tag = '2018-12-03'
        restore_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        op_exit_code = helpers.download_operation(self.env_customer_id, sut_backup_tag,
                                                  restore_path)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)


class TestRecoverFromInterruptionInDownloadPendingVolumes(SystemTestBaseClass,
                                                          SystemTestAssertions):
    """Testing capability of the BUR to recover from an interrupted download operation."""

    def setUp(self):
        """
        Set up the environment.

        Print test name, create filesystem layout and perform an upload of the customer under test.
        """
        interrupted_scenario = LAYOUT_DICT['interrupted_download_vols_fin_down_pen_layout']
        create_bur_env_layout(self._testMethodName, interrupted_scenario)

        self.env_customer_id = '0'
        helpers.default_upload_operation(self.env_customer_id)

    def test_resume_interrupted_download_finished_downloaded_pending(self):
        """
        Recover from an interrupted download.

        In this case, volume0 was finished successfully, volume1 should be processed and volume2
        should be downloaded.
        """
        sut_backup_tag = '2018-12-03'
        restore_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        op_exit_code = helpers.download_operation(self.env_customer_id, sut_backup_tag,
                                                  restore_path)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)


class TestRecoverFromInterruptionInDownloadBackupOkDownloadedPendingVolumes(SystemTestBaseClass,
                                                                            SystemTestAssertions):
    """Testing capability of the BUR to recover from an interrupted download operation."""

    def setUp(self):
        """
        Set up the environment.

        Print test name, create filesystem layout and perform an upload of the customer under test.
        """
        interrupted_scenario = LAYOUT_DICT['interrupted_download_backup_ok_fin_missing_vols_layout']
        create_bur_env_layout(self._testMethodName, interrupted_scenario)

        self.env_customer_id = '0'
        helpers.default_upload_operation(self.env_customer_id)

    def test_resume_interrupted_download_missing_volumes(self):
        """
        Recover from an interrupted download.

        In this case, volume0 was finished successfully, volume1 should be processed and volume2
        should be downloaded and processed, even with backup ok tag already downloaded.
        """
        sut_backup_tag = '2018-12-03'
        restore_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        op_exit_code = helpers.download_operation(self.env_customer_id, sut_backup_tag,
                                                  restore_path)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)


class TestRecoverFromInterruptionInDownloadBackupOkDownloadedNoVolumes(SystemTestBaseClass,
                                                                       SystemTestAssertions):
    """Testing capability of the BUR to recover from an interrupted download operation."""

    def setUp(self):
        """
        Set up the environment.

        Print test name, create filesystem layout and perform an upload of the customer under test.
        """
        interrupted_scenario = LAYOUT_DICT[
            'interrupted_download_backup_ok_fin_missing_all_vols_layout']
        create_bur_env_layout(self._testMethodName, interrupted_scenario)

        self.env_customer_id = '0'
        helpers.default_upload_operation(self.env_customer_id)

    def test_resume_interrupted_download_missing_all_volumes(self):
        """
        Recover from an interrupted download.

        In this case, all volumes should be downloaded and processed, even with backup ok tag
        already downloaded.
        """
        sut_backup_tag = '2018-12-03'
        restore_path = os.path.join(BUR_SIM_ENV_PATH, RESTORE_FOLDER_NAME)

        op_exit_code = helpers.download_operation(self.env_customer_id, sut_backup_tag,
                                                  restore_path)

        self.assertEqual(SUCCESS_EXIT_CODE, op_exit_code)


if __name__ == "__main__":
    unittest.main()
