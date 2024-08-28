##############################################################################
# COPYRIGHT Ericsson AB 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=too-many-lines,too-many-arguments

"""Module for testing backup/offsite_backup_handler.py script."""

import collections
import unittest

import mock

from backup.backup_settings import EnmConfig
from backup.constants import VOLUME_OUTPUT_KEYS
from backup.exceptions import DownloadBackupException, ExceptionCodes, RsyncException, \
    UtilsException
from backup.offsite_backup_handler import download_volume_from_offsite, OffsiteBackupHandler, \
    unwrapper_process_volume_function
from backup.utils.decorator import get_undecorated_class_method

MOCK_PACKAGE = 'backup.offsite_backup_handler.'

CONF_FILE_NAME = 'config.cfg'

MOCK_REMOTE_DIR = 'mock_remote_dir'
MOCK_CUSTOMER_NAME = 'mock_customer'
MOCK_BKP_DESTINATION = 'mock_bkp_dest'
MOCK_BKP_TAG = 'mock_bkp_tag'
MOCK_BKP_PATH = 'mock_bkp_path'
MOCK_BKP_DOWNLOAD = 'mock_download_bkp'
MOCK_VOLUME = 'mock_volume'
MOCK_VOLUME_LIST_DESCRIPTOR_FILE_PATH = 'mock_volume_list_descriptor_file'
MOCK_FILE_LIST_DESCRIPTOR_FILE_PATH = 'mock_file_list_descriptor_file'
MOCK_SUCCESS_FLAG = 'mock_success_flag'
MOCK_FILE = 'mock_file'
MOCK_RETENTION = 4

NUMBER_THREADS = 1
NUMBER_PROCESSORS = 1
NUMBER_TRANSFER_PROCESSORS = 1


def create_offsite_bkp_object():
    """Create an OffsiteBackupHandler object for tests."""
    with mock.patch('backup.gnupg_manager.GnupgManager') as mock_gnupg_manager:
        with mock.patch('backup.gnupg_manager.GPG') as mock_gpg:
            mock_gnupg_manager.gpg_handler.side_effect = mock_gpg

    with mock.patch('backup.backup_settings.EnmConfig') as enm_config:
        customer_config_dict = {MOCK_CUSTOMER_NAME, enm_config}

    with mock.patch('backup.backup_settings.OffsiteConfig') as mock_offsite_config:
        offsite_config = mock_offsite_config

    with mock.patch(MOCK_PACKAGE + 'CustomLogger') as logger:
        with mock.patch(MOCK_PACKAGE + 'dill.dumps'):
            offsite_bkp_handler = OffsiteBackupHandler(mock_gnupg_manager,
                                                       offsite_config,
                                                       customer_config_dict,
                                                       NUMBER_THREADS,
                                                       NUMBER_PROCESSORS,
                                                       NUMBER_TRANSFER_PROCESSORS,
                                                       logger)
    return offsite_bkp_handler


