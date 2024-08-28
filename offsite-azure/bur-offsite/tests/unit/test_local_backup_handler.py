##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=too-many-arguments,too-many-locals,too-many-lines

"""This module is for unit tests from the local_backup_handler.py script."""

import logging
import unittest

import mock

from backup.backup_settings import EnmConfig
from backup.constants import BACKUP_META_FILE, BUR_FILE_LIST_DESCRIPTOR_FILE_NAME,\
    BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME, PROCESSED_VOLUME_ENDS_WITH, SUCCESS_FLAG_FILE,\
    VOLUME_OUTPUT_KEYS
from backup.exceptions import ExceptionCodes, GnupgException, RsyncException, \
    UploadBackupException, UtilsException
from backup.local_backup_handler import LocalBackupHandler, \
    unwrapper_local_backup_handler_function, VOLUME_CALLBACK_OUTPUT_INDEX
from backup.utils.decorator import get_undecorated_class_method

logging.disable(logging.CRITICAL)

MOCK_VOLUME_NAME = 'mock_volume'
MOCK_CUSTOMER_NAME = 'mock_customer'
MOCK_BACKUP_NAME = 'mock_backup_name'
MOCK_TMP_BKP_PATH = 'mock_tmp_bkp_path'
MOCK_SUCCESS_FLAG_NAME = 'mock_success_flag'
MOCK_REMOTE_BKP_PATH = 'mock_remote_bkp_path'
MOCK_LOCAL_BACKUP_PATH = 'mock_local_backup_path'

MOCK_PACKAGE = 'backup.local_backup_handler.'
MOCK_GNUPG_MANAGER_PACKAGE = 'backup.gnupg_manager.'
MOCK_ENCRYPT = "backup.gnupg_manager.GnupgManager.compress_encrypt_file_list"
MOCK_PARALLELISM_CONSTANT = 1


def get_local_backup_handler():
    """
    Get an instance of local backup handler for mock_customer.

    :return: LocalBackupHandler object
    """
    with mock.patch(MOCK_GNUPG_MANAGER_PACKAGE + 'GnupgManager') as mock_gnupg_manager:
        with mock.patch(MOCK_GNUPG_MANAGER_PACKAGE + 'GPG') as mock_gpg:
            mock_gnupg_manager.gpg_handler.side_effect = mock_gpg

    customer_enmaas_cfg = EnmConfig(MOCK_CUSTOMER_NAME, MOCK_LOCAL_BACKUP_PATH)

    with mock.patch('backup.backup_settings.OffsiteConfig') as mock_offsite_config:
        with mock.patch(MOCK_PACKAGE + 'CustomLogger') as mock_logger:
            with mock.patch(MOCK_PACKAGE + 'dill.dumps'):
                with mock.patch('backup.backup_settings.OnsiteConfig') as mock_onsite_cfg:
                    local_bkp_handler = LocalBackupHandler(mock_offsite_config, mock_onsite_cfg,
                                                           customer_enmaas_cfg, mock_gnupg_manager,
                                                           MOCK_PARALLELISM_CONSTANT,
                                                           MOCK_PARALLELISM_CONSTANT,
                                                           MOCK_PARALLELISM_CONSTANT, mock_logger)
    local_bkp_handler.backup_output_dict = {}

    return local_bkp_handler


