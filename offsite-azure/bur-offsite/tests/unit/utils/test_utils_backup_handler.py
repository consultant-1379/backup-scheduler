##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""The purpose of this module is to provide unit testing for backup_handler.py utility script."""

import unittest

import mock

import backup.constants as constants
import backup.utils.backup_handler as backup_handler

MOCK_PACKAGE = 'backup.utils.backup_handler.'
MOCK_LOGGER_PACKAGE = 'backup.logger.CustomLogger'

MOCK_CUSTOMER_NAME = "mock_customer"
MOCK_TEMP_BACKUP_PATH = 'mock_tmp_bkp_path'
MOCK_REMOTE_BACKUP_PATH = 'mock_remote_bkp_path'
MOCK_LOCAL_BACKUP_PATH = 'mock_local_bkp_path'
MOCK_DOWNLOAD_BACKUP_PATH = 'mock_download_bkp_path'
MOCK_TAR_VOLUME_FILE = 'mock_volume.tar'

MOCK_HOST = 'localhost'


def get_mock_logger():
    """Get a mock logger object."""
    with mock.patch(MOCK_LOGGER_PACKAGE) as mock_logger:
        mock_logger.log_root_path = ""
        mock_logger.log_file_name = ""

    return mock_logger


class BackupHandlerCheckLocalDiskSpaceForUpload(unittest.TestCase):
    """Test cases for check_local_disk_space_for_upload inside backup_handler script."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    @mock.patch(MOCK_PACKAGE + 'get_size_on_disk')
    @mock.patch(MOCK_PACKAGE + 'get_free_disk_space')
    def test_check_local_disk_space_for_upload_should_succeed(
            self, mock_get_free_disk_space, mock_get_size_on_disk):
        """Test when there is available space to perform the backup upload."""
        mock_free_disk_space = 2000
        mock_bkp_size = 1000

        mock_get_free_disk_space.return_value = mock_free_disk_space
        mock_get_size_on_disk.return_value = mock_bkp_size

        calls = [mock.call("Required space to store temporary backup data in '{}': {}{}. Available "
                           "space {}{}.".format(MOCK_TEMP_BACKUP_PATH,
                                                mock_bkp_size,
                                                constants.BLOCK_SIZE_MB_STR,
                                                mock_free_disk_space,
                                                constants.BLOCK_SIZE_MB_STR))]
        sut_expect_result = True

        sut_result = backup_handler.check_local_disk_space_for_upload(
            MOCK_LOCAL_BACKUP_PATH, MOCK_TEMP_BACKUP_PATH, self.mock_logger)

        self.assertEqual(sut_expect_result, sut_result)

        self.mock_logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'get_size_on_disk')
    @mock.patch(MOCK_PACKAGE + 'get_free_disk_space')
    def test_check_local_disk_space_for_upload_no_space(
            self, mock_get_free_disk_space, mock_get_size_on_disk):
        """Test when there is no space left to perform the backup upload."""
        mock_free_disk_space = 1000
        mock_bkp_size = 2000

        mock_get_free_disk_space.return_value = mock_free_disk_space
        mock_get_size_on_disk.return_value = mock_bkp_size

        expected_exception_msg = "Path doesn't have enough disk space for backup."

        with self.assertRaises(Exception) as raised:
            backup_handler.check_local_disk_space_for_upload(
                MOCK_LOCAL_BACKUP_PATH, MOCK_TEMP_BACKUP_PATH, self.mock_logger)

        self.assertIn(expected_exception_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'get_free_disk_space')
    def test_check_local_disk_space_for_upload_invalid_temp_path(
            self, mock_get_free_disk_space):
        """Test when the informed temporary path is not valid."""
        exp_message = 'Mock exception message'
        mock_get_free_disk_space.side_effect = Exception(exp_message)

        with self.assertRaises(Exception) as ex:
            backup_handler.check_local_disk_space_for_upload(
                MOCK_LOCAL_BACKUP_PATH, MOCK_TEMP_BACKUP_PATH, self.mock_logger)

        self.assertEqual(exp_message, ex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'get_size_on_disk')
    @mock.patch(MOCK_PACKAGE + 'get_free_disk_space')
    def test_check_local_disk_space_for_upload_invalid_backup_path(
            self, mock_get_free_disk_space, mock_get_size_on_disk):
        """Test when the informed backup path is not valid."""
        mock_get_free_disk_space.return_value = ''

        exp_message = 'Mock exception message'
        mock_get_size_on_disk.side_effect = Exception(exp_message)

        with self.assertRaises(Exception) as ex:
            backup_handler.check_local_disk_space_for_upload(
                MOCK_LOCAL_BACKUP_PATH, MOCK_TEMP_BACKUP_PATH, self.mock_logger)

        self.assertEqual(exp_message, ex.exception.message)


class BackupHandlerCheckLocalDiskSpaceForDownload(unittest.TestCase):
    """Test cases for check_local_disk_space_for_download inside backup_handler script."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    @mock.patch(MOCK_PACKAGE + 'get_remote_folder_size')
    @mock.patch(MOCK_PACKAGE + 'get_free_disk_space')
    def test_check_local_disk_space_for_download_should_succeed(
            self, mock_get_free_disk_space, mock_get_remote_folder_size):
        """Test when there is available space to perform the backup download."""
        mock_free_disk_space = 2000
        mock_remote_folder_size = 1000

        mock_get_free_disk_space.return_value = mock_free_disk_space
        mock_get_remote_folder_size.return_value = mock_remote_folder_size

        calls = [mock.call("Required space to download backup '{}': {}{}. Available space {}{}."
                           .format(MOCK_REMOTE_BACKUP_PATH,
                                   mock_remote_folder_size,
                                   constants.BLOCK_SIZE_MB_STR,
                                   mock_free_disk_space,
                                   constants.BLOCK_SIZE_MB_STR))]
        sut_expect_result = True

        sut_result = backup_handler.check_local_disk_space_for_download(
            MOCK_REMOTE_BACKUP_PATH, MOCK_HOST, MOCK_DOWNLOAD_BACKUP_PATH, self.mock_logger)

        self.mock_logger.info.assert_has_calls(calls)

        self.assertEqual(sut_expect_result, sut_result)

    @mock.patch(MOCK_PACKAGE + 'get_remote_folder_size')
    @mock.patch(MOCK_PACKAGE + 'get_free_disk_space')
    def test_check_local_disk_space_for_download_no_space(
            self, mock_get_free_disk_space, mock_get_remote_folder_size):
        """Test when there is no space left to perform the backup download."""
        mock_free_disk_space = 1000
        mock_remote_folder_size = 2000

        mock_get_free_disk_space.return_value = mock_free_disk_space
        mock_get_remote_folder_size.return_value = mock_remote_folder_size

        expected_exception_msg = "Path doesn't have enough disk space for backup."

        with self.assertRaises(Exception) as raised:
            backup_handler.check_local_disk_space_for_download(
                MOCK_REMOTE_BACKUP_PATH, MOCK_HOST, MOCK_DOWNLOAD_BACKUP_PATH, self.mock_logger)

        self.assertIn(expected_exception_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'get_free_disk_space')
    def test_check_local_disk_space_for_download_invalid_download_path(
            self, mock_get_free_disk_space):
        """Test when the informed download path is not valid."""
        exp_message = 'Mock exception message'
        mock_get_free_disk_space.side_effect = Exception(exp_message)

        with self.assertRaises(Exception) as ex:
            backup_handler.check_local_disk_space_for_download(
                MOCK_REMOTE_BACKUP_PATH, MOCK_HOST, MOCK_DOWNLOAD_BACKUP_PATH, self.mock_logger)

        self.assertEqual(exp_message, ex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'get_remote_folder_size')
    @mock.patch(MOCK_PACKAGE + 'get_free_disk_space')
    def test_check_local_disk_space_for_download_invalid_remote_path(
            self, mock_get_free_disk_space, mock_get_remote_folder_size):
        """Test when the informed backup remote path is not valid."""
        mock_get_free_disk_space.return_value = ''

        exp_message = 'Mock exception message'
        mock_get_remote_folder_size.side_effect = Exception(exp_message)

        with self.assertRaises(Exception) as ex:
            backup_handler.check_local_disk_space_for_download(
                MOCK_REMOTE_BACKUP_PATH, MOCK_HOST, MOCK_DOWNLOAD_BACKUP_PATH, self.mock_logger)

        self.assertEqual(exp_message, ex.exception.message)