class OffsiteBkpHandlerDownloadVolumeFromOffsiteTestCase(unittest.TestCase):
    """Class to test download_volume_from_offsite() method."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    def test_download_volume_from_offsite_transfer_exception(self, mock_transfer_file):
        """Test the raise of the exception and return value if transfer fails."""
        mock_transfer_file.side_effect = RsyncException(
            ExceptionCodes.RsyncTransferNumberFilesDiffer)

        error_message = "Error while downloading volume. " \
                        "Error Code 63. Number of files transferred differs " \
                        "from files on origin path and destination path."

        result = download_volume_from_offsite(MOCK_VOLUME, MOCK_VOLUME, MOCK_BKP_PATH,
                                              MOCK_BKP_DESTINATION)

        self.assertEqual(MOCK_VOLUME, result[0])
        self.assertEqual(MOCK_VOLUME, result[1])
        self.assertEqual(error_message, result[2]['output'])
        self.assertEqual(MOCK_BKP_DESTINATION, result[3])

    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    def test_download_volume_from_offsite_return_value(self, mock_transfer_file):
        """Test the return value for successful scenario."""
        rsync_sample_output = (11, 11, 1, 1, 12, 1)

        mock_transfer_file.return_value = rsync_sample_output

        volume_output_expected_result = dict()

        volume_output_expected_result[
            VOLUME_OUTPUT_KEYS.status.name] = True
        volume_output_expected_result[
            VOLUME_OUTPUT_KEYS.rsync_output.name] = rsync_sample_output
        volume_output_expected_result[
            VOLUME_OUTPUT_KEYS.transfer_time.name] = 0.0

        result = download_volume_from_offsite(MOCK_VOLUME, MOCK_VOLUME, MOCK_BKP_PATH,
                                              MOCK_BKP_DESTINATION)

        self.assertEqual(MOCK_VOLUME, result[0])
        self.assertEqual(MOCK_VOLUME, result[1])
        self.assertEqual(dict, type(result[2]))
        self.assertEqual(volume_output_expected_result, result[2])
        self.assertEqual(MOCK_BKP_DESTINATION, result[3])


class OffsiteBkpHandlerUnwrapperProcessVolumeTestCase(unittest.TestCase):
    """Test cases for unwrapper_local_backup_handler_function function."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'dill.loads')
    def test_unwrapper_process_volume_function_invalid_instance_exception(
            self, mock_dill_loads):
        """Test when an invalid instance of offsite_backup_handler is loaded by dill."""
        mock_dill_loads.return_value = None
        expected_error_msg = "Could not unwrap backup handler object."

        with self.assertRaises(DownloadBackupException) as cex:
            unwrapper_process_volume_function(None, '')

        self.assertEqual(expected_error_msg, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.process_volume')
    @mock.patch(MOCK_PACKAGE + 'dill.loads')
    def test_unwrapper_process_volume_function_valid_instance(
            self, mock_dill_loads, mock_process_volume):
        """Test when a valid instance of offsite backup handler is loaded by dill."""
        mock_process_volume.return_value = None
        self.offsite_bkp_handler.process_volume = mock_process_volume

        mock_dill_loads.return_value = self.offsite_bkp_handler

        result = unwrapper_process_volume_function(self.offsite_bkp_handler, '')

        self.assertIsNone(result, "Should have returned None.")


class OffsiteBkpHandlerExecuteDownloadBkpFromOffsiteTestCase(unittest.TestCase):
    """Class to test execute_download_backup_from_offsite method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    def test_execute_download_backup_from_offsite_empty_bkp_tag_exception(self):
        """Test to check the raise of exception if backup tag is empty."""
        with self.assertRaises(UtilsException) as raised:
            self.offsite_bkp_handler.execute_download_backup_from_offsite(
                MOCK_CUSTOMER_NAME, "", MOCK_BKP_DESTINATION)

        self.assertEqual("Value not informed.", raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_offsite_backup_dict')
    @mock.patch(MOCK_PACKAGE + 'get_values_from_dict')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_execute_download_backup_from_offsite_bkp_tag_exception(self, mock_os,
                                                                    mock_get_values_from_dict,
                                                                    mock_get_offsite_bkp):
        """Test to check the raise of exception if backup tag is not found."""
        enm_config = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION)
        self.offsite_bkp_handler.customer_config_dict = {MOCK_CUSTOMER_NAME: enm_config}
        mock_get_offsite_bkp.return_value = collections.OrderedDict()
        mock_os.path.join.return_value = MOCK_BKP_DESTINATION
        mock_get_values_from_dict.return_value = None
        expected_error_msg = "Backup tag not found. (mock_bkp_tag)"

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_bkp_handler.execute_download_backup_from_offsite(
                MOCK_CUSTOMER_NAME, MOCK_BKP_TAG, MOCK_BKP_DESTINATION)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.validate_backup_destination')
    @mock.patch(MOCK_PACKAGE + 'find_elem_dict')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_offsite_backup_dict')
    @mock.patch(MOCK_PACKAGE + 'get_values_from_dict')
    def test_execute_download_backup_from_offsite_download_failure(self,
                                                                   mock_get_values_from_dict,
                                                                   mock_get_offsite_bkp,
                                                                   mock_find_elem_dict,
                                                                   mock_validate_backup_destination
                                                                   ):
        """Test to check the raise of exception if backup download fails and the warning message."""
        mock_get_values_from_dict.return_value = None
        mock_get_offsite_bkp.return_value = collections.OrderedDict()
        mock_find_elem_dict.return_value = (MOCK_CUSTOMER_NAME, MOCK_BKP_PATH)
        mock_validate_backup_destination.side_effect = DownloadBackupException(
            ExceptionCodes.CannotCreatePath)
        expected_error_msg = "Path informed cannot be created."

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_bkp_handler.execute_download_backup_from_offsite(
                MOCK_CUSTOMER_NAME, MOCK_BKP_TAG, MOCK_BKP_DESTINATION)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.download_process_backup')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.validate_backup_destination')
    @mock.patch(MOCK_PACKAGE + 'find_elem_dict')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_offsite_backup_dict')
    @mock.patch(MOCK_PACKAGE + 'get_values_from_dict')
    def test_execute_download_backup_from_offsite_download_return_value(
            self, mock_get_values_from_dict, mock_get_offsite_bkp, mock_find_elem_dict,
            mock_validate_backup_destination, mock_download_process_backup):
        """Test to check the return value and info log for the successful scenario."""
        mock_get_values_from_dict.return_value = None
        mock_get_offsite_bkp.return_value = collections.OrderedDict()
        mock_find_elem_dict.return_value = (MOCK_CUSTOMER_NAME, MOCK_BKP_PATH)
        mock_validate_backup_destination.return_value = MOCK_BKP_DESTINATION

        mock_download_process_backup.return_value = (MOCK_BKP_TAG, {}, (11, 11, 1, 1, 12, 1), 0.01)

        self.assertTrue(self.offsite_bkp_handler.execute_download_backup_from_offsite(
            MOCK_CUSTOMER_NAME, MOCK_BKP_TAG, MOCK_BKP_DESTINATION))


class OffsiteBkpHandlerValidateBkpDestinationTestCase(unittest.TestCase):
    """Class to test validate_backup_destination() method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'create_path')
    def test_validate_backup_destination_empty_warning(self, mock_create_path):
        """Test to check the warning log and return value in backup destination is empty."""
        enm_config = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION)
        self.offsite_bkp_handler.customer_config_dict = {MOCK_CUSTOMER_NAME: enm_config}

        calls = [mock.call("Backup destination not informed. Default location 'mock_bkp_dest' "
                           "used")]

        mock_create_path.return_value = True

        self.assertEqual(MOCK_BKP_DESTINATION,
                         self.offsite_bkp_handler.validate_backup_destination(MOCK_CUSTOMER_NAME))

        self.offsite_bkp_handler.logger.warning.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_validate_backup_destination_return_value(self, mock_os, mock_create_path):
        """Test to check the return value in backup destination is not empty."""
        mock_os.path.join.return_value = MOCK_BKP_DESTINATION

        enm_config = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION)
        self.offsite_bkp_handler.customer_config_dict = {MOCK_CUSTOMER_NAME: enm_config}

        mock_create_path.return_value = True

        result = self.offsite_bkp_handler.validate_backup_destination(MOCK_CUSTOMER_NAME)
        self.assertEqual(MOCK_BKP_DESTINATION, result)