class LocalBackupHandlerUnwrapperProcessBackupVolumeTestCase(unittest.TestCase):
    """Test cases for unwrapper_local_backup_handler_function function."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'dill.loads')
    def test_unwrapper_local_backup_handler_function_invalid_local_bkp_handler_instance_exception(
            self, mock_dill_loads):
        """Test when an invalid instance of local backup handler is loaded by dill."""
        mock_dill_loads.return_value = None

        with self.assertRaises(Exception) as raised:
            unwrapper_local_backup_handler_function(None, '')

        self.assertEqual("Could not unwrap backup handler object.", raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_volume')
    @mock.patch(MOCK_PACKAGE + 'dill.loads')
    def test_unwrapper_local_backup_handler_function_valid_instance_process_volume(
            self, mock_dill_loads, mock_process_volume):
        """Test when a valid local backup handler is loaded and the function is process_volume."""
        mock_process_volume.return_value = {}
        mock_process_volume.__name__ = "process_volume"

        self.local_bkp_handler.process_volume = mock_process_volume

        mock_dill_loads.return_value = self.local_bkp_handler

        unwrapper_result = unwrapper_local_backup_handler_function(self.local_bkp_handler,
                                                                   'process_volume', '',
                                                                   MOCK_VOLUME_NAME, '',
                                                                   MOCK_REMOTE_BKP_PATH)

        self.assertIsNotNone(unwrapper_result, "Should not have returned None.")
        self.assertEqual(
            MOCK_VOLUME_NAME, unwrapper_result[VOLUME_CALLBACK_OUTPUT_INDEX.VOLUME_NAME.value - 1])
        self.assertEqual({}, unwrapper_result[VOLUME_CALLBACK_OUTPUT_INDEX.VOLUME_OUTPUT.value - 1])
        self.assertEqual(MOCK_REMOTE_BKP_PATH, unwrapper_result[
            VOLUME_CALLBACK_OUTPUT_INDEX.REMOTE_BACKUP_PATH.value - 1])

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.transfer_backup_volume_to_offsite')
    @mock.patch(MOCK_PACKAGE + 'dill.loads')
    def test_unwrapper_local_backup_handler_function_valid_instance_transfer_backup(
            self, mock_dill_loads, mock_transfer_backup_volume_to_offsite):
        """
        Test loading local backup handler for the transfer_backup_volume_to_offsite function.

        Test when a valid local backup handler is loaded and the function is
        transfer_backup_volume_to_offsite.
        """
        mock_transfer_backup_volume_to_offsite.return_value = (MOCK_VOLUME_NAME, {})
        mock_transfer_backup_volume_to_offsite.__name__ = "transfer_backup_volume_to_offsite"

        self.local_bkp_handler.transfer_backup_volume_to_offsite = \
            mock_transfer_backup_volume_to_offsite

        mock_dill_loads.return_value = self.local_bkp_handler

        unwrapper_result = unwrapper_local_backup_handler_function(
            self.local_bkp_handler, 'transfer_backup_volume_to_offsite', '', MOCK_VOLUME_NAME,
            '', MOCK_REMOTE_BKP_PATH)

        self.assertIsNotNone(unwrapper_result, "Should not have returned None.")
        self.assertEqual(
            MOCK_VOLUME_NAME, unwrapper_result[VOLUME_CALLBACK_OUTPUT_INDEX.VOLUME_NAME.value - 1])
        self.assertEqual({}, unwrapper_result[VOLUME_CALLBACK_OUTPUT_INDEX.VOLUME_OUTPUT.value - 1])


class LocalBackupHandlerProcessBackupListTestCase(unittest.TestCase):
    """Test cases for process_backup_list method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_local_backup_list')
    def test_process_backup_list_with_invalid_backup_tag(self, mock_get_local_backup_list):
        """Test when the passed backup tag to upload doesn't match any of the backups onsite."""
        mock_bkp_list = ['backup0', 'backup1', 'backup2']
        mock_get_local_backup_list.return_value = mock_bkp_list

        expected_exception_code = ExceptionCodes.NoSuchBackupTag.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.process_backup_list('backup3')

        self.assertEqual(expected_exception_code, raised.exception.code.value)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_create_offsite_onsite_base_paths')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_and_validate_onsite_backups_list')
    def test_process_backup_list_validate_create_offsite_onsite_base_paths_fails(
            self, mock_get_and_validate_onsite_backups_list,
            mock_validate_create_offsite_onsite_base_paths):
        """Test when there is a problem with the onsite offsite base paths validations."""
        mock_get_and_validate_onsite_backups_list.return_value = ['']

        mock_expected_error_msg = "Mock validation exception."
        mock_validate_create_offsite_onsite_base_paths.side_effect = \
            UploadBackupException(ExceptionCodes.CannotCreatePath,
                                  mock_expected_error_msg)

        expected_exception_code = ExceptionCodes.CannotCreatePath.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.process_backup_list()

        self.assertEqual(expected_exception_code, raised.exception.code.value)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_and_validate_onsite_backups_list')
    def test_process_backup_list_no_backups_to_process(self, get_and_validate_onsite_backups_list):
        """Test when there aren't onsite backups for the customer to process."""
        mock_expected_error_msg = "No backup to be processed for the customer mock_customer."
        get_and_validate_onsite_backups_list.side_effect = \
            UploadBackupException(ExceptionCodes.NoBackupsToProcess, mock_expected_error_msg)

        expected_exception_code = ExceptionCodes.NoBackupsToProcess.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.process_backup_list()

        self.assertEqual(expected_exception_code, raised.exception.code.value)

    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_create_offsite_onsite_base_paths')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_and_validate_onsite_backups_list')
    def test_process_backup_list_create_onsite_backup_temporary_folder_fails(
            self, mock_get_and_validate_onsite_backups_list,
            mock_validate_offsite_onsite_customer_paths, mock_os, mock_create_path):
        """Test when there is a problem to create the onsite backup temporary folder."""
        mock_bkp_list = ['backup0']
        mock_get_and_validate_onsite_backups_list.return_value = mock_bkp_list
        mock_validate_offsite_onsite_customer_paths.return_value = True

        calls = [mock.call("Doing backup of: mock_customer, directories: {}".format(mock_bkp_list))]

        mock_os.path.join.side_effect = ['remote_path', 'temp_path']
        mock_create_path.return_value = False

        expected_exception_code = ExceptionCodes.ProcessBackupListErrors.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.process_backup_list()

        self.assertEqual(expected_exception_code, raised.exception.code.value)
        self.local_bkp_handler.logger.log_info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_backup')
    @mock.patch(MOCK_PACKAGE + 'create_remote_dir')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_create_offsite_onsite_base_paths')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_and_validate_onsite_backups_list')
    def test_process_backup_list_backup_process_bkp_exception(
            self, mock_get_and_validate_onsite_backups_list,
            mock_validate_offsite_onsite_customer_paths, mock_os, mock_create_path,
            mock_create_remote_dir, mock_process_backup):
        """Test when one of the backups fails while executing process_backup method."""
        mock_bkp_list = ['backup0']
        mock_get_and_validate_onsite_backups_list.return_value = mock_bkp_list
        mock_validate_offsite_onsite_customer_paths.return_value = True
        mock_os.path.join.return_value = ''
        mock_create_path.return_value = True
        mock_create_remote_dir.return_value = True

        mock_expected_error_msg = "Mock process backup exception."
        mock_process_backup.side_effect = UploadBackupException(
            ExceptionCodes.ProcessBackupListErrors, mock_expected_error_msg)

        expected_exception_code = ExceptionCodes.ProcessBackupListErrors.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.process_backup_list()

        self.assertEqual(expected_exception_code, raised.exception.code.value)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_backup')
    @mock.patch(MOCK_PACKAGE + 'create_remote_dir')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_create_offsite_onsite_base_paths')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_and_validate_onsite_backups_list')
    def test_process_backup_list_process_backup_called_for_all(
            self, mock_get_and_validate_onsite_backups_list,
            mock_validate_offsite_onsite_customer_paths, mock_os, mock_create_path,
            mock_create_remote_dir, mock_process_backup):
        """process_backup should be called for all valid backups to be processed from scratch."""
        mock_bkp_list = ['backup0', 'backup1', 'backup2']
        mock_get_and_validate_onsite_backups_list.return_value = mock_bkp_list
        mock_validate_offsite_onsite_customer_paths.return_value = True
        mock_os.path.join.return_value = ''
        mock_create_path.return_value = True
        mock_create_remote_dir.return_value = True

        process_backup_calls = [mock.call('backup0', '', ''),
                                mock.call('backup1', '', ''),
                                mock.call('backup2', '', '')]

        process_bkp_list_return = self.local_bkp_handler.process_backup_list()

        self.assertTrue(process_bkp_list_return, "Should have returned true.")
        mock_process_backup.assert_has_calls(process_backup_calls)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_backup')
    @mock.patch(MOCK_PACKAGE + 'create_remote_dir')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_create_offsite_onsite_base_paths')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_and_validate_onsite_backups_list')
    def test_process_backup_list_with_valid_backup_tag(
            self, mock_get_and_validate_onsite_backups_list,
            mock_validate_offsite_onsite_customer_paths, mock_os, mock_create_path,
            mock_create_remote_dir, mock_process_backup, mock_remove_path):
        """Test when the backup identified by the backup tag is successfully processed."""
        mock_backup_tag = ['backup1']
        mock_get_and_validate_onsite_backups_list.return_value = mock_backup_tag
        mock_validate_offsite_onsite_customer_paths.return_value = True
        mock_os.path.join.return_value = ''
        mock_create_path.return_value = True
        mock_create_remote_dir.return_value = True
        mock_remove_path.return_value = True

        process_bkp_list_return = self.local_bkp_handler.process_backup_list('backup1')

        self.assertTrue(process_bkp_list_return, "Should have returned true.")
        mock_process_backup.assert_any_call('backup1', '', '')

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_backup')
    @mock.patch(MOCK_PACKAGE + 'create_remote_dir')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_create_offsite_onsite_base_paths')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_and_validate_onsite_backups_list')
    def test_process_backup_list_with_valid_backup_tag_remove_tmp_fails(
            self, mock_get_and_validate_onsite_backups_list,
            mock_validate_offsite_onsite_customer_paths, mock_os, mock_create_path,
            mock_create_remote_dir, mock_process_backup, mock_remove_path):
        """
        Test when removing the onsite temporary folder fails.

        Test when the backup identified by the backup tag is successfully processed,
        but removing the onsite temporary folder fails.
        """
        mock_backup_tag = ['backup1']
        mock_get_and_validate_onsite_backups_list.return_value = mock_backup_tag
        mock_validate_offsite_onsite_customer_paths.return_value = True
        mock_os.path.join.return_value = ''
        mock_create_path.return_value = True
        mock_create_remote_dir.return_value = True
        mock_remove_path.return_value = False
        calls = [mock.call("Error while removing temporary backup folder ''.")]

        process_bkp_list_return = self.local_bkp_handler.process_backup_list('backup1')

        self.assertTrue(process_bkp_list_return, "Should have returned true.")
        mock_process_backup.assert_any_call('backup1', '', '')
        self.local_bkp_handler.logger.error.assert_has_calls(calls)