class BackupHandlerValidateBackupPerVolume(unittest.TestCase):
    """Test cases for validate_backup_per_volume inside backup_handler script."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_validate_backup_per_volume_empty_backup(self, mock_os):
        """Test when the backup path is empty."""
        mock_os.path.exists.return_value = True
        mock_os.listdir.return_value = []

        val_result = backup_handler.validate_backup_per_volume(
            MOCK_CUSTOMER_NAME, MOCK_LOCAL_BACKUP_PATH, self.mock_logger)

        self.assertFalse(val_result, "Should have returned False.")

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_validate_backup_per_volume_no_success_flag(self, mock_os):
        """Test when the backup flag does not exist."""
        mock_os.path.exists.side_effect = [True, False]
        mock_os.listdir.return_value = ['volume0', 'volume1']
        mock_os.path.join.return_value = ''

        val_result = backup_handler.validate_backup_per_volume(
            MOCK_CUSTOMER_NAME, MOCK_LOCAL_BACKUP_PATH, self.mock_logger)

        self.assertFalse(val_result, "Should have returned False.")

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_validate_backup_per_volume_file_found(self, mock_os):
        """Test when there are not expected files inside the backup folder.."""
        mock_os.path.exists.side_effect = [True, False]
        mock_os.listdir.side_effect = [['volume0', 'volume1'], ['file0', 'file1']]
        mock_os.path.join.return_value = ''
        mock_os.path.isdir.return_value = True

        val_result = backup_handler.validate_backup_per_volume(
            MOCK_CUSTOMER_NAME, MOCK_LOCAL_BACKUP_PATH, self.mock_logger)

        self.assertFalse(val_result, "Should have returned False.")

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_validate_backup_per_volume_empty_volume(self, mock_os):
        """Test when the backup flag does not exist."""
        mock_os.path.exists.side_effect = [True, False]
        mock_os.listdir.side_effect = [['volume0', 'volume1'], []]
        mock_os.path.join.return_value = ''
        mock_os.path.isdir.return_value = True

        val_result = backup_handler.validate_backup_per_volume(
            MOCK_CUSTOMER_NAME, MOCK_LOCAL_BACKUP_PATH, self.mock_logger)

        self.assertFalse(val_result, "Should have returned False.")

    @mock.patch(MOCK_PACKAGE + 'validate_volume_metadata')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_validate_backup_per_volume_invalid_metadata(
            self, mock_os, mock_validate_volume_metadata):
        """Test when the metadata validation fails."""
        mock_os.path.exists.side_effect = [True, False]
        mock_os.listdir.side_effect = [['volume0', 'volume1'], ['file0', 'file1']]
        mock_os.path.join.return_value = ''
        mock_os.path.isdir.return_value = True
        mock_validate_volume_metadata.return_value = False

        sut_result = backup_handler.validate_backup_per_volume(
            MOCK_CUSTOMER_NAME, MOCK_LOCAL_BACKUP_PATH, self.mock_logger)

        self.assertFalse(sut_result)

    @mock.patch(MOCK_PACKAGE + 'is_backup_ok_valid')
    @mock.patch(MOCK_PACKAGE + 'is_backup_volume_valid')
    @mock.patch(MOCK_PACKAGE + 'report_unexpected_files_presence')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_validate_backup_per_volume_successful_case(
            self, mock_os, mock_report_unexpected_files_presence,
            mock_is_backup_volume_valid, mock_is_backup_ok_valid):
        """Test a successful metadata validation."""
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = True
        mock_is_backup_volume_valid.return_value = True
        mock_is_backup_ok_valid.return_value = True
        mock_report_unexpected_files_presence.return_value = None
        mock_os.listdir.side_effect = [['volume0', 'volume1'], ['file0', 'file1'],
                                       ['file0', 'file1']]

        val_result = backup_handler.validate_backup_per_volume(
            MOCK_CUSTOMER_NAME, MOCK_LOCAL_BACKUP_PATH, self.mock_logger)

        self.assertTrue(val_result, "Should have returned True.")

    @mock.patch(MOCK_PACKAGE + 'is_backup_ok_valid')
    @mock.patch(MOCK_PACKAGE + 'report_unexpected_files_presence')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_validate_backup_per_volume_success_flag_not_found_genie_vol_bkp(
            self, mock_os, mock_report_unexpected_files_presence,
            mock_is_backup_ok_valid):
        """Test when the backup flag does not exist for the genie_vol_bkp."""
        mock_os.listdir.return_value = []
        mock_report_unexpected_files_presence.return_value = None
        mock_is_backup_ok_valid.return_value = False
        val_result = backup_handler.validate_backup_per_volume(
            constants.GENIE_VOL_BKPS_DEPLOYMENT, MOCK_LOCAL_BACKUP_PATH, self.mock_logger)
        mock_backup_structure = {'files': [], 'folders': []}
        validation_call = [mock.call(MOCK_LOCAL_BACKUP_PATH, mock_backup_structure,
                                     self.mock_logger)]
        mock_is_backup_ok_valid.assert_has_calls(validation_call)
        self.assertFalse(val_result, "Should have returned False.")

    @mock.patch(MOCK_PACKAGE + 'is_backup_ok_valid')
    @mock.patch(MOCK_PACKAGE + 'report_unexpected_files_presence')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_validate_backup_per_volume_success_flag_found_genie_vol_bkp(
            self, mock_os, mock_report_unexpected_files_presence,
            mock_is_backup_ok_valid):
        """Test when the backup flag does exist for the genie_vol_bkp."""
        mock_os.listdir.return_value = []
        mock_report_unexpected_files_presence.return_value = None
        mock_is_backup_ok_valid.return_value = True
        val_result = backup_handler.validate_backup_per_volume(
            constants.GENIE_VOL_BKPS_DEPLOYMENT, MOCK_LOCAL_BACKUP_PATH, self.mock_logger)
        mock_backup_structure = {'files': [], 'folders': []}
        validation_call = [mock.call(MOCK_LOCAL_BACKUP_PATH, mock_backup_structure,
                                     self.mock_logger)]
        mock_is_backup_ok_valid.assert_has_calls(validation_call)
        self.assertTrue(val_result, "Should have returned True.")


class BackupHandlerReportUnexpectedFilesPresence(unittest.TestCase):
    """Test cases for report_unexpected_files_presence inside backup_handler script."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    def test_report_unexpected_files_inside_tag_directory(self):
        """Report Unnecessary files as a warning log message while validating."""
        sut_unnecessary_file_name = 'some_file'
        sut_backup_structure = {'files': [constants.SUCCESS_FLAG_FILE, sut_unnecessary_file_name]}

        calls = [mock.call("Unexpected files found: {}".format([sut_unnecessary_file_name]))]

        sut_return = backup_handler.report_unexpected_files_presence(sut_backup_structure,
                                                                     self.mock_logger)

        self.assertIsNone(sut_return)
        self.mock_logger.warning.assert_has_calls(calls)

    def test_no_unexpected_files_inside_tag_directory_should_not_log(self):
        """Report Unnecessary files should not log a warning when no unexpected file."""
        sut_backup_structure = {'files': [constants.SUCCESS_FLAG_FILE]}

        expected_warning_log_content = []

        sut_return = backup_handler.report_unexpected_files_presence(sut_backup_structure,
                                                                     self.mock_logger)

        self.assertIsNone(sut_return)
        self.mock_logger.warning.assert_has_calls(expected_warning_log_content)