class OffsiteBkpHandlerGetOffsiteBkpDictTestCase(unittest.TestCase):
    """Class for testing get_offsite_backup_dict() method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'run_ssh_command')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_offsite_bkp_dict_none_config_return_value(self, mock_os, mock_run_remote_command):
        """Test the info log and the return value when customer_config_query=None."""
        mock_os.path.join.return_value = MOCK_BKP_DESTINATION
        mock_run_remote_command.return_value = ("MOCK_BKP_DESTINATION", "")

        enm_config = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION)
        self.offsite_bkp_handler.customer_config_dict = {MOCK_CUSTOMER_NAME: enm_config}

        calls = [mock.call("Looking for available backups for customers: {}.".
                           format(self.offsite_bkp_handler.customer_config_dict.values()))]

        self.assertEqual(dict, type(self.offsite_bkp_handler.get_offsite_backup_dict()))

        self.offsite_bkp_handler.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'run_ssh_command')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_offsite_bkp_dict_stdout_return_value(self, mock_os, mock_run_remote_command):
        """Test the return value when customer_config_query is not None."""
        enm_config = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION)
        self.offsite_bkp_handler.customer_config_dict = {MOCK_CUSTOMER_NAME: enm_config}

        mock_os.path.join.return_value = MOCK_BKP_DESTINATION
        mock_run_remote_command.return_value = ("MOCK_BKP_DESTINATION", "")

        result = self.offsite_bkp_handler.get_offsite_backup_dict([enm_config])

        self.assertEqual(1, len(result[MOCK_CUSTOMER_NAME]))

    @mock.patch(MOCK_PACKAGE + 'run_ssh_command')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_offsite_bkp_dict_empty_stdout_return_value(self, mock_os, mock_run_remote_command):
        """Test the return value when stdout is empty."""
        enm_config = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION)
        self.offsite_bkp_handler.customer_config_dict = {MOCK_CUSTOMER_NAME: enm_config}

        mock_os.path.join.return_value = MOCK_BKP_DESTINATION
        mock_run_remote_command.return_value = ("", "")

        result = self.offsite_bkp_handler.get_offsite_backup_dict()

        self.assertEqual(0, len(result[MOCK_CUSTOMER_NAME]))

    @mock.patch(MOCK_PACKAGE + 'run_ssh_command')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_offsite_bkp_dict_returned_dictionary(self, mock_os, mock_run_remote_command):
        """Test the returned dictionary is as expected when customer_config_query is None."""
        enm_config_0 = EnmConfig("customer_0", MOCK_BKP_DESTINATION)
        enm_config_1 = EnmConfig("customer_1", MOCK_BKP_DESTINATION)

        self.offsite_bkp_handler.customer_config_dict = \
            {"customer_0": enm_config_0, "customer_1": enm_config_1}

        expected_dictionary = dict()
        expected_dictionary["customer_0"] = ["path0_1", "path0_2"]
        expected_dictionary["customer_1"] = ["path1_1", "path1_2"]

        mock_os.path.join.return_value = MOCK_BKP_DESTINATION
        mock_run_remote_command.return_value = (
            "path0_1\npath0_2\nEND-OF-COMMAND\npath1_1\npath1_2\nEND-OF-COMMAND\n", "")

        result = self.offsite_bkp_handler.get_offsite_backup_dict()

        self.assertEqual(len(expected_dictionary.keys()), len(result.keys()))
        self.assertEqual(expected_dictionary["customer_0"], result["customer_0"])
        self.assertEqual(expected_dictionary["customer_1"], result["customer_1"])


class OffsiteBkpHandlerDownloadProcessBkpTestCase(unittest.TestCase):
    """Class to test download_process_backup() method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()
        self.offsite_bkp_handler.download_process_backup = get_undecorated_class_method(
            self.offsite_bkp_handler.download_process_backup, self.offsite_bkp_handler)

    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_download')
    def test_download_process_backup_create_backup_destination_path_failure_exception(
            self, mock_check_local_disk_space_for_download, mock_os,
            mock_create_path):
        """Test to check the raise of exception if the backup folder can't be created."""
        mock_check_local_disk_space_for_download.return_value = True
        mock_os.path.join.return_value = MOCK_BKP_DOWNLOAD
        mock_create_path.return_value = False
        expected_error_msg = "Path informed cannot be created. (mock_download_bkp)"

        with self.assertRaises(DownloadBackupException) as cex:
            self.offsite_bkp_handler.download_process_backup(
                MOCK_CUSTOMER_NAME, MOCK_BKP_TAG, MOCK_BKP_PATH, MOCK_BKP_DESTINATION)

        self.assertEqual(expected_error_msg, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_download')
    def test_download_process_backup_check_onsite_disk_space_download_failure_exception(
            self, mock_check_local_disk_space_for_download):
        """Test to check the raise of exception if there is no enough space left on disk."""
        expected_error_msg = "Path doesn't have enough disk space for backup."

        mock_check_local_disk_space_for_download.side_effect = UtilsException(
            ExceptionCodes.NotEnoughFreeDiskSpace)

        with self.assertRaises(UtilsException) as raised:
            self.offsite_bkp_handler.download_process_backup(
                MOCK_CUSTOMER_NAME, MOCK_BKP_TAG, MOCK_BKP_PATH, MOCK_BKP_DESTINATION)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.check_volumes_for_download')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.check_offsite_backup_success_flag')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_download')
    def test_download_process_backup_empty_volume_list_failure_exception(
            self, mock_check_local_disk_space_for_download, mock_os,
            mock_create_path,
            mock_check_offsite_backup_success_flag, mock_check_volumes_for_download):
        """Assert if raises an exception when volume_name_list from pickle file is empty."""
        mock_check_local_disk_space_for_download.return_value = True
        mock_os.path.join.return_value = MOCK_BKP_DOWNLOAD
        mock_create_path.return_value = True
        mock_check_offsite_backup_success_flag.return_value = True
        mock_check_volumes_for_download.side_effect = DownloadBackupException(
            ExceptionCodes.NoVolumeListForBackup)
        expected_error_msg = "No volume list found for the backup."

        with self.assertRaises(DownloadBackupException) as cex:
            with mock.patch(MOCK_PACKAGE + 'mp.Pool'):
                self.offsite_bkp_handler.download_process_backup(MOCK_CUSTOMER_NAME,
                                                                 MOCK_BKP_TAG,
                                                                 MOCK_BKP_PATH,
                                                                 MOCK_BKP_DESTINATION)

        self.assertEqual(expected_error_msg, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.process_backup_metadata_files')
    @mock.patch(MOCK_PACKAGE + 'download_volume_from_offsite')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.check_volumes_for_download')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.check_offsite_backup_success_flag')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_download')
    def test_download_process_backup_volume_level_metadata_failure_exception(
            self, mock_check_local_disk_space_for_download, mock_os,
            mock_create_path,
            mock_check_offsite_backup_success_flag, mock_check_volumes_for_download,
            mock_download_volume_from_offsite, mock_process_backup_metadata_files):
        """Assert if raises an exception when cannot validate backup against its metadata."""
        mock_check_local_disk_space_for_download.return_value = True

        volume_list = ['volume1', 'volume2']

        mock_os.path.join.side_effect = [MOCK_BKP_DOWNLOAD, volume_list[0], volume_list[1]]

        mock_create_path.return_value = True
        mock_check_offsite_backup_success_flag.return_value = True

        mock_check_volumes_for_download.return_value = volume_list, volume_list

        calls = [mock.call("Downloading backup {} to '{}'.".format(MOCK_BKP_TAG,
                                                                   MOCK_BKP_DOWNLOAD)),
                 mock.call("Downloading list of volumes: {}.".format(volume_list)),
                 mock.call("Downloading volume '{}'.".format(volume_list[0])),
                 mock.call("Downloading volume '{}'.".format(volume_list[1]))]

        mock_download_volume_from_offsite.return_value = None

        mock_process_backup_metadata_files.side_effect = DownloadBackupException(
            ExceptionCodes.MissingBackupOKFlag)

        expected_error_msg = "Backup OK flag not found for the backup."

        with self.assertRaises(DownloadBackupException) as raised:
            with mock.patch(MOCK_PACKAGE + 'mp.Pool'):
                self.offsite_bkp_handler.download_process_backup(MOCK_CUSTOMER_NAME,
                                                                 MOCK_BKP_TAG,
                                                                 MOCK_BKP_PATH,
                                                                 MOCK_BKP_DESTINATION)

        self.offsite_bkp_handler.logger.info.assert_has_calls(calls)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.check_backup_download_errors')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.process_backup_metadata_files')
    @mock.patch(MOCK_PACKAGE + 'download_volume_from_offsite')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.check_volumes_for_download')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.check_offsite_backup_success_flag')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_download')
    def test_download_process_backup_volume_output_failure_exception(
            self, mock_check_local_disk_space_for_download, mock_os,
            mock_create_path,
            mock_check_offsite_backup_success_flag, mock_check_volumes_for_download,
            mock_download_volume_from_offsite, mock_process_backup_metadata_files,
            mock_check_backup_download_errors):
        """Assert if raises an exception when download process has errors."""
        mock_check_local_disk_space_for_download.return_value = True

        volume_list = ['volume1', 'volume2']

        mock_os.path.join.side_effect = [MOCK_BKP_DOWNLOAD, volume_list[0], volume_list[1]]

        mock_create_path.return_value = True
        mock_check_offsite_backup_success_flag.return_value = True
        mock_check_volumes_for_download.return_value = volume_list, volume_list

        calls = [mock.call("Downloading backup {} to '{}'.".format(MOCK_BKP_TAG,
                                                                   MOCK_BKP_DOWNLOAD)),
                 mock.call("Downloading list of volumes: {}.".format(volume_list)),
                 mock.call("Downloading volume '{}'.".format(volume_list[0])),
                 mock.call("Downloading volume '{}'.".format(volume_list[1]))]

        mock_download_volume_from_offsite.return_value = None

        mock_process_backup_metadata_files.return_value = True

        mock_check_backup_download_errors.side_effect = DownloadBackupException(
            ExceptionCodes.DownloadProcessFailed)

        expected_error_msg = "Failed to process downloaded backup."

        with self.assertRaises(DownloadBackupException) as cex:
            with mock.patch(MOCK_PACKAGE + 'mp.Pool'):
                self.offsite_bkp_handler.download_process_backup(MOCK_CUSTOMER_NAME,
                                                                 MOCK_BKP_TAG,
                                                                 MOCK_BKP_PATH,
                                                                 MOCK_BKP_DESTINATION)

        self.offsite_bkp_handler.logger.info.assert_has_calls(calls)

        self.assertEqual(expected_error_msg, cex.exception.message)