class LocalBackupHandlerGetAndValidateOnsiteBackupsListTestCase(unittest.TestCase):
    """TCs for get_and_validate_onsite_backups_list method under local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_local_backup_list')
    def test_get_and_validate_onsite_backups_list_no_backup_tag_passed(self,
                                                                       mock_get_local_backup_list):
        """
        Test get all valid onsite backup tags list.

        Test if get_and_validate_onsite_backups_list will return all the valid onsite backup
        tags in a list.
        """
        mock_valid_onsite_backups = ["backup0", "backup1"]
        mock_get_local_backup_list.return_value = mock_valid_onsite_backups

        expected = ["backup0", "backup1"]
        result = self.local_bkp_handler.get_and_validate_onsite_backups_list()

        self.assertEqual(expected, result)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_local_backup_list')
    def test_get_and_validate_onsite_backups_list_return_tag_as_list(self,
                                                                     mock_get_local_backup_list):
        """
        Test if the passed backup tag was found in the list of valid onsite backups tags.

        Test if get_and_validate_onsite_backups_list will return the backup tag as a list,
        if the passed backup tag was found in the list of valid onsite backups tags.
        """
        mock_get_local_backup_list.return_value = ["backup0", "backup1"]
        backup_tag_to_upload = "backup1"

        expected = [backup_tag_to_upload]
        result = self.local_bkp_handler.get_and_validate_onsite_backups_list(backup_tag_to_upload)

        self.assertEqual(expected, result)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_local_backup_list')
    def test_get_and_validate_onsite_backups_list_return_type(self, mock_get_local_backup_list):
        """
        Test if the returned object type is list.

        Test if get_and_validate_onsite_backups_list will return an object of list type,
        if the passed backup tag was found in the list of valid onsite backups tags.
        """
        mock_get_local_backup_list.return_value = ["backup0", "backup1"]
        backup_tag_to_upload = "backup1"

        expected = []
        result = self.local_bkp_handler.get_and_validate_onsite_backups_list(backup_tag_to_upload)

        self.assertEqual(type(expected), type(result))

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_local_backup_list')
    def test_get_and_validate_onsite_backups_list_backup_tag_not_found(self,
                                                                       mock_get_local_backup_list):
        """
        Test when the passed backup_tag not found in the list of valid onsite backup tags.

        Test if get_and_validate_onsite_backups_list will return False if the backup_tag not
        found in the list of valid onsite backup tags.
        """
        mock_get_local_backup_list.return_value = ["backup0", "backup1"]
        backup_tag_to_upload = "backup3"

        expected_exception_code = ExceptionCodes.NoSuchBackupTag.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.get_and_validate_onsite_backups_list(
                backup_tag_to_upload)

        self.assertEqual(expected_exception_code, raised.exception.code.value)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_local_backup_list')
    def test_get_and_validate_onsite_backups_list_raises_exception(self,
                                                                   mock_get_local_backup_list):
        """
        Test when there are no backups to be processed for the customer.

        Test if get_and_validate_onsite_backups_list will raise an exception when there are no
        backups to be processed for the customer.
        """
        mock_get_local_backup_list.return_value = []

        with self.assertRaises(UploadBackupException):
            self.local_bkp_handler.get_and_validate_onsite_backups_list()


class LocalBackupHandlerValidateOffsiteOnsiteCustomerPathsTestCase(unittest.TestCase):
    """TCs for validate_create_offsite_onsite_base_paths method under local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'create_remote_dir')
    def test_validate_offsite_onsite_customer_paths_remote_dir_creation_exception(
            self, mock_create_remote_dir):
        """Test when there is a problem creating the remote directory."""
        mock_create_remote_dir.return_value = False

        expected_exception_code = ExceptionCodes.CannotCreatePath.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.validate_create_offsite_onsite_base_paths()

        self.assertEqual(expected_exception_code, raised.exception.code.value)

    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'create_remote_dir')
    def test_validate_offsite_onsite_customer_paths_root_temp_dir_creation_exception(
            self, mock_create_remote_dir, mock_create_path):
        """Test when there is a problem creating the local temporary root directory."""
        mock_create_remote_dir.return_value = True
        mock_create_path.return_value = False

        expected_exception_code = ExceptionCodes.CannotCreatePath.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.validate_create_offsite_onsite_base_paths()

        self.assertEqual(expected_exception_code, raised.exception.code.value)

    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'create_remote_dir')
    def test_validate_offsite_onsite_customer_paths_customer_dir_creation_exception(
            self, mock_create_remote_dir, mock_create_path):
        """Test when there is a problem creating the local temporary customer directory."""
        mock_create_remote_dir.return_value = True
        mock_create_path.side_effect = [True, False]

        expected_exception_code = ExceptionCodes.CannotCreatePath.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.validate_create_offsite_onsite_base_paths()

        self.assertEqual(expected_exception_code, raised.exception.code.value)

    @mock.patch(MOCK_PACKAGE + 'create_path')
    @mock.patch(MOCK_PACKAGE + 'create_remote_dir')
    def test_validate_offsite_onsite_customer_paths_success_case(
            self, mock_create_remote_dir, mock_create_path):
        """Test when the validation occurred successfully."""
        mock_create_remote_dir.return_value = True
        mock_create_path.side_effect = [True, True]

        validation_return = self.local_bkp_handler.validate_create_offsite_onsite_base_paths()

        self.assertTrue(validation_return, "Should have returned true.")