class BackupHandlerIsBackupOkValid(unittest.TestCase):
    """Test cases for is_backup_ok_valid inside backup_handler script."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    def test_backup_ok_should_be_validated_successfully(self):
        """Test validating the existence of BACKUP OK file."""
        sut_customer_tag_path = '/path/to/customer/tag/folder'
        sut_backup_structure = {'files': [constants.SUCCESS_FLAG_FILE]}

        sut_result = backup_handler.is_backup_ok_valid(sut_customer_tag_path,
                                                       sut_backup_structure,
                                                       self.mock_logger)

        self.assertTrue(sut_result)

    def test_backup_ok_not_found_should_log_issue(self):
        """Log warning message when a backup ok not exist."""
        sut_customer_tag_path = '/path/to/customer/tag/folder'
        sut_backup_structure = {'files': [constants.BACKUP_META_FILE]}
        calls = [mock.call("Backup '{}' does not have a success flag."
                           .format(sut_customer_tag_path))]

        sut_result = backup_handler.is_backup_ok_valid(sut_customer_tag_path,
                                                       sut_backup_structure,
                                                       self.mock_logger)

        self.assertFalse(sut_result)
        self.mock_logger.warning.assert_has_calls(calls)


class BackupHandlerIsCustomerBackupPathExist(unittest.TestCase):
    """Test cases for is_customer_backup_path_exist inside backup_handler script."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    @mock.patch(MOCK_PACKAGE + 'os.path.exists')
    def test_is_customer_backup_valid_should_succeed(self, mock_os_path_exists):
        """Validate successfully when the customer backup exists."""
        mock_os_path_exists.return_value = True
        sut_customer_tag_path = '/path/to/customer/tag/folder'
        sut_result = backup_handler.is_customer_backup_path_exist(sut_customer_tag_path,
                                                                  self.mock_logger)

        self.assertTrue(sut_result)

    @mock.patch(MOCK_PACKAGE + 'os.path.exists')
    def test_is_customer_backup_invalid_should_log(self, mock_os_path_exists):
        """Test the logging warning message when customer backup not exist."""
        mock_os_path_exists.return_value = False
        sut_customer_tag_path = '/path/to/customer/tag/folder'
        calls = [mock.call("Backup path '{}' does not exist."
                           .format(sut_customer_tag_path))]

        sut_result = backup_handler.is_customer_backup_path_exist(sut_customer_tag_path,
                                                                  self.mock_logger)

        self.assertFalse(sut_result)
        self.mock_logger.warning.assert_has_calls(calls)