class OffsiteBkpHandlerCheckOffsiteBackupSuccessFlagTestCase(unittest.TestCase):
    """Class to test check_offsite_backup_success_flag() method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    def test_check_offsite_backup_success_flag_file_not_found_failure_exception(
            self, mock_check_remote_path_exists):
        """Assert if raises an exception when the backup success flag does not exist."""
        mock_check_remote_path_exists.return_value = False
        expected_error_msg = "Backup OK flag not found for the backup. (mock_bkp_path)"

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_bkp_handler.check_offsite_backup_success_flag(MOCK_BKP_PATH)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    def test_check_offsite_backup_success_flag_success_return(self, mock_check_remote_path_exists):
        """Test whether the backup success flag exist."""
        mock_check_remote_path_exists.return_value = True

        check_return = self.offsite_bkp_handler.check_offsite_backup_success_flag(MOCK_BKP_PATH)

        self.assertTrue(check_return)


class OffsiteBkpHandlerCheckVolumesForDownloadTestCase(unittest.TestCase):
    """Class to test check_volumes_for_download method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.retrieve_remote_pickle_file_content')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_volumes_for_download_empty_volume_list_failure_exception(
            self, mock_os, mock_retrieve_remote_pickle_file_content):
        """Assert if raises an exception when descriptor file content is an empty volumes' list."""
        mock_os.path.join.return_value = MOCK_VOLUME_LIST_DESCRIPTOR_FILE_PATH
        mock_retrieve_remote_pickle_file_content.return_value = []
        expected_error_msg = "No volume list found for the backup. " \
                             "(mock_volume_list_descriptor_file)"

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_bkp_handler.check_volumes_for_download(
                MOCK_REMOTE_DIR, MOCK_BKP_DOWNLOAD)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'check_is_processed_volume')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.retrieve_remote_pickle_file_content')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_volumes_for_download_all_volumes_processed(
            self, mock_os, mock_retrieve_remote_pickle_file_content,
            mock_check_is_processed_volume):
        """Test when all volumes were processed."""
        mock_os.path.join.return_value = MOCK_VOLUME_LIST_DESCRIPTOR_FILE_PATH

        mock_volume_list = ['volume1', 'volume2']

        mock_retrieve_remote_pickle_file_content.return_value = mock_volume_list
        mock_check_is_processed_volume.return_value = True

        volume_list, missing_volume_list = \
            self.offsite_bkp_handler.check_volumes_for_download(MOCK_REMOTE_DIR,
                                                                MOCK_BKP_DOWNLOAD)

        self.assertEqual(mock_volume_list, volume_list, "Returned volume list is invalid.")

        self.assertTrue(len(missing_volume_list) == 0, "No missing volume should be returned.")

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.on_volume_downloaded')
    @mock.patch(MOCK_PACKAGE + 'check_is_processed_volume')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.retrieve_remote_pickle_file_content')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_volumes_for_download_all_volumes_downloaded(
            self, mock_os, mock_retrieve_remote_pickle_file_content,
            mock_check_is_processed_volume, mock_on_volume_downloaded):
        """Test when all volumes were already downloaded but not processed."""
        mock_volume_list = ['volume0', 'volume1']

        mock_os.path.join.side_effect = [MOCK_VOLUME_LIST_DESCRIPTOR_FILE_PATH,
                                         MOCK_VOLUME, mock_volume_list[0], MOCK_VOLUME,
                                         mock_volume_list[1]]

        mock_retrieve_remote_pickle_file_content.return_value = mock_volume_list
        mock_check_is_processed_volume.return_value = False
        mock_os.path.exists.return_value = True
        mock_on_volume_downloaded.return_value = True
        calls = [mock.call("Volumes found on offsite : ['volume0', 'volume1']"),
                 mock.call("'volume0' already downloaded in the system. Starting to process it."),
                 mock.call("'volume1' already downloaded in the system. Starting to process it.")]

        volume_list, missing_volume_list = \
            self.offsite_bkp_handler.check_volumes_for_download(MOCK_REMOTE_DIR,
                                                                MOCK_BKP_DOWNLOAD)

        self.assertEqual(mock_volume_list, volume_list, "Returned volume list is invalid.")
        self.assertTrue(len(missing_volume_list) == 0, "No missing volume should be returned.")
        self.offsite_bkp_handler.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'check_is_processed_volume')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.retrieve_remote_pickle_file_content')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_volumes_for_download_all_volumes_missing(
            self, mock_os, mock_retrieve_remote_pickle_file_content,
            mock_check_is_processed_volume):
        """Test when all volumes are missing, that is, need to be downloaded from offsite."""
        mock_volume_list = ['volume0', 'volume1']
        mock_archived_volume_list = ['volume0.tar', 'volume1.tar']

        mock_os.path.join.side_effect = [MOCK_VOLUME_LIST_DESCRIPTOR_FILE_PATH,
                                         MOCK_VOLUME, mock_volume_list[0], MOCK_VOLUME,
                                         mock_volume_list[1]]

        mock_retrieve_remote_pickle_file_content.return_value = mock_volume_list
        mock_check_is_processed_volume.return_value = False

        mock_os.path.exists.return_value = False

        volume_list, missing_volume_list = \
            self.offsite_bkp_handler.check_volumes_for_download(MOCK_REMOTE_DIR,
                                                                MOCK_BKP_DOWNLOAD)

        self.assertEqual(mock_volume_list, volume_list, "Returned volume list is invalid.")

        self.assertEqual(mock_archived_volume_list, missing_volume_list, "Returned invalid "
                                                                         "missing volume list.")

    @mock.patch(MOCK_PACKAGE + 'check_is_processed_volume')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.retrieve_remote_pickle_file_content')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_volumes_for_download_some_processed_some_missing(
            self, mock_os, mock_retrieve_remote_pickle_file_content,
            mock_check_is_processed_volume):
        """Test when some volumes were already processed, but some are still missing."""
        mock_volume_list = ['volume0', 'volume1']
        mock_archived_volume_list = ['volume0.tar', 'volume1.tar']

        mock_os.path.join.side_effect = [MOCK_VOLUME_LIST_DESCRIPTOR_FILE_PATH,
                                         MOCK_VOLUME, MOCK_VOLUME, mock_volume_list[1]]

        mock_retrieve_remote_pickle_file_content.return_value = mock_volume_list
        mock_check_is_processed_volume.side_effect = [True, False]

        mock_os.path.exists.return_value = False

        volume_list, missing_volume_list = \
            self.offsite_bkp_handler.check_volumes_for_download(MOCK_REMOTE_DIR,
                                                                MOCK_BKP_DOWNLOAD)

        self.assertEqual(mock_volume_list, volume_list, "Returned volume list is invalid.")

        self.assertEqual([mock_archived_volume_list[1]], missing_volume_list, "Returned invalid "
                                                                              "missing volume "
                                                                              "list.")

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.on_volume_downloaded')
    @mock.patch(MOCK_PACKAGE + 'check_is_processed_volume')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.retrieve_remote_pickle_file_content')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_volumes_for_download_some_processed_some_downloaded(
            self, mock_os, mock_retrieve_remote_pickle_file_content,
            mock_check_is_processed_volume, mock_on_volume_downloaded):
        """Test when some volumes were already processed and the rest was already downloaded."""
        mock_volume_list = ['volume0', 'volume1']

        mock_os.path.join.side_effect = [MOCK_VOLUME_LIST_DESCRIPTOR_FILE_PATH,
                                         MOCK_VOLUME, MOCK_VOLUME, mock_volume_list[1]]

        mock_retrieve_remote_pickle_file_content.return_value = mock_volume_list
        mock_check_is_processed_volume.side_effect = [True, False]

        mock_os.path.exists.return_value = True

        mock_on_volume_downloaded.return_value = True

        volume_list, missing_volume_list = \
            self.offsite_bkp_handler.check_volumes_for_download(MOCK_REMOTE_DIR,
                                                                MOCK_BKP_DOWNLOAD)

        self.assertEqual(mock_volume_list, volume_list, "Returned volume list is invalid.")

        self.assertEqual([], missing_volume_list, "Returned invalid missing volume list.")

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.on_volume_downloaded')
    @mock.patch(MOCK_PACKAGE + 'check_is_processed_volume')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.retrieve_remote_pickle_file_content')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_volumes_for_download_some_processed_some_downloaded_some_missing(
            self, mock_os, mock_retrieve_remote_pickle_file_content,
            mock_check_is_processed_volume, mock_on_volume_downloaded):
        """Assert if the downloaded volumes are corrected identified and process the missing."""
        mock_volume_list = ['volume0', 'volume1', 'volume2']

        mock_os.path.join.side_effect = [MOCK_VOLUME_LIST_DESCRIPTOR_FILE_PATH,
                                         MOCK_VOLUME, MOCK_VOLUME, mock_volume_list[1],
                                         MOCK_VOLUME, mock_volume_list[2]]

        mock_retrieve_remote_pickle_file_content.return_value = mock_volume_list
        mock_check_is_processed_volume.side_effect = [True, False, False]

        mock_os.path.exists.side_effect = [True, False]

        mock_on_volume_downloaded.return_value = True

        calls = [mock.call("Volumes found on offsite : ['volume0', 'volume1', 'volume2']"),
                 mock.call("'volume1' already downloaded in the system. Starting to process it.")]

        volume_list, missing_volume_list = \
            self.offsite_bkp_handler.check_volumes_for_download(MOCK_REMOTE_DIR,
                                                                MOCK_BKP_DOWNLOAD)

        self.assertEqual(mock_volume_list, volume_list, "Returned volume list is invalid.")

        self.assertEqual(['volume2.tar'], missing_volume_list, "Returned invalid missing volume "
                                                               "list.")

        self.offsite_bkp_handler.logger.info.assert_has_calls(calls)