class LocalBackupHandlerGetListProcessedVolsNamesOffsiteTestCase(unittest.TestCase):
    """Test cases for get_list_processed_vols_names_offsite method under local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'get_remote_folder_content')
    def test_get_list_processed_vols_names_offsite(self, mock_get_remote_folder_content):
        """
        Test get_list_processed_vols_names_offsite return value.

        Test get_list_processed_vols_names_offsite if it will return the expected processed volumes
        names, if there are volumes already uploaded to offsite.
        """
        processed_vols_relative_path = ["volume0" + PROCESSED_VOLUME_ENDS_WITH,
                                        "volume1" + PROCESSED_VOLUME_ENDS_WITH,
                                        "volume2" + PROCESSED_VOLUME_ENDS_WITH]

        mock_get_remote_folder_content.return_value = processed_vols_relative_path
        expected = ["volume0", "volume1", "volume2"]

        result = self.local_bkp_handler.get_list_processed_vols_names_offsite(MOCK_REMOTE_BKP_PATH)

        self.assertEqual(expected, result)

    @mock.patch(MOCK_PACKAGE + 'get_remote_folder_content')
    def test_get_list_processed_vols_names_offsite_when_no_processed_vols_found_on_offsite(
            self, mock_get_remote_folder_content):
        """
        Test when there are no fully processed volumes found for the backup on offsite.

        Test get_list_processed_vols_names_offsite if it will return an empty list and log a
        warning, in case if no fully processed volumes were found for the backup on offsite.
        """
        mock_get_remote_folder_content.return_value = []
        calls = [mock.call("Off-site backup {} doesn't have any fully processed volumes."
                           .format(MOCK_REMOTE_BKP_PATH))]
        expected = []

        result = self.local_bkp_handler.get_list_processed_vols_names_offsite(MOCK_REMOTE_BKP_PATH)

        self.assertEqual(expected, result)
        self.local_bkp_handler.logger.warning.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'get_remote_folder_content')
    def test_get_list_processed_vols_names_offsite_raise_exception(
            self, mock_get_remote_folder_content):
        """Test get_list_processed_vols_names_offsite if it will raise an exception."""
        mock_get_remote_folder_content.side_effect = UtilsException

        expected_exception_code = ExceptionCodes.FailedToGetProcessedVolsNamesOffsite.value

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.get_list_processed_vols_names_offsite(MOCK_REMOTE_BKP_PATH)

        self.assertEqual(expected_exception_code, raised.exception.code.value)


class LocalBackupHandlerProcessBackupTestCase(unittest.TestCase):
    """Test cases for process_backup method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()
        self.local_bkp_handler.process_backup = get_undecorated_class_method(
            self.local_bkp_handler.process_backup, self.local_bkp_handler)

    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_upload')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_backup_check_disk_space_failed(self, mock_os,
                                                    mock_check_local_disk_space_for_upload):
        """Test when checking disk space fails."""
        mock_os.path.join.return_value = ''

        mock_expected_error_msg = "Mock disk space error message"
        mock_check_local_disk_space_for_upload.side_effect = Exception(mock_expected_error_msg)

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.process_backup('', '', '')

        self.assertEqual(mock_expected_error_msg, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_already_processed_volumes')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_upload')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_backup_descriptor_file_or_volume_list_is_empty(
            self, mock_os, mock_check_local_disk_space_for_upload,
            mock_validate_already_processed_volumes):
        """Test when descriptor file or volume list is empty."""
        mock_os.path.join.return_value = ''
        mock_check_local_disk_space_for_upload.return_value = True

        mock_expected_error_message = "Mock empty list error."
        mock_validate_already_processed_volumes.side_effect = Exception(mock_expected_error_message)

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.process_backup(MOCK_BACKUP_NAME, '', '')

        self.assertEqual(mock_expected_error_message, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_bur_descriptors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_backup_metadata_files')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.check_backup_output_errors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_already_processed_volumes')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_upload')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_backup_volume_to_be_processed_list_is_empty(
            self, mock_os, mock_check_local_disk_space_for_upload,
            mock_validate_already_processed_volumes, mock_check_backup_output_errors,
            mock_process_backup_metadata_files, mock_process_bur_descriptors):
        """Test when there is no volume to be processed."""
        mock_os.path.join.return_value = ''
        mock_check_local_disk_space_for_upload.return_value = True

        mock_validate_already_processed_volumes.return_value = \
            (['file0', 'file1'], ['volume0', 'volume1'], [])

        mock_check_backup_output_errors.return_value = True
        mock_process_backup_metadata_files.return_value = []
        mock_process_bur_descriptors.return_value = True

        process_backup_return = self.local_bkp_handler.process_backup(MOCK_BACKUP_NAME, '', '')

        self.assertIsNotNone(process_backup_return, "Should have returned a tuple.")

        self.assertEqual("{}_{}".format(MOCK_CUSTOMER_NAME, MOCK_BACKUP_NAME),
                         process_backup_return[0])

        self.assertIsNotNone(process_backup_return[1], "Should not return None.")

        self.assertGreater(process_backup_return[2], 0.0, "Time should be bigger than zero.")

    @mock.patch(MOCK_PACKAGE + 'unwrapper_local_backup_handler_function')
    @mock.patch(MOCK_PACKAGE + 'mp.Pool')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_bur_descriptors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_backup_metadata_files')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.check_backup_output_errors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_already_processed_volumes')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_upload')
    def test_process_backup_check_async_calls_per_volume(
            self, mock_check_local_disk_space_for_upload, mock_validate_already_processed_volumes,
            mock_check_backup_output_errors, mock_process_backup_metadata_files,
            mock_process_bur_descriptors, mock_mp_pool,
            mock_unwrapper_local_backup_handler_function):
        """Test the async calls to process the volumes were triggered."""
        mock_check_local_disk_space_for_upload.return_value = True

        mock_volume_list = ['path/to/volume0', 'path/to/volume1']
        mock_validate_already_processed_volumes.return_value = (['file0', 'file1'], [],
                                                                mock_volume_list)

        mock_unwrapper_local_backup_handler_function.return_value = None
        mock_pool_apply_async = mock_mp_pool.return_value.apply_async
        mock_pool_close = mock_mp_pool.return_value.close
        mock_pool_join = mock_mp_pool.return_value.join

        mock_check_backup_output_errors.return_value = True
        mock_process_backup_metadata_files.return_value = []
        mock_process_bur_descriptors.return_value = True

        self.local_bkp_handler.process_backup(MOCK_BACKUP_NAME, MOCK_TMP_BKP_PATH,
                                              MOCK_REMOTE_BKP_PATH)

        for idx in [0, 1]:
            volume_path = 'path/to/volume' + str(idx)
            volume_name = 'volume' + str(idx)
            tmp_volume_path = MOCK_TMP_BKP_PATH + '/volume' + str(idx)

            mock_pool_apply_async.assert_any_call(
                mock_unwrapper_local_backup_handler_function,
                (self.local_bkp_handler.serialized_object, 'process_volume', volume_path,
                 volume_name, tmp_volume_path, MOCK_REMOTE_BKP_PATH),
                callback=self.local_bkp_handler.on_volume_ready)

        assert mock_pool_close.called
        assert mock_pool_join.called

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.check_backup_output_errors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_already_processed_volumes')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_upload')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_backup_backup_output_errors_failed_exception(
            self, mock_os, mock_check_local_disk_space_for_upload,
            mock_validate_already_processed_volumes, mock_check_backup_output_errors):
        """Test when there were errors in the backup upload process."""
        mock_os.path.join.return_value = ''
        mock_check_local_disk_space_for_upload.return_value = True
        mock_validate_already_processed_volumes.return_value = \
            (['file0', 'file1'], ['volume0', 'volume1'], [])

        mock_expected_error_message = "Mock error exception."
        mock_check_backup_output_errors.side_effect = Exception(mock_expected_error_message)

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.process_backup('', '', '')

        self.assertEqual(mock_expected_error_message, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_backup_metadata_files')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.check_backup_output_errors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_already_processed_volumes')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_upload')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_backup_backup_process_backup_metadata_failed_exception(
            self, mock_os, mock_check_local_disk_space_for_upload,
            mock_validate_already_processed_volumes, mock_check_backup_output_errors,
            mock_process_backup_metadata_files):
        """Test when there is a problem to process backup metadata files."""
        mock_os.path.join.return_value = ''
        mock_check_local_disk_space_for_upload.return_value = True
        mock_validate_already_processed_volumes.return_value = \
            (['file0', 'file1'], ['volume0', 'volume1'], [])
        mock_check_backup_output_errors.return_value = True

        mock_expected_error_message = "Mock error exception."
        mock_process_backup_metadata_files.side_effect = Exception(mock_expected_error_message)

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.process_backup('', '', '')

        self.assertEqual(mock_expected_error_message, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_bur_descriptors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_backup_metadata_files')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.check_backup_output_errors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_already_processed_volumes')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_upload')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_backup_process_bur_descriptors_failed_exception(
            self, mock_os, mock_check_local_disk_space_for_upload,
            mock_validate_already_processed_volumes, mock_check_backup_output_errors,
            mock_process_backup_metadata_files, mock_process_bur_descriptors):
        """Test when there is a problem to process BUR descriptor files."""
        mock_os.path.join.return_value = ''
        mock_check_local_disk_space_for_upload.return_value = True
        mock_validate_already_processed_volumes.return_value = \
            (['file0', 'file1'], ['volume0', 'volume1'], [])
        mock_check_backup_output_errors.return_value = True
        mock_process_backup_metadata_files.return_value = []

        mock_expected_error_message = "Mock error exception."
        mock_process_bur_descriptors.side_effect = Exception(mock_expected_error_message)

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.process_backup('', '', '')

        self.assertEqual(mock_expected_error_message, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_bur_descriptors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.process_backup_metadata_files')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.check_backup_output_errors')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.validate_already_processed_volumes')
    @mock.patch(MOCK_PACKAGE + 'check_local_disk_space_for_upload')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_process_backup_check_volume_to_process_not_empty_success_case(
            self, mock_os, mock_check_local_disk_space_for_upload,
            mock_validate_already_processed_volumes, mock_check_backup_output_errors,
            mock_process_backup_metadata_files, mock_process_bur_descriptors):
        """Test when process backup executes normally."""
        mock_os.path.join.return_value = ''
        mock_check_local_disk_space_for_upload.return_value = True
        mock_validate_already_processed_volumes.return_value = \
            (['file0', 'file1'], ['volume0', 'volume1'], ['volume0', 'volume1'])
        mock_check_backup_output_errors.return_value = True
        mock_process_backup_metadata_files.return_value = []
        mock_process_bur_descriptors.return_value = True

        calls = [mock.call("Processing list of volumes: ['volume0', 'volume1'].")]

        with mock.patch(MOCK_PACKAGE + 'mp.Pool'):
            process_backup_return = self.local_bkp_handler.process_backup(MOCK_BACKUP_NAME, '', '')

        self.assertIsNotNone(process_backup_return, "Should have returned a tuple.")

        self.assertEqual("{}_{}".format(MOCK_CUSTOMER_NAME, MOCK_BACKUP_NAME),
                         process_backup_return[0])

        self.assertIsNotNone(process_backup_return[1], "Should not return None.")

        self.assertGreater(process_backup_return[2], 0.0, "Time should be bigger than zero.")

        self.local_bkp_handler.logger.info.assert_has_calls(calls)