class BackupHandlerGetVolumeMetadataFile(unittest.TestCase):
    """Test cases for get_volume_metadata_file inside backup_handler script."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    @mock.patch(MOCK_PACKAGE + 'glob.glob')
    def test_get_volume_metadata_file_should_return_metadata_file(self, mock_glob):
        """Test capability to find and return meta file in a volume."""
        sut_meta_file = ['/path/to/meta/file/1_backup_metadata']
        sut_customer_tag_path = '/path/to/customer/tag/folder'
        mock_glob.return_value = sut_meta_file

        sut_result = backup_handler.get_volume_metadata_file(sut_customer_tag_path,
                                                             self.mock_logger)

        self.assertEqual(sut_meta_file.pop(), sut_result)

    @mock.patch(MOCK_PACKAGE + 'glob.glob')
    def test_not_existing_metadata_file_get_volume_metadata_file_should_log_issue(self, mock_glob):
        """Test capability to log issue when meta file not in a volume."""
        sut_customer_tag_path = '/path/to/customer/tag/folder'
        mock_glob.return_value = []
        calls = [mock.call("Cannot recognize metadata file in volume: '{}'"
                           .format(sut_customer_tag_path))]

        sut_result = backup_handler.get_volume_metadata_file(sut_customer_tag_path,
                                                             self.mock_logger)

        self.assertIsNone(sut_result)
        self.mock_logger.error.assert_has_calls(calls)


class BackupHandlerGetMetadataFileJson(unittest.TestCase):
    """Test cases for get_metadata_file_json inside backup_handler script."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    @mock.patch(MOCK_PACKAGE + 'json.load')
    @mock.patch(MOCK_PACKAGE + 'get_volume_metadata_file')
    def test_get_metadata_file_json_should_return_json(self, mock_get_volume_metadata_file,
                                                       mock_json):
        """Return meta file in json format in a valid condition."""
        sut_json_meta_data = {'test': 'test_value'}
        sut_customer_tag_path = '/path/to/customer/tag/folder'
        sut_meta_file = '/path/to/meta/file/1_backup_metadata'

        mock_get_volume_metadata_file.return_value = sut_meta_file
        mock_json.return_value = sut_json_meta_data
        with mock.patch("__builtin__.open",
                        mock.mock_open()):
            sut_result = backup_handler.get_metadata_file_json(sut_customer_tag_path,
                                                               self.mock_logger)
            self.assertEqual(sut_json_meta_data, sut_result)

    @mock.patch(MOCK_PACKAGE + 'json.load')
    @mock.patch(MOCK_PACKAGE + 'get_volume_metadata_file')
    def test_invalid_metadata_file_should_raise_exception_and_log(self,
                                                                  mock_get_volume_metadata_file,
                                                                  mock_json):
        """Return exception occurred in loading meta file."""
        sut_customer_tag_path = '/path/to/customer/tag/folder'
        sut_meta_file = '/path/to/meta/file/1_backup_metadata'

        mock_get_volume_metadata_file.return_value = sut_meta_file
        sut_exception_msg = 'message'
        mock_json.side_effect = ValueError(sut_exception_msg)
        calls = [mock.call("Metadata error: Could not parse metadata file '{}'. Cause: {}."
                           .format(sut_meta_file, sut_exception_msg))]

        with mock.patch("__builtin__.open",
                        mock.mock_open()):
            sut_result = backup_handler.get_metadata_file_json(sut_customer_tag_path,
                                                               self.mock_logger)
            self.assertIsNone(sut_result)
            self.mock_logger.error.assert_has_calls(calls)