class OffsiteBkpHandlerOnVolumeDownloadedTestCase(unittest.TestCase):
    """Class to test on_volume_downloaded() method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    def test_on_volume_downloaded_failed_download(self):
        """Test to check when the callback when the download is failed."""
        mock_volume_output = {VOLUME_OUTPUT_KEYS.status.name: False,
                              VOLUME_OUTPUT_KEYS.rsync_output.name: None,
                              VOLUME_OUTPUT_KEYS.transfer_time.name: 0.0}

        mock_backup_output_dict = {'mock_volume': mock_volume_output}

        mock_download_volume_from_offsite_return = [MOCK_VOLUME, MOCK_VOLUME,
                                                    mock_volume_output,
                                                    MOCK_BKP_DESTINATION]

        calls = [mock.call("An error happened while downloading volume 'mock_volume'.")]

        result = self.offsite_bkp_handler.on_volume_downloaded(
            mock_download_volume_from_offsite_return)

        self.assertFalse(result, "Callback should have received an invalid volume.")

        self.assertEqual(mock_backup_output_dict, self.offsite_bkp_handler.backup_output_dict,
                         "Invalid output dict.")

        self.offsite_bkp_handler.logger.error.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'mp.Pool')
    def test_on_volume_downloaded_return_value(self, mock_mp_pool):
        """Test to check return value for successful scenario."""
        mock_mp_pool.return_value.apply_async = None
        self.offsite_bkp_handler.process_pool = mock_mp_pool

        mock_download_volume_from_offsite_return = [MOCK_VOLUME, MOCK_VOLUME,
                                                    {VOLUME_OUTPUT_KEYS.status.name: True},
                                                    MOCK_BKP_DESTINATION]

        result = self.offsite_bkp_handler.on_volume_downloaded(
            mock_download_volume_from_offsite_return)

        self.assertTrue(result, "Callback should have received a valid volume.")


class OffsiteBkpHandlerProcessBkpMetadataFilesTestCase(unittest.TestCase):
    """Class to test process_backup_metadata_files() method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + "OffsiteBackupHandler.check_onsite_backup_success_flag")
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    @mock.patch(MOCK_PACKAGE + 'is_tar_file')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.retrieve_remote_pickle_file_content')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_backup_metadata_files_bkp_ok_flag_error(
            self, mock_os, mock_retrieve_remote_pickle_file_content, mock_is_tar_file,
            mock_transfer_file, mock_check_backup_ok_flag):
        """Assert if raises an exception when cannot verify the backup ok flag for backup."""
        backup_ok_test_path = "NO_BACKUP_OK"
        mock_os.path.join.return_value = [MOCK_FILE_LIST_DESCRIPTOR_FILE_PATH, backup_ok_test_path]
        mock_retrieve_remote_pickle_file_content.return_value = [backup_ok_test_path]
        mock_is_tar_file.return_value = False
        mock_transfer_file.return_value = (11, 11, 1, 1, 12, 1)
        mock_check_backup_ok_flag.side_effect = DownloadBackupException(
            ExceptionCodes.MissingBackupOKFlag)
        expected_error_msg = "Backup OK flag not found for the backup."

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_bkp_handler.process_backup_metadata_files(MOCK_BKP_DOWNLOAD,
                                                                   MOCK_BKP_DESTINATION)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    @mock.patch(MOCK_PACKAGE + 'is_tar_file')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.retrieve_remote_pickle_file_content')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_backup_metadata_files_return_value(self,
                                                        mock_os,
                                                        mock_retrieve_remote_pickle_file_content,
                                                        mock_is_tar_file,
                                                        mock_transfer_file):
        """Test to check the return value and info log for successful scenario."""
        backup_ok_test_path = "BACKUP_OK"

        mock_os.path.join.return_value = [MOCK_FILE_LIST_DESCRIPTOR_FILE_PATH, backup_ok_test_path]
        mock_retrieve_remote_pickle_file_content.return_value = [backup_ok_test_path]
        mock_is_tar_file.return_value = False
        mock_os.path.basename.return_value = backup_ok_test_path
        mock_transfer_file.return_value = (11, 11, 1, 1, 12, 1)

        calls = [mock.call("Processing backup metadata files.")]

        self.assertTrue(self.offsite_bkp_handler.process_backup_metadata_files(
            MOCK_BKP_DOWNLOAD, MOCK_BKP_DESTINATION))

        self.offsite_bkp_handler.logger.info.assert_has_calls(calls)