class LocalBackupHandlerValidateAlreadyProcessedVolumesTestCase(unittest.TestCase):
    """Test cases for validate_already_processed_volumes located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'get_folder_file_lists_from_dir')
    def test_validate_already_processed_volumes_empty_volume_list_exception(
            self, mock_get_folder_file_lists_from_dir):
        """Test when the volume list returns empty."""
        mock_get_folder_file_lists_from_dir.return_value = ([], [])
        expected_error_msg = "No volume list found for the backup. (mock_tmp_bkp_path)"

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.validate_already_processed_volumes(
                MOCK_TMP_BKP_PATH, '', '')

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'get_folder_file_lists_from_dir')
    def test_validate_already_processed_volumes_empty_file_list_exception(
            self, mock_get_folder_file_lists_from_dir):
        """Test when the metadata file list returns empty."""
        mock_get_folder_file_lists_from_dir.return_value = ([''], [])
        expected_error_msg = "No metadata/descriptor file found for the backup. (mock_tmp_bkp_path)"

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.validate_already_processed_volumes(
                MOCK_TMP_BKP_PATH, '', '')

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_list_processed_vols_names_offsite')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'get_folder_file_lists_from_dir')
    def test_validate_already_processed_volumes_no_processed_no_uploaded_volumes(
            self, mock_get_folder_file_lists_from_dir, mock_os,
            mock_get_list_processed_vols_names_offsite):
        """Test when all volumes should be processed."""
        file_list = ['file0', 'file1']
        volume_list = ['volume0', 'volume1']

        mock_get_folder_file_lists_from_dir.return_value = (volume_list, file_list)
        mock_get_list_processed_vols_names_offsite.return_value = []
        mock_os.path.basename.return_value = ''
        mock_os.path.join.return_value = ''
        mock_os.path.exists.return_value = False

        validation_return = self.local_bkp_handler.validate_already_processed_volumes(
            MOCK_TMP_BKP_PATH, '', '')

        self.assertIsNotNone(validation_return, "Should have returned a tuple.")
        self.assertEqual(file_list, validation_return[0], "Should have returned the file list.")
        self.assertEqual(volume_list, validation_return[1], "Should have returned the volume list.")
        self.assertEqual(volume_list, validation_return[2], "Should have returned the volume list.")

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_list_processed_vols_names_offsite')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.on_volume_ready')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'get_folder_file_lists_from_dir')
    def test_validate_already_processed_volumes_existing_processed_volumes(
            self, mock_get_folder_file_lists_from_dir, mock_os, mock_on_volume_ready,
            mock_get_list_processed_vols_names_offsite):
        """Test when there is already processed volumes in the system."""
        file_list = ['file0', 'file1']
        volume_list = ['volume0', 'volume1', 'volume2', 'volume3']

        mock_get_folder_file_lists_from_dir.return_value = (volume_list, file_list)
        mock_get_list_processed_vols_names_offsite.return_value = []
        mock_os.path.exists.side_effect = [True, False, False, True, False, False]
        mock_os.path.join.side_effect = ['volume0.tar', 'volume1.tar', 'tmp/volume1',
                                         'volume2.tar', 'volume3.tar', 'tmp/volume3']

        calls = [mock.call("Found already processed volume in the system 'volume0.tar'. "
                           "Sending it to off-site."),
                 mock.call("Found already processed volume in the system 'volume2.tar'. "
                           "Sending it to off-site.")]

        mock_on_volume_ready.return_value = None

        volume_to_process_list = ['volume1', 'volume3']

        validation_return = self.local_bkp_handler.validate_already_processed_volumes(
            MOCK_TMP_BKP_PATH, '', '')

        self.local_bkp_handler.logger.info.assert_has_calls(calls)

        self.assertIsNotNone(validation_return, "Should have returned a tuple.")
        self.assertEqual(file_list, validation_return[0], "Should have returned a file list.")
        self.assertEqual(volume_list, validation_return[1], "Should have returned a volume list.")
        self.assertEqual(volume_to_process_list, validation_return[2], "Should have returned a "
                                                                       "volume list.")

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_list_processed_vols_names_offsite')
    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'get_folder_file_lists_from_dir')
    def test_validate_already_processed_volumes_existing_cleaning_unfinished_volumes(
            self, mock_get_folder_file_lists_from_dir, mock_os, mock_remove_path,
            mock_get_list_processed_vols_names_offsite):
        """Test when there is garbage data from unfinished upload execution."""
        file_list = ['file0', 'file1']
        volume_list = ['volume0', 'volume1', 'volume2', 'volume3']

        mock_get_folder_file_lists_from_dir.return_value = (volume_list, file_list)
        mock_get_list_processed_vols_names_offsite.return_value = []
        mock_os.path.exists.side_effect = [False, False, False, True, False, False, False, True]
        mock_remove_path.return_value = None
        mock_os.path.join.side_effect = ['volume0.tar', 'tmp/volume0', 'volume1.tar', 'tmp/volume1',
                                         'volume2.tar', 'tmp/volume2', 'volume3.tar', 'tmp/volume3']

        calls = [mock.call("Cleaning up unfinished volume 'tmp/volume1'."),
                 mock.call("Cleaning up unfinished volume 'tmp/volume3'.")]

        validation_return = self.local_bkp_handler.validate_already_processed_volumes(
            MOCK_TMP_BKP_PATH, '', '')

        self.local_bkp_handler.logger.info.assert_has_calls(calls)

        self.assertIsNotNone(validation_return, "Should have returned a tuple.")
        self.assertEqual(file_list, validation_return[0], "Should have returned a file list.")
        self.assertEqual(volume_list, validation_return[1], "Should have returned a volume list.")
        self.assertEqual(volume_list, validation_return[2], "Should have returned a volume list.")

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_list_processed_vols_names_offsite')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'get_folder_file_lists_from_dir')
    def test_validate_already_processed_volumes_existing_uploaded_volumes(
            self, mock_get_folder_file_lists_from_dir, mock_os,
            mock_get_list_processed_vols_names_offsite):
        """Test when there are existing uploaded volumes."""
        file_list = ['file0', 'file1']
        volume_list = ['volume0', 'volume1']

        mock_get_folder_file_lists_from_dir.return_value = (volume_list, file_list)
        mock_get_list_processed_vols_names_offsite.return_value = volume_list
        mock_os.path.basename.side_effect = volume_list

        calls = [mock.call("Found already uploaded volume 'volume0'. Skipping it."),
                 mock.call("Found already uploaded volume 'volume1'. Skipping it.")]

        validation_return = self.local_bkp_handler.validate_already_processed_volumes(
            MOCK_TMP_BKP_PATH, '', '')

        self.local_bkp_handler.logger.info.assert_has_calls(calls)

        self.assertIsNotNone(validation_return, "Should have returned a tuple.")
        self.assertEqual(file_list, validation_return[0], "Should have returned a file list.")
        self.assertEqual(volume_list, validation_return[1], "Should have returned a volume list.")
        self.assertEqual([], validation_return[2], "Should have returned empty.")

    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.on_volume_ready')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_empty_volume_output')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.get_list_processed_vols_names_offsite')
    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_PACKAGE + 'get_folder_file_lists_from_dir')
    def test_validate_already_processed_volumes_existing_uploaded_processed_unfinished_volumes(
            self, mock_get_folder_file_lists_from_dir, mock_os, mock_remove_path,
            mock_get_list_processed_vols_names_offsite, mock_get_empty_volume_output,
            mock_on_volume_ready):
        """Test when there are existing uploaded, processed and unfinished volumes in the system."""
        file_list = ['file0', 'file1']
        volume_list = ['volume0', 'volume1', 'volume2', 'volume3', 'volume4', 'volume5']

        mock_get_folder_file_lists_from_dir.return_value = (volume_list, file_list)

        uploaded_volumes = ['volume0', 'volume1']

        mock_get_list_processed_vols_names_offsite.return_value = uploaded_volumes
        mock_os.path.basename.side_effect = volume_list
        mock_os.path.exists.side_effect = [True, True, False, True, False, True]
        mock_get_empty_volume_output.return_value = {}
        mock_on_volume_ready.return_value = None
        mock_remove_path.return_value = None
        mock_os.path.join.side_effect = ['tmp/volume2.tar', 'tmp/volume3.tar',
                                         'tmp/volume4.tar', 'tmp/volume4',
                                         'tmp/volume5.tar', 'tmp/volume5']

        calls = [mock.call("Found already uploaded volume 'volume0'. Skipping it."),
                 mock.call("Found already uploaded volume 'volume1'. Skipping it."),
                 mock.call("Found already processed volume in the system 'tmp/volume2.tar'. "
                           "Sending it to off-site."),
                 mock.call("Found already processed volume in the system 'tmp/volume3.tar'. "
                           "Sending it to off-site."),
                 mock.call("Cleaning up unfinished volume 'tmp/volume4'."),
                 mock.call("Cleaning up unfinished volume 'tmp/volume5'.")]

        volume_to_process_list = ['volume4', 'volume5']

        validation_return = self.local_bkp_handler.validate_already_processed_volumes(
            MOCK_TMP_BKP_PATH, '', '')

        self.local_bkp_handler.logger.info.assert_has_calls(calls)

        self.assertIsNotNone(validation_return, "Should have returned a tuple.")
        self.assertEqual(file_list, validation_return[0], "Should have returned a file list.")
        self.assertEqual(volume_list, validation_return[1], "Should have returned a volume list.")
        self.assertEqual(volume_to_process_list, validation_return[2], "Should have returned a "
                                                                       "volume list.")


class LocalBackupHandlerProcessBurDescriptorsTestCase(unittest.TestCase):
    """Test cases for process_bur_descriptors method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.create_transfer_pickle_file')
    def test_process_bur_descriptors_transferring_exception(
            self, mock_create_transfer_pickle_file, mock_check_remote_path_exists):
        """Test when there is an error while creating the file list descriptor."""
        calls = [mock.call("Creating and sending BUR file descriptor file '{}' to off-site."
                           .format(BUR_FILE_LIST_DESCRIPTOR_FILE_NAME))]

        mock_check_remote_path_exists.return_value = False

        mock_expected_error_msg = "Mock error message."
        mock_create_transfer_pickle_file.side_effect = Exception(mock_expected_error_msg)

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.process_bur_descriptors(BUR_FILE_LIST_DESCRIPTOR_FILE_NAME,
                                                           '', '', '')

        self.assertEqual(mock_expected_error_msg, cex.exception.message)

        self.local_bkp_handler.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    def test_process_bur_descriptors_already_uploaded_descriptor(
            self, mock_check_remote_path_exists):
        """Test when the descriptor file is already on off-site."""
        calls = [mock.call("Backup descriptor {} was already uploaded to off-site."
                           .format(BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME))]

        mock_check_remote_path_exists.return_value = True

        self.local_bkp_handler.process_bur_descriptors(BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME, '',
                                                       '', '')

        self.local_bkp_handler.logger.warning.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    @mock.patch(MOCK_PACKAGE + 'LocalBackupHandler.create_transfer_pickle_file')
    def test_process_bur_descriptors_success_case(
            self, mock_create_transfer_pickle_file, mock_check_remote_path_exists):
        """Test when the descriptor was created and uploaded successfully."""
        calls = [mock.call("Creating and sending BUR file descriptor file '{}' to off-site."
                           .format(BUR_FILE_LIST_DESCRIPTOR_FILE_NAME))]

        mock_check_remote_path_exists.return_value = False
        mock_create_transfer_pickle_file.return_value = True

        process_descriptor_result = self.local_bkp_handler.process_bur_descriptors(
            BUR_FILE_LIST_DESCRIPTOR_FILE_NAME, '', '', '')

        self.assertTrue(process_descriptor_result, "Should have returned True.")

        self.local_bkp_handler.logger.info.assert_has_calls(calls)