class BackupHandlerValidateMetadataContent(unittest.TestCase):
    """Test cases for validate_metadata_content inside backup_handler script."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    @mock.patch(MOCK_PACKAGE + 'os.listdir')
    def test_validate_metadata_content_should_succeed(self, mock_os_listdir):
        """Test validating metadata content with fine structure."""
        sut_customer_volume_path = '/path/to/customer/back/volume1'
        mock_os_listdir.return_value = ['volume_file1.dat', 'volume_file0.dat',
                                        '1_backup_sha256file', 'volume_file2.dat',
                                        '1_backup_metadata']
        sut_metadata_json = {constants.META_DATA_KEYS.objects.name: [
            {'volume_file1.dat': {
                'length': 102400,
                'offset': 0,
                'compression': 'none',
                'md5': '1'}}, {
                    'volume_file0.dat': {
                        'length': 102400,
                        'offset': 0,
                        'compression': 'none',
                        'md5': '1'}},
            {
                'volume_file2.dat': {
                    'length': 102400,
                    'offset': 0,
                    'compression': 'none',
                    'md5': '1'}}]}

        sut_result = backup_handler.validate_metadata_content(sut_customer_volume_path,
                                                              sut_metadata_json,
                                                              self.mock_logger)

        self.assertTrue(sut_result)

    @mock.patch(MOCK_PACKAGE + 'os.listdir')
    def test_validate_malformed_metadata_content_should_log(self, mock_os_listdir):
        """Test error log message for a malformed meta data."""
        sut_customer_volume_path = '/path/to/customer/back/volume1'
        mock_os_listdir.return_value = ['volume_file1.dat', 'volume_file0.dat',
                                        '1_backup_sha256file', 'volume_file2.dat',
                                        '1_backup_metadata']
        sut_metadata_json = {constants.META_DATA_KEYS.objects.name: [
            {'volume_file1.dat': {'length': 102400, 'offset': 0,
                                  'compression': 'none',
                                  'md5': '1'},
             'problematic_key': 'problematic_value'
             },
            {
                'volume_file0.dat': {'length': 102400, 'offset': 0,
                                     'compression': 'none',
                                     'md5': '1'}
            },
            {
                'volume_file2.dat': {'length': 102400, 'offset': 0,
                                     'compression': 'none',
                                     'md5': '1'}
            }]}
        calls = [mock.call("Metadata error: File entry is malformed.")]

        sut_result = backup_handler.validate_metadata_content(sut_customer_volume_path,
                                                              sut_metadata_json,
                                                              self.mock_logger)

        self.assertFalse(sut_result)
        self.mock_logger.error.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'os.listdir')
    def test_invalidate_metadata_content_should_log(self, mock_os_listdir):
        """Test when an item inside metadata not found in filesystem."""
        sut_customer_volume_path = '/path/to/customer/back/volume1'
        sut_not_existing_volume = 'volume_not_exist_name'
        sut_metadata_list = [sut_not_existing_volume, 'volume_file0.dat',
                             '1_backup_sha256file', 'volume_file2.dat',
                             '1_backup_metadata']
        mock_os_listdir.return_value = sut_metadata_list
        sut_metadata_json = {constants.META_DATA_KEYS.objects.name: [
            {'volume_file1.dat': {'length': 102400, 'offset': 0,
                                  'compression': 'none',
                                  'md5': '1'}
             },
            {
                'volume_file0.dat': {'length': 102400, 'offset': 0,
                                     'compression': 'none',
                                     'md5': '1'}
            },
            {
                'volume_file2.dat': {'length': 102400, 'offset': 0,
                                     'compression': 'none',
                                     'md5': '1'}
            }]}
        calls = [mock.call("Metadata item {} not found inside volume {}"
                           .format(sut_metadata_json[constants.META_DATA_KEYS.objects.name][0],
                                   repr(sut_metadata_list)))]

        sut_result = backup_handler.validate_metadata_content(sut_customer_volume_path,
                                                              sut_metadata_json,
                                                              self.mock_logger)

        self.assertFalse(sut_result)
        self.mock_logger.error.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'os.listdir')
    def test_absent_md5_in_metadata_content_should_log(self, mock_os_listdir):
        """Test error log message when md5 key is not in the metadata."""
        sut_customer_volume_path = '/path/to/customer/back/volume1'
        sut_metadata_list = ['volume_file1.dat', 'volume_file0.dat',
                             '1_backup_sha256file', 'volume_file2.dat',
                             '1_backup_metadata']
        mock_os_listdir.return_value = sut_metadata_list
        sut_metadata_json = {constants.META_DATA_KEYS.objects.name: [
            {'volume_file1.dat': {'length': 102400, 'offset': 0,
                                  'compression': 'none'
                                  }
             },
            {
                'volume_file0.dat': {'length': 102400, 'offset': 0,
                                     'compression': 'none',
                                     'md5': '1'}
            },
            {
                'volume_file2.dat': {'length': 102400, 'offset': 0,
                                     'compression': 'none',
                                     'md5': '1'}
            }]}
        calls = [mock.call("Metadata error: Missing key {} for file {}."
                           .format(constants.META_DATA_KEYS.md5.name,
                                   sut_metadata_json[constants.META_DATA_KEYS.objects.name]))]

        sut_result = backup_handler.validate_metadata_content(sut_customer_volume_path,
                                                              sut_metadata_json,
                                                              self.mock_logger)

        self.assertFalse(sut_result)
        self.mock_logger.error.assert_has_calls(calls)