class OffsiteBkpHandlerCheckBackupDownloadErrorsTestCase(unittest.TestCase):
    """Class to test check_backup_download_errors() method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_backup_download_errors_output_exception(self, mock_os):
        """Test to check the raise of exception and error log."""
        mock_dict = {MOCK_CUSTOMER_NAME: {'status': False, 'output': 'mock_output'}}
        calls = [mock.call('mock_output')]
        expected_error_msg = "Failed to process downloaded backup. (['mock_output'])"

        self.offsite_handler.backup_output_dict = mock_dict
        mock_os.path.join.return_value = ""
        mock_os.path.exists.return_value = True

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_handler.check_backup_download_errors(
                MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION, [MOCK_VOLUME])

        self.assertEqual(expected_error_msg, raised.exception.message)
        self.offsite_handler.logger.error.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_backup_download_errors_volume_not_found_exception(self, mock_os):
        """Assert if an exception is raised when one or more volumes is missing."""
        mock_os.path.exists.return_value = False
        mock_destination_path = "{}/{}".format(MOCK_BKP_DOWNLOAD, MOCK_VOLUME)
        mock_os.path.join.return_value = mock_destination_path
        expected_error_msg = "Volume not found in path. " \
                             "(['mock_volume', 'mock_download_bkp/mock_volume'])"

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_handler.check_backup_download_errors(
                MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION, [MOCK_VOLUME])

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'validate_backup_per_volume')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_backup_download_errors_volume_metadata_exception(
            self, mock_os, mock_validate_backup_per_volume):
        """Assert if raises an exception when cannot validate backup against its metadata."""
        mock_os.path.join.return_value = ""
        mock_os.path.exists.return_value = True
        mock_validate_backup_per_volume.return_value = False
        expected_error_msg = "Downloaded backup could not be validated against metadata. " \
                             "(mock_bkp_dest)"

        self.offsite_handler.backup_output_dict = \
            {MOCK_CUSTOMER_NAME: {'status': True, 'output': 'mock_output'}}

        with self.assertRaises(DownloadBackupException) as cex:
            self.offsite_handler.check_backup_download_errors(
                MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION, [MOCK_VOLUME])

        self.assertEqual(expected_error_msg, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'validate_backup_per_volume')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_check_backup_download_errors_return_value(
            self, mock_os, mock_validate_backup_per_volume):
        """Test to check the return value for successful scenario."""
        mock_os.path.join.return_value = ""
        mock_os.path.exists.return_value = True
        mock_validate_backup_per_volume.return_value = True

        self.offsite_handler.backup_output_dict = \
            {MOCK_CUSTOMER_NAME: {'status': True, 'output': 'mock_output'}}

        result = self.offsite_handler.check_backup_download_errors(
            MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION, [MOCK_VOLUME])

        self.assertTrue(result)


class OffsiteBkpHandlerProcessVolumeTestCase(unittest.TestCase):
    """Class to test execute_download_backup_from_offsite method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'is_valid_path')
    @mock.patch(MOCK_PACKAGE + 'decompress_file')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_volume_path_not_exist_success(self, mock_os, mock_decompress_file,
                                                   mock_is_valid_path):
        """Test to check the return value and info log for the successful scenario."""
        mock_os.path.join.return_value = MOCK_BKP_PATH
        mock_is_valid_path.return_value = True
        mock_decompress_file.return_value = MOCK_BKP_DESTINATION

        calls = [mock.call("Extracting volume mock_bkp_path."),
                 mock.call("Decrypting and decompressing files from volume 'mock_bkp_path'.")]

        self.assertTrue(self.offsite_bkp_handler.process_volume(MOCK_VOLUME, MOCK_BKP_PATH, {}))

        self.offsite_bkp_handler.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'is_valid_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_volume_path_not_exist_process_exception(self, mock_os, mock_is_valid_path):
        """Test to check the return value and raise of exception if volume path does not exist."""
        mock_os.path.join.return_value = MOCK_BKP_PATH
        mock_is_valid_path.side_effect = UtilsException(ExceptionCodes.InvalidPath, MOCK_VOLUME)

        error_msg = "Error Code 32. " \
                    "Path informed is not a valid formatted folder or file. (mock_volume)."
        output = "Error while processing volume. {}".format(error_msg)

        result = self.offsite_bkp_handler.process_volume(MOCK_VOLUME, MOCK_BKP_PATH, {})

        self.assertIsNotNone(result, "Should have returned a tuple.")
        self.assertEqual(MOCK_VOLUME, result[0])
        self.assertEqual(output, result[1]['output'])