class LocalBackupHandlerProcessBackupMetadataFilesTestCase(unittest.TestCase):
    """Test cases for process_backup_metadata_files method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'compress_file')
    def test_process_backup_metadata_files_all_valid_files_processed(
            self, mock_compress_file, mock_remove_path, mock_transfer_file,
            mock_check_remote_path_exists):
        """Test when all files are processed correctly."""
        mock_check_remote_path_exists.return_value = False
        mock_file_list = [SUCCESS_FLAG_FILE, BACKUP_META_FILE]

        self.local_bkp_handler.gpg_manager.compress_encrypt_file.return_value = BACKUP_META_FILE

        mock_target_dir = "{}:{}".format(self.local_bkp_handler.offsite_config.host,
                                         MOCK_REMOTE_BKP_PATH)

        calls = [mock.call("Transferring backup metadata file 'BACKUP_OK' to '{}'."
                           .format(mock_target_dir)),
                 mock.call("Archiving backup metadata file '{}'.".format(BACKUP_META_FILE)),
                 mock.call("Transferring backup metadata file '{0}' to '{1}'."
                           .format(BACKUP_META_FILE, mock_target_dir))]

        mock_compress_file.return_value = BACKUP_META_FILE
        mock_remove_path.return_value = True
        mock_transfer_file.return_value = None

        process_result = self.local_bkp_handler.process_backup_metadata_files(mock_file_list, '',
                                                                              MOCK_REMOTE_BKP_PATH)

        expected_file_list = [SUCCESS_FLAG_FILE, BACKUP_META_FILE]
        self.assertIsNotNone(process_result, "Should have returned a list.")
        self.assertEqual(expected_file_list, process_result, "File list should be {}.".format(
            mock_file_list))

        self.local_bkp_handler.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    def test_process_backup_metadata_files_compression_encryption_exception(
            self, mock_check_remote_path_exists, mock_transfer_file):
        """Test when one of the files could not be encrypted."""
        mock_check_remote_path_exists.return_value = False
        self.local_bkp_handler.gpg_manager.compress_encrypt_file.side_effect = \
            Exception("Mock error message.")
        mock_transfer_file.return_value = None

        mock_file_list = [SUCCESS_FLAG_FILE, BACKUP_META_FILE]
        with self.assertRaises(Exception) as raised:
            self.local_bkp_handler.process_backup_metadata_files(mock_file_list, '', '')

        self.assertIn("Mock error message.", raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'compress_file')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    def test_process_backup_metadata_files_archiving_exception(
            self, mock_check_remote_path_exists, mock_transfer_file, mock_compress_file):
        """Test when one of the files could not be archived."""
        mock_check_remote_path_exists.return_value = False
        self.local_bkp_handler.gpg_manager.compress_encrypt_file.return_value = BACKUP_META_FILE
        mock_compress_file.side_effect = Exception("Mock error message.")
        mock_transfer_file.return_value = None

        mock_file_list = [SUCCESS_FLAG_FILE, BACKUP_META_FILE]
        with self.assertRaises(Exception) as raised:
            self.local_bkp_handler.process_backup_metadata_files(mock_file_list, '', '')

        self.assertIn("Mock error message.", raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'compress_file')
    def test_process_backup_metadata_files_file_removal_exception(
            self, mock_compress_file, mock_remove_path, mock_transfer_file,
            mock_check_remote_path_exists):
        """Test when one of the files is processed but could not be removed."""
        mock_check_remote_path_exists.return_value = False
        mock_file_list = [SUCCESS_FLAG_FILE, BACKUP_META_FILE]

        self.local_bkp_handler.gpg_manager.compress_encrypt_file.return_value = BACKUP_META_FILE
        mock_compress_file.return_value = ''
        mock_remove_path.return_value = False
        mock_transfer_file.return_value = None

        with self.assertRaises(UploadBackupException) as raised:
            self.local_bkp_handler.process_backup_metadata_files(mock_file_list, '', '')

        self.assertIn("File cannot be removed.", raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'check_remote_path_exists')
    def test_process_backup_metadata_files_all_files_already_uploaded(
            self, mock_check_remote_path_exists):
        """Test when one of the files is processed but could not be removed."""
        mock_check_remote_path_exists.return_value = True

        calls = [mock.call("Backup metadata BACKUP_OK was already uploaded to off-site."),
                 mock.call("Backup metadata {} was already uploaded to off-site."
                           .format(BACKUP_META_FILE))]

        mock_file_list = [SUCCESS_FLAG_FILE, BACKUP_META_FILE]
        result = self.local_bkp_handler.process_backup_metadata_files(mock_file_list, '', '')

        self.assertEqual([], result, "File list should be empty.")

        self.local_bkp_handler.logger.warning.assert_has_calls(calls)


class LocalBackupHandlerOnVolumeReadyTestCase(unittest.TestCase):
    """Test cases for on_volume_ready method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    def test_on_volume_ready_failed_processing(self):
        """Test when there is a problem in the volume processing."""
        mock_volume_output = {VOLUME_OUTPUT_KEYS.status.name: False}

        mock_process_result = (MOCK_VOLUME_NAME, mock_volume_output, '')

        on_volume_ready_result = self.local_bkp_handler.on_volume_ready(mock_process_result)

        calls = [mock.call("An error happened while processing volume '{}'.".format(
            MOCK_VOLUME_NAME))]

        self.assertFalse(on_volume_ready_result, "Should have returned false.")

        self.local_bkp_handler.logger.error.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'mp.Pool')
    @mock.patch(MOCK_PACKAGE + 'get_formatted_size_on_disk')
    def test_on_volume_ready_successful_processing(self, mock_get_formatted_size_on_disk,
                                                   mock_mp_pool):
        """Test when the volume was processed correctly and it was sent to the transfer pool."""
        mock_volume_output = {VOLUME_OUTPUT_KEYS.status.name: True,
                              VOLUME_OUTPUT_KEYS.volume_path.name: MOCK_VOLUME_NAME}

        mock_get_formatted_size_on_disk.return_value = 'mock_size'

        mock_process_result = (MOCK_VOLUME_NAME, mock_volume_output, '')

        mock_mp_pool.return_value.apply_async = None
        self.local_bkp_handler.transfer_pool = mock_mp_pool

        on_volume_ready_result = self.local_bkp_handler.on_volume_ready(mock_process_result)

        calls = [mock.call("Volume '{}' processed successfully. Size: mock_size. "
                           "Starting to send it.".format(MOCK_VOLUME_NAME))]

        self.assertTrue(on_volume_ready_result, "Should have returned true.")

        self.local_bkp_handler.logger.info.assert_has_calls(calls)