class OffsiteBkpHandlerGetBkpDirListToCleanupTestCase(unittest.TestCase):
    """Class to test get_backup_dir_list_to_cleanup() method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'sort_remote_folders_by_content')
    @mock.patch(MOCK_PACKAGE + 'is_remote_folder_empty')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_offsite_backup_dict')
    @mock.patch(MOCK_PACKAGE + 'get_values_from_dict')
    def test_get_backup_dir_list_to_cleanup_one_customer_zero_backup_to_remove(
            self, mock_get_values_from_dict, mock_get_offsite_bkp_dict,
            mock_is_remote_folder_empty, mock_sort_remote_folders_by_content):
        """
        Test to check when no backup should be deleted according to the retention policy.

        In this scenario there is just one customer no backup to be removed.
        """
        enm_config = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION)
        mock_get_values_from_dict.return_value = [enm_config]

        mock_bkp_list_offsite = ['/path/bkp1', '/path/bkp2', '/path/bkp3', '/path/bkp4']
        mock_get_offsite_bkp_dict.return_value = {MOCK_CUSTOMER_NAME: mock_bkp_list_offsite}

        mock_is_remote_folder_empty.return_value = False
        mock_sort_remote_folders_by_content.return_value = mock_bkp_list_offsite

        expected_backup_to_be_deleted = []
        self.assertEqual(expected_backup_to_be_deleted,
                         self.offsite_bkp_handler.get_backup_dir_list_to_cleanup(MOCK_RETENTION))

    @mock.patch(MOCK_PACKAGE + 'sort_remote_folders_by_content')
    @mock.patch(MOCK_PACKAGE + 'is_remote_folder_empty')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_offsite_backup_dict')
    @mock.patch(MOCK_PACKAGE + 'get_values_from_dict')
    def test_get_backup_dir_list_to_cleanup_one_customer_empty_backups(
            self, mock_get_values_from_dict, mock_get_offsite_bkp_dict,
            mock_is_remote_folder_empty, mock_sort_remote_folders_by_content):
        """
        Test to check when no backup should be deleted according to the retention policy.

        In this scenario all backups are empty on offsite.
        """
        enm_config = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION)
        mock_get_values_from_dict.return_value = [enm_config]

        mock_bkp_list_offsite = ['/path/bkp1', '/path/bkp2', '/path/bkp3', '/path/bkp4']
        mock_get_offsite_bkp_dict.return_value = {MOCK_CUSTOMER_NAME: mock_bkp_list_offsite}

        mock_is_remote_folder_empty.return_value = True
        mock_sort_remote_folders_by_content.return_value = mock_bkp_list_offsite

        expected_backup_to_be_deleted = []
        self.assertEqual(expected_backup_to_be_deleted,
                         self.offsite_bkp_handler.get_backup_dir_list_to_cleanup(MOCK_RETENTION))

    @mock.patch(MOCK_PACKAGE + 'sort_remote_folders_by_content')
    @mock.patch(MOCK_PACKAGE + 'is_remote_folder_empty')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_offsite_backup_dict')
    @mock.patch(MOCK_PACKAGE + 'get_values_from_dict')
    def test_get_backup_dir_list_to_cleanup_one_customer_remove_backup(
            self, mock_get_values_from_dict, mock_get_offsite_bkp_dict,
            mock_is_remote_folder_empty, mock_sort_remote_folders_by_content):
        """
        Test to check when there are backups to be deleted according to the retention policy.

        In this scenario there is just one customer and two backups to be removed.
        """
        enm_config = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_BKP_DESTINATION)
        mock_get_values_from_dict.return_value = [enm_config]

        mock_bkp_list_offsite = ['/path/bkp1', '/path/bkp2', '/path/bkp3', '/path/bkp4',
                                 '/path/bkp5', '/path/bkp6']
        mock_get_offsite_bkp_dict.return_value = {MOCK_CUSTOMER_NAME: mock_bkp_list_offsite}

        mock_is_remote_folder_empty.return_value = False
        mock_sort_remote_folders_by_content.return_value = mock_bkp_list_offsite

        expected_backup_to_be_deleted = ['/path/bkp5', '/path/bkp6']
        self.assertEqual(expected_backup_to_be_deleted,
                         self.offsite_bkp_handler.get_backup_dir_list_to_cleanup(MOCK_RETENTION))

    @mock.patch(MOCK_PACKAGE + 'sort_remote_folders_by_content')
    @mock.patch(MOCK_PACKAGE + 'is_remote_folder_empty')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_offsite_backup_dict')
    @mock.patch(MOCK_PACKAGE + 'get_values_from_dict')
    def test_get_backup_dir_list_to_cleanup_multiple_customers_remove_backup(
            self, mock_get_values_from_dict, mock_get_offsite_bkp_dict,
            mock_is_remote_folder_empty, mock_sort_remote_folders_by_content):
        """
        Test to check when there are backups to be deleted according to the retention policy.

        In this scenario there are two customers with one backup to be removed for each.
        """
        mock_customer_name_1 = MOCK_CUSTOMER_NAME + '1'
        mock_customer_name_2 = MOCK_CUSTOMER_NAME + '2'
        enm_config_customer_1 = EnmConfig(mock_customer_name_1, MOCK_BKP_DESTINATION)
        enm_config_customer_2 = EnmConfig(mock_customer_name_2, MOCK_BKP_DESTINATION)

        mock_get_values_from_dict.return_value = [enm_config_customer_1, enm_config_customer_2]

        mock_bkp_list_offsite = ['/path/bkp1', '/path/bkp2', '/path/bkp3', '/path/bkp4',
                                 '/path/bkp5']

        mock_get_offsite_bkp_dict.return_value = {mock_customer_name_1: mock_bkp_list_offsite,
                                                  mock_customer_name_2: mock_bkp_list_offsite}

        mock_is_remote_folder_empty.return_value = False
        mock_sort_remote_folders_by_content.return_value = mock_bkp_list_offsite

        expected_backup_to_be_deleted = ['/path/bkp5', '/path/bkp5']
        self.assertEqual(expected_backup_to_be_deleted,
                         self.offsite_bkp_handler.get_backup_dir_list_to_cleanup(MOCK_RETENTION))


class OffsiteBkpHandlerCleanOffsiteBkpTestCase(unittest.TestCase):
    """Class to test clean_offsite_backup() method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_backup_dir_list_to_cleanup')
    def test_clean_offsite_backup_check_return_value_no_removal(self, mock_get_bkp_dir_list):
        """Test to check the return value if no backup was removed."""
        mock_get_bkp_dir_list.return_value = []

        result = self.offsite_bkp_handler.clean_offsite_backup(4)

        self.assertTrue(result[0])
        self.assertEqual("Off-site clean up finished successfully with no backup removed.",
                         result[1])
        self.assertEqual([], result[2])

    @mock.patch('backup.utils.remote.validate_removed_dir_list')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_backup_dir_list_to_cleanup')
    def test_clean_offsite_backup_check_return_value_not_removed(self,
                                                                 mock_get_bkp_dir_list,
                                                                 mock_validate_removed_dir_list):
        """Test to check the return value if no backup was removed."""
        mock_get_bkp_dir_list.return_value = [MOCK_BKP_PATH]
        mock_validate_removed_dir_list.return_value = (MOCK_BKP_DESTINATION, MOCK_BKP_PATH)

        self.offsite_bkp_handler.offsite_config.host = '127.0.0.1'

        result = self.offsite_bkp_handler.clean_offsite_backup(4)

        self.assertFalse(result[0])
        self.assertEqual("Following backups were not removed: mock_bkp_dest", result[1])
        self.assertEqual(MOCK_BKP_PATH, result[2])

    @mock.patch('backup.utils.remote.validate_removed_dir_list')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_backup_dir_list_to_cleanup')
    def test_clean_offsite_backup_check_return_value_cleanup_error(self,
                                                                   mock_get_bkp_dir_list,
                                                                   mock_validate_removed_dir_list):
        """Test to check the return value if there occurred cleanup error."""
        mock_get_bkp_dir_list.return_value = [MOCK_BKP_PATH]
        mock_validate_removed_dir_list.return_value = (MOCK_BKP_PATH, "")

        self.offsite_bkp_handler.offsite_config.host = '127.0.0.1'

        result = self.offsite_bkp_handler.clean_offsite_backup(4)

        self.assertFalse(result[0])
        self.assertEqual("Following backups were not removed: mock_bkp_path", result[1])
        self.assertEqual('', result[2])

    @mock.patch('backup.utils.remote.validate_removed_dir_list')
    @mock.patch(MOCK_PACKAGE + 'OffsiteBackupHandler.get_backup_dir_list_to_cleanup')
    def test_clean_offsite_backup_check_return_value_success(self,
                                                             mock_get_bkp_dir_list,
                                                             mock_validate_removed_dir_list):
        """Test to check the return value if removal was successful."""
        mock_get_bkp_dir_list.return_value = [MOCK_BKP_PATH]
        mock_validate_removed_dir_list.return_value = ("", "")

        self.offsite_bkp_handler.offsite_config.host = '127.0.0.1'

        result = self.offsite_bkp_handler.clean_offsite_backup(4)

        self.assertTrue(result[0])
        self.assertEqual("Off-site clean up finished successfully.", result[1])
        self.assertEqual('', result[2])


class OffsiteBkpHandlerRetrieveRemotePickleFileContentTestCase(unittest.TestCase):
    """Class to test retrieve_remote_pickle_file_content method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    def test_retrieve_remote_pickle_file_content_file_transferring_failure_exception(
            self, mock_transfer_file):
        """Test when an error happened during file download."""
        mock_transfer_file.side_effect = RsyncException
        expected_error_msg = "Something went wrong."

        with self.assertRaises(RsyncException) as raised:
            self.offsite_bkp_handler.retrieve_remote_pickle_file_content(MOCK_FILE,
                                                                         MOCK_BKP_DESTINATION)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'load_pickle_file')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    def test_retrieve_remote_pickle_file_content_file_loading_failure_exception(
            self, mock_transfer_file, mock_os, mock_load_pickle_file):
        """Test when an error happened during file download."""
        mock_transfer_file.return_value = None
        mock_os.path.join.return_value = 'mock_pickle_file'
        mock_load_pickle_file.return_value = None
        expected_error_msg = "Expected input has a wrong type. " \
                             "(['Pickle file content was supposed to be a list.', None])"

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_bkp_handler.retrieve_remote_pickle_file_content(MOCK_FILE,
                                                                         MOCK_BKP_DESTINATION)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'load_pickle_file')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    def test_retrieve_remote_pickle_file_content_file_removal_failure_exception(
            self, mock_transfer_file, mock_os, mock_load_pickle_file, mock_remove_path):
        """Test when an error happened while removing the pickle file."""
        mock_transfer_file.return_value = None
        mock_os.path.join.return_value = 'mock_pickle_file'
        mock_load_pickle_file.return_value = []
        mock_remove_path.return_value = False
        expected_error_msg = "File cannot be removed. (mock_pickle_file)"

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_bkp_handler.retrieve_remote_pickle_file_content(MOCK_FILE,
                                                                         MOCK_BKP_DESTINATION)

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'load_pickle_file')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    def test_retrieve_remote_pickle_file_content_success_return(
            self, mock_transfer_file, mock_os, mock_load_pickle_file, mock_remove_path):
        """Test when the pickle file was successfully loaded and removed."""
        mock_transfer_file.return_value = None
        mock_os.path.join.return_value = 'mock_pickle_file'
        mock_load_pickle_file.return_value = []
        mock_remove_path.return_value = True

        return_value = self.offsite_bkp_handler.retrieve_remote_pickle_file_content(
            MOCK_FILE, MOCK_BKP_DESTINATION)

        self.assertEqual([], return_value, "Invalid return value.")


class OffsiteBackupHandlerCheckOnsiteBackupSuccessFlag(unittest.TestCase):
    """Class to test check_onsite_backup_success_flag method from OffsiteBackupHandler class."""

    def setUp(self):
        """Set up the test constants."""
        self.offsite_bkp_handler = create_offsite_bkp_object()

    @mock.patch(MOCK_PACKAGE + 'os.path.exists')
    def test_check_onsite_backup_success_flag(self, mock_os_exists):
        """Assert if returns True when BACKUP_OK flag was successfully downloaded."""
        mock_backup_destination_path = "fake/path/to/backup"
        mock_os_exists.return_value = True
        mock_call = "Backup OK file recognized: 'fake/path/to/backup/BACKUP_OK'."

        result = self.offsite_bkp_handler.check_onsite_backup_success_flag(
            mock_backup_destination_path)

        self.assertTrue(result, "Should have returned True.")
        self.offsite_bkp_handler.logger.info.assert_called_with(mock_call)

    @mock.patch(MOCK_PACKAGE + 'os.path.exists')
    def test_check_onsite_backup_success_flag_raise_exception(self, mock_os_exists):
        """Assert if raises the correct exception when BACKUP_OK flag is missing from download."""
        mock_backup_destination_path = "fake/path/to/backup"
        mock_os_exists.return_value = False
        expected_error_msg = "Backup OK flag not found for the backup."

        with self.assertRaises(DownloadBackupException) as raised:
            self.offsite_bkp_handler.check_onsite_backup_success_flag(
                mock_backup_destination_path)

        self.assertEqual(expected_error_msg, raised.exception.message)