class LocalBackupHandlerCheckBackupOutputErrorsTestCase(unittest.TestCase):
    """Test cases for get_backup_output_errors method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    def test_check_backup_output_errors_failed_volume(self):
        """Tests that when there are failed volumes on the batch, these are detected."""
        mock_bkp_out_per_vol_dic_with_error = {
            'volume0': {'status': False,
                        'output': 'some error in volume 0'},
            'volume1': {'status': True,
                        'output': ''},
            'volume2': {'status': False,
                        'output': 'some error in volume 2'}
        }

        self.local_bkp_handler.backup_output_dict = mock_bkp_out_per_vol_dic_with_error

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.check_backup_output_errors()

        self.assertIn("'some error in volume 0'", cex.exception.message)
        self.assertIn("'some error in volume 2'", cex.exception.message)

    def test_check_backup_output_errors_no_errors(self):
        """Tests that no error message is returned when no backup is provided."""
        mock_bkp_out_per_vol_dic_no_error = {
            'volume0': {'status': True,
                        'output': 'some error in volume 0'},
            'volume1': {'status': True,
                        'output': ''},
        }
        self.local_bkp_handler.backup_output_dict = mock_bkp_out_per_vol_dic_no_error

        self.assertTrue(self.local_bkp_handler.check_backup_output_errors())


class LocalBackupHandlerProcessVolumeTestCase(unittest.TestCase):
    """Test cases for process_volume method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'create_path')
    def test_process_volume_temp_backup_folder_not_created_exception(
            self, mock_create_path):
        """Test when the temporary folder could no be created."""
        mock_create_path.return_value = False
        expected_error_message = "Error while processing volume. " \
                                 "Error Code 35. Path informed cannot be created."

        processed_volume = self.local_bkp_handler.process_volume(MOCK_VOLUME_NAME, '')

        self.assertTrue(isinstance(processed_volume, dict))
        self.assertTrue(VOLUME_OUTPUT_KEYS.output.name in processed_volume.keys())
        self.assertEqual(expected_error_message, processed_volume[VOLUME_OUTPUT_KEYS.output.name])
        self.assertFalse(processed_volume[VOLUME_OUTPUT_KEYS.status.name])

    @mock.patch(MOCK_PACKAGE + 'create_path')
    def test_process_volume_compress_encrypt_file_list_exception(self, mock_create_path):
        """Test when the compress_encrypt_file_list function raised a problem."""
        mock_create_path.return_value = True

        self.local_bkp_handler.gpg_manager.compress_encrypt_file_list.side_effect = \
            GnupgException(ExceptionCodes.EncryptError)

        expected_error_msg = "Error while processing volume. " \
                             "Error Code 68. File encryption could not be completed."

        processed_volume = self.local_bkp_handler.process_volume(MOCK_VOLUME_NAME, '')

        self.assertEqual(expected_error_msg, processed_volume[VOLUME_OUTPUT_KEYS.output.name])
        self.assertFalse(processed_volume[VOLUME_OUTPUT_KEYS.status.name])

    @mock.patch(MOCK_PACKAGE + 'compress_file')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    def test_process_volume_compress_file_exception(
            self, mock_create_path, mock_compress_file):
        """Test when the compression of the processed volume raised a problem."""
        mock_create_path.return_value = True
        self.local_bkp_handler.gpg_manager.compress_encrypt_file_list.return_value = True

        mock_compress_file.side_effect = UtilsException(ExceptionCodes.GzipCommandError)

        expected_error_msg = "Error while processing volume. " \
                             "Error Code 48. Gzip command returned error code."

        processed_volume = self.local_bkp_handler.process_volume(MOCK_VOLUME_NAME, '')

        self.assertEqual(expected_error_msg, processed_volume[VOLUME_OUTPUT_KEYS.output.name])
        self.assertFalse(processed_volume[VOLUME_OUTPUT_KEYS.status.name])

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'compress_file')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    def test_process_volume_temp_backup_folder_not_removed_exception(
            self, mock_create_path, mock_compress_file, mock_remove_path):
        """Test when the temporary folder could not be removed."""
        mock_create_path.return_value = True
        self.local_bkp_handler.gpg_manager.compress_encrypt_file_list.return_value = True
        mock_compress_file.return_value = ''
        mock_remove_path.return_value = False

        expected_error_msg = "Error while processing volume. " \
                             "Error Code 60. Path(s) informed cannot be removed."

        processed_volume = self.local_bkp_handler.process_volume(MOCK_VOLUME_NAME, '')

        self.assertEqual(expected_error_msg, processed_volume[VOLUME_OUTPUT_KEYS.output.name])
        self.assertFalse(processed_volume[VOLUME_OUTPUT_KEYS.status.name])

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'compress_file')
    @mock.patch(MOCK_PACKAGE + 'create_path')
    def test_process_volume_successful_scenario(
            self, mock_create_path, mock_compress_file, mock_remove_path):
        """Test when the volume was processed successfully."""
        mock_create_path.return_value = True
        self.local_bkp_handler.gpg_manager.compress_encrypt_file_list.return_value = True

        mock_tar_volume_name = 'tar_volume'
        mock_compress_file.return_value = mock_tar_volume_name

        mock_remove_path.return_value = True

        processed_volume = self.local_bkp_handler.process_volume(MOCK_VOLUME_NAME, '')

        self.assertTrue(VOLUME_OUTPUT_KEYS.volume_path.name in processed_volume.keys(),
                        "Should have returned a dict with volume_path key.")

        self.assertEqual(mock_tar_volume_name, processed_volume[
            VOLUME_OUTPUT_KEYS.volume_path.name], "Should have returned status=True.")

        self.assertTrue(processed_volume[VOLUME_OUTPUT_KEYS.status.name],
                        "Should have returned status=True.")


class LocalBackupHandlerTransferBackupVolumeToOffsiteTestCase(unittest.TestCase):
    """Test cases for transfer_backup_volume_to_offsite method under local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    def test_transfer_backup_volume_to_offsite_transfer_file_exception(
            self, mock_transfer_file):
        """Test when there is a problem to transfer the volume to off-site."""
        mock_transfer_file.side_effect = RsyncException
        expected_error_msg = "Error while transferring volume. Error Code 30. Something went wrong."
        mock_vol_output = {}

        transfer_result = \
            self.local_bkp_handler.transfer_backup_volume_to_offsite(
                MOCK_VOLUME_NAME, mock_vol_output, '', '')

        self.assertIsNotNone(transfer_result)
        self.assertEqual(MOCK_VOLUME_NAME, transfer_result[0])
        self.assertEqual(mock_vol_output, transfer_result[1])
        self.assertTrue(VOLUME_OUTPUT_KEYS.status.name in mock_vol_output.keys())
        self.assertFalse(mock_vol_output[VOLUME_OUTPUT_KEYS.status.name])
        self.assertTrue(VOLUME_OUTPUT_KEYS.output.name in mock_vol_output.keys())
        self.assertEqual(expected_error_msg, mock_vol_output[VOLUME_OUTPUT_KEYS.output.name])
        self.assertTrue(VOLUME_OUTPUT_KEYS.rsync_output.name in mock_vol_output.keys())
        self.assertTrue(VOLUME_OUTPUT_KEYS.transfer_time.name in mock_vol_output.keys())

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    def test_transfer_backup_volume_to_offsite_remove_file_exception(
            self, mock_transfer_file, mock_remove_path):
        """Test when there is a problem to remove transferred file from NFS."""
        mock_transfer_file.return_value = None
        mock_remove_path.return_value = False
        mock_volume_output = {}
        expected_error_msg = "Error while transferring volume. Error Code 60. " \
                             "Path(s) informed cannot be removed. (mock_tmp_bkp_path)"
        calls = [mock.call("Volume 'mock_tmp_bkp_path' was successfully transferred to off-site "
                           "for customer mock_customer.")]

        transfer_result = \
            self.local_bkp_handler.transfer_backup_volume_to_offsite(
                MOCK_VOLUME_NAME, mock_volume_output, MOCK_TMP_BKP_PATH, '')

        self.assertIsInstance(transfer_result, tuple)
        self.assertEqual(MOCK_VOLUME_NAME, transfer_result[0])
        self.assertEqual(expected_error_msg, mock_volume_output[VOLUME_OUTPUT_KEYS.output.name])
        self.local_bkp_handler.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    def test_transfer_backup_volume_to_offsite_success_case(
            self, mock_transfer_file, mock_remove_path):
        """Test when the volume was successfully transferred to offsite."""
        mock_transfer_file.return_value = None
        mock_remove_path.return_value = True
        calls = [mock.call("Volume 'mock_tmp_bkp_path' was successfully transferred to off-site "
                           "for customer mock_customer.")]
        mock_vol_output = {}

        transfer_result = \
            self.local_bkp_handler.transfer_backup_volume_to_offsite(
                MOCK_VOLUME_NAME, mock_vol_output, MOCK_TMP_BKP_PATH, '')

        self.local_bkp_handler.logger.info.assert_has_calls(calls)

        self.assertTrue(VOLUME_OUTPUT_KEYS.status.name in mock_vol_output.keys(),
                        "Should have returned a dict with status key.")

        self.assertTrue(mock_vol_output[VOLUME_OUTPUT_KEYS.status.name],
                        "Should have returned status=True.")

        self.assertTrue(VOLUME_OUTPUT_KEYS.output.name in mock_vol_output.keys(),
                        "Should have returned a dict with output key.")

        self.assertEqual("", mock_vol_output[VOLUME_OUTPUT_KEYS.output.name])

        self.assertTrue(VOLUME_OUTPUT_KEYS.rsync_output.name in mock_vol_output.keys(),
                        "Should have returned a dict with rsync_output key.")

        self.assertTrue(VOLUME_OUTPUT_KEYS.transfer_time.name in mock_vol_output.keys(),
                        "Should have returned a dict with transfer_time key.")

        self.assertTrue(transfer_result, "Should have returned True.")


class LocalBackupHandlerCleanLocalBackupTestCase(unittest.TestCase):
    """Test cases for clean_local_backup method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_clean_local_backup_do_not_remove_backup(self, mock_os):
        """Test when the minimum number of backups on NFS is reached.

        So that the backup can't be deleted.
        """
        mock_os.listdir.return_value = ['bkp0']
        mock_os.path.isfile.return_value = False

        calls = [mock.call("There are currently 1 backup(s) in the folder "
                           "'mock_local_backup_path'.")]

        clean_result = self.local_bkp_handler.clean_local_backup('bkp0')

        expected_output_message = "Backup 'bkp0' NOT removed. Just 1 backup found."

        self.assertFalse(clean_result[0], "Should have returned False.")
        self.assertEqual(expected_output_message, clean_result[1])

        self.local_bkp_handler.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_clean_local_backup_remove_backup_does_not_exists(self, mock_os, mock_remove_path):
        """Test when it is not possible to delete the informed backup."""
        mock_os.listdir.return_value = ['bkp0', 'bkp1']
        mock_os.path.isfile.return_value = False
        mock_remove_path.return_value = False

        calls = [mock.call("There are currently 2 backup(s) in the folder "
                           "'mock_local_backup_path'."),
                 mock.call("Removing backup 'bkp0' from NFS server.")]

        clean_result = self.local_bkp_handler.clean_local_backup('bkp0')

        expected_output_message = "Error while deleting folder 'bkp0' from NFS server."

        self.assertFalse(clean_result[0], "Should have returned False.")
        self.assertEqual(expected_output_message, clean_result[1])

        self.local_bkp_handler.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_clean_local_backup_remove_backup_success_case(self, mock_os, mock_remove_path):
        """Test when the backup was successfully deleted."""
        mock_os.listdir.return_value = ['bkp0', 'bkp1']
        mock_os.path.isfile.return_value = False
        mock_remove_path.return_value = True

        calls = [mock.call("There are currently 2 backup(s) in the folder "
                           "'mock_local_backup_path'."),
                 mock.call("Removing backup 'bkp0' from NFS server.")]

        clean_result = self.local_bkp_handler.clean_local_backup('bkp0')

        expected_output_message = "Backup 'bkp0' removed successfully."

        self.assertTrue(clean_result[0], "Should have returned True.")
        self.assertEqual(expected_output_message, clean_result[1])

        self.local_bkp_handler.logger.info.assert_has_calls(calls)


class LocalBackupHandlerGetLocalBackupListTestCase(unittest.TestCase):
    """Test cases for get_local_backup_list method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_local_backup_list_source_path_does_not_exist(self, mock_os):
        """Test when the source path does not exist."""
        mock_os.path.exists.return_value = False

        get_list_return = self.local_bkp_handler.get_local_backup_list()

        self.assertIsNone(get_list_return, "Should have returned None.")

    @mock.patch(MOCK_PACKAGE + 'validate_backup_per_volume')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_local_backup_list_each_folder_has_an_issue(
            self, mock_os, mock_validate_backup_per_volume):
        """Test when the folder list inside the informed backup path has all possible issues."""
        mock_os.path.exists.return_value = True
        mock_list_dir = ['is_file', 'invalid_backup']
        mock_os.listdir.return_value = mock_list_dir
        mock_os.path.join.side_effect = ['source/is_file', 'source/invalid_backup']
        mock_os.path.isfile.side_effect = [True, False]
        mock_validate_backup_per_volume.return_value = False

        calls = [mock.call("Found a file 'source/is_file' inside backup folder."),
                 mock.call("Backup 'source/invalid_backup' is not valid.")]

        mock_os.path.getmtime.return_value = 1
        get_list_return = self.local_bkp_handler.get_local_backup_list()

        self.assertEqual([], get_list_return, "Should have returned empty list.")

        self.local_bkp_handler.logger.warning.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'validate_backup_per_volume')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_local_backup_list_one_valid_backup(self, mock_os, mock_validate_backup_per_volume):
        """Test when there is one valid backup in the folder."""
        mock_os.path.exists.return_value = True
        mock_list_dir = ['invalid_backup', 'valid_backup']
        mock_os.listdir.return_value = mock_list_dir
        mock_os.path.join.side_effect = ['source/invalid_backup', 'source/valid_backup',
                                         'valid_backup']
        mock_os.path.isfile.return_value = False
        mock_validate_backup_per_volume.side_effect = [False, True]

        mock_os.path.getmtime.return_value = 1

        calls = [mock.call("Backup 'source/invalid_backup' is not valid.")]

        get_list_return = self.local_bkp_handler.get_local_backup_list()

        self.assertEqual(['valid_backup'], get_list_return, "Should have returned a list with 1 "
                                                            "element.")
        self.local_bkp_handler.logger.warning.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'validate_backup_per_volume')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_local_backup_list_several_valid_backups(
            self, mock_os, mock_validate_backup_per_volume):
        """Test when there is more than one valid backup in the folder."""
        mock_os.path.exists.return_value = True

        mock_list_dir = ['is_valid_first', 'is_valid_second', 'is_valid_third']
        mock_index_dir = [1, 2, 3]

        mock_os.listdir.return_value = mock_list_dir
        mock_os.path.join.return_value = ''
        mock_os.path.isfile.return_value = False
        mock_validate_backup_per_volume.return_value = True
        mock_os.path.getmtime.side_effect = mock_index_dir

        get_list_return = self.local_bkp_handler.get_local_backup_list()

        self.assertEqual(len(mock_list_dir), len(get_list_return))

        self.assertEqual(['is_valid_first', 'is_valid_second', 'is_valid_third'], get_list_return)


class LocalBackupHandlerCreateTransferPickleFileTestCase(unittest.TestCase):
    """Test Cases for create_transfer_pickle_file method located in local_backup_handler.py."""

    def setUp(self):
        """Set up the test constants."""
        self.local_bkp_handler = get_local_backup_handler()

    @mock.patch(MOCK_PACKAGE + 'create_pickle_file')
    def test_create_transfer_pickle_file_creation_exception(self, mock_create_pickle_file):
        """Test when there is an error in the pickle file creation."""
        mock_exception_message = 'Mock create pickle exception.'
        mock_create_pickle_file.side_effect = Exception(mock_exception_message)

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.create_transfer_pickle_file('', [], '')

        self.assertEqual(mock_exception_message, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    @mock.patch(MOCK_PACKAGE + 'create_pickle_file')
    def test_create_transfer_pickle_file_transfer_exception(
            self, mock_create_pickle_file, mock_transfer_file):
        """Test when there is an error in the transferring of the file."""
        mock_create_pickle_file.return_value = ''

        mock_exception_message = 'Mock transfer exception.'
        mock_transfer_file.side_effect = Exception(mock_exception_message)

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.create_transfer_pickle_file('', [], '')

        self.assertEqual(mock_exception_message, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    @mock.patch(MOCK_PACKAGE + 'create_pickle_file')
    def test_create_transfer_pickle_file_removal_exception(
            self, mock_create_pickle_file, mock_transfer_file, mock_remove_path):
        """Test when there is an error in the removal of the pickle file."""
        mock_create_pickle_file.return_value = ''
        mock_transfer_file.return_value = None

        mock_exception_message = 'Mock remove exception.'
        mock_remove_path.side_effect = Exception(mock_exception_message)

        with self.assertRaises(Exception) as cex:
            self.local_bkp_handler.create_transfer_pickle_file('', [], '')

        self.assertEqual(mock_exception_message, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'RsyncManager.transfer_file')
    @mock.patch(MOCK_PACKAGE + 'create_pickle_file')
    def test_create_transfer_pickle_file_successful_case(
            self, mock_create_pickle_file, mock_transfer_file, mock_remove_path):
        """Test when the pickle file was created, transferred and removed successfully."""
        mock_create_pickle_file.return_value = ''
        mock_transfer_file.return_value = None
        mock_remove_path.return_value = True

        result = self.local_bkp_handler.create_transfer_pickle_file('', [], '')

        self.assertTrue(result, "Should have returned true.")
