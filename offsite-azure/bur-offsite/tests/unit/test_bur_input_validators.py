##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module for unit testing the bur_input_validators.py script."""

import unittest

import mock

import backup.bur_input_validators as validators
from backup.constants import DEFAULT_NUM_PROCESSORS, DEFAULT_NUM_THREADS
from backup.exceptions import BackupSettingsException, InputValidatorsException
from backup.main import SCRIPT_OPERATIONS

MOCK_BUR_INPUT_VALIDATORS = 'backup.bur_input_validators'
MOCK_BACKUP_SETTINGS = 'backup.backup_settings'
MOCK_LOGGER = 'backup.bur_input_validators.CustomLogger'
MOCK_CPU_COUNT = 'backup.bur_input_validators.multiprocessing.cpu_count'

SCRIPT_UPLOAD = 1
SCRIPT_DOWNLOAD = 2
SCRIPT_RETENTION = 3
SCRIPT_INVALID_OPTION = -1
CUSTOMER_NAME = "fake_customer"
BACKUP_TAG = "fake_tag"
NO_CUSTOMER = ""
NO_BACKUP_TAG = ""
CONFIG_FILE_NAME = 'fake_config_file'


class BurInputValidatorsPrepareLogFileName(unittest.TestCase):
    """Class for unit testing the prepare_log_file_name function."""

    def test_prepare_log_file_name_upload_all_customers(self):
        """Assert if log filename is returned when there is no customer or backup_tag informed."""
        correct_log_name = "all_customers_upload.log"
        result = validators.prepare_log_file_name(SCRIPT_UPLOAD, SCRIPT_OPERATIONS,
                                                  NO_CUSTOMER, NO_BACKUP_TAG)

        self.assertEqual(correct_log_name, result)

    def test_prepare_log_file_name_upload_customer(self):
        """Assert if a customer_upload.log is returned when there is a customer_name informed."""
        correct_log_name = "fake_customer_upload.log"
        result = validators.prepare_log_file_name(SCRIPT_UPLOAD, SCRIPT_OPERATIONS,
                                                  CUSTOMER_NAME, NO_BACKUP_TAG)

        self.assertEqual(correct_log_name, result)

    def test_prepare_log_file_name_download_customer_backup_tag(self):
        """Assert if log filename is returned when customer_name and backup_tag are informed."""
        correct_log_name = "fake_customer_fake_tag_download.log"
        result = validators.prepare_log_file_name(SCRIPT_DOWNLOAD, SCRIPT_OPERATIONS,
                                                  CUSTOMER_NAME, BACKUP_TAG)

        self.assertEqual(correct_log_name, result)

    def test_prepare_log_file_name_download_customer(self):
        """Assert if a customer_download.log is returned when there is a customer_name informed."""
        correct_log_name = "fake_customer_download.log"
        result = validators.prepare_log_file_name(SCRIPT_DOWNLOAD, SCRIPT_OPERATIONS,
                                                  CUSTOMER_NAME, NO_BACKUP_TAG)

        self.assertEqual(correct_log_name, result)

    def test_prepare_log_file_name_download_backup_tag(self):
        """Assert if a tag_download.log is returned when there is a backup_tag informed."""
        correct_log_name = "fake_tag_download.log"
        result = validators.prepare_log_file_name(SCRIPT_DOWNLOAD, SCRIPT_OPERATIONS,
                                                  NO_CUSTOMER, BACKUP_TAG)

        self.assertEqual(correct_log_name, result)

    def test_prepare_log_file_name_download(self):
        """Assert if log filename is returned when there is no customer or backup_tag informed."""
        correct_log_name = "error_download.log"
        result = validators.prepare_log_file_name(SCRIPT_DOWNLOAD, SCRIPT_OPERATIONS,
                                                  NO_CUSTOMER, NO_BACKUP_TAG)

        self.assertEqual(correct_log_name, result)

    def test_prepare_log_file_name_retention_all_customers(self):
        """Assert if log filename is returned when there is no customer_name informed."""
        correct_log_name = "all_customers_retention.log"
        result = validators.prepare_log_file_name(SCRIPT_RETENTION, SCRIPT_OPERATIONS,
                                                  NO_CUSTOMER, NO_BACKUP_TAG)

        self.assertEqual(correct_log_name, result)

    def test_prepare_log_file_name_retention_customer(self):
        """Assert if customer_retention.log is returned when there is a customer_name informed."""
        correct_log_name = "fake_customer_retention.log"
        result = validators.prepare_log_file_name(SCRIPT_RETENTION, SCRIPT_OPERATIONS,
                                                  CUSTOMER_NAME, NO_BACKUP_TAG)

        self.assertEqual(correct_log_name, result)

    def test_prepare_log_file_name_exception(self):
        """Asserts if an Exception is raised when an invalid script operation is informed."""
        with self.assertRaises(InputValidatorsException) as raised:
            validators.prepare_log_file_name(SCRIPT_INVALID_OPTION, SCRIPT_OPERATIONS,
                                             NO_CUSTOMER, NO_BACKUP_TAG)

        expected_error_message = "Operation Code informed is not supported."

        self.assertIn(expected_error_message, raised.exception.message)


class BurInputValidatorsValidateScriptSettings(unittest.TestCase):
    """Class for unit testing the validate_script_settings function."""

    def setUp(self):
        """Set up test constants/variables."""
        with mock.patch(MOCK_BACKUP_SETTINGS + '.NotificationHandler') as notification_handler:
            self.mock_notification_handler = notification_handler

        with mock.patch('backup.gnupg_manager.GnupgManager') as gnupg:
            self.mock_gnupg_manager = gnupg

        with mock.patch(MOCK_BACKUP_SETTINGS + '.OffsiteConfig') as offsite_config:
            self.mock_offsite_config = offsite_config

        with mock.patch(MOCK_BACKUP_SETTINGS + '.EnmConfig') as enm_config:
            self.mock_customer_config_dict = dict({'customer_0': enm_config})

        with mock.patch(MOCK_BACKUP_SETTINGS + '.DelayConfig') as delay_config:
            self.mock_delay_config = delay_config

        with mock.patch(MOCK_LOGGER) as logger:
            self.mock_logger = logger

    @mock.patch(MOCK_BUR_INPUT_VALIDATORS + '.ScriptSettings.get_customer_config_dict')
    @mock.patch(MOCK_BUR_INPUT_VALIDATORS + '.ScriptSettings')
    def test_validate_script_settings(self, mock_script_settings, mock_customer_config):
        """
        Assert if script settings were generated correctly according to config file.

        :param mock_script_settings: mock of ScriptSettings object.
        :param mock_customer_config: ScriptSettings.get_customer_config_dict method.
        """
        mock_script_settings.return_value.get_notification_handler = self.mock_notification_handler
        mock_script_settings.return_value.get_gnupg_manager = self.mock_gnupg_manager
        mock_script_settings.return_value.get_offsite_config = self.mock_offsite_config
        mock_script_settings.return_value.get_delay_config = self.mock_delay_config
        mock_customer_config.return_value = self.mock_customer_config_dict

        result = validators.validate_script_settings(CONFIG_FILE_NAME, {}, self.mock_logger)

        self.assertIsNotNone(result)
        self.assertIs(validators.SCRIPT_OBJECTS.SIZE.value - 1, len(result))

    @mock.patch(MOCK_BUR_INPUT_VALIDATORS + '.ScriptSettings')
    def test_validate_script_settings_notification_handler_error(self, mock_script_settings):
        """
        Assert if raises an Exception when trying to get NotificationHandler from ScriptSetting.

        As side effect is just a representation of BackupSettingException, the default code
        should be provided to the exception.

        :param mock_script_settings: mock of ScriptSettings object
        """
        mock_script_settings.return_value.get_notification_handler.side_effect = \
            BackupSettingsException

        with self.assertRaises(Exception):
            validators.validate_script_settings(CONFIG_FILE_NAME, {}, self.mock_logger)

    @mock.patch(MOCK_BUR_INPUT_VALIDATORS + '.ScriptSettings')
    def test_validate_script_settings_gnupg_manager_error(self, mock_script_settings):
        """
        Assert if raises an Exception when trying to get Gnupg_Manager from ScriptSetting.

        As side effect is just a representation of BackupSettingException, the default code
        should be provided to the exception.

        :param mock_script_settings: mock of ScriptSettings object
        """
        mock_script_settings.return_value.get_gnupg_manager.side_effect = \
            BackupSettingsException

        with self.assertRaises(Exception):
            validators.validate_script_settings(CONFIG_FILE_NAME, {}, self.mock_logger)

    @mock.patch(MOCK_BUR_INPUT_VALIDATORS + '.ScriptSettings')
    def test_validate_script_settings_offsite_config_error(self, mock_script_settings):
        """
        Assert if raises an Exception when trying to get OffsiteConfig from ScriptSetting.

        As side effect is just a representation of BackupSettingException, the default code
        should be provided to the exception.

        :param mock_script_settings: mock of ScriptSettings object
        """
        mock_script_settings.return_value.get_offsite_config.side_effect = \
            BackupSettingsException

        with self.assertRaises(Exception):
            validators.validate_script_settings(CONFIG_FILE_NAME, {}, self.mock_logger)

    @mock.patch(MOCK_BUR_INPUT_VALIDATORS + '.ScriptSettings')
    def test_validate_script_settings_customer_config_dic_error(self, mock_script_settings):
        """
        Assert if raises an Exception when trying to get customer_config_dict from ScriptSetting.

        As side effect is just a representation of BackupSettingException, the default code
        should be provided to the exception.

        :param mock_script_settings: mock of ScriptSettings object.
        """
        mock_script_settings.return_value.get_customer_config_dict.side_effect = \
            BackupSettingsException

        with self.assertRaises(Exception):
            validators.validate_script_settings(CONFIG_FILE_NAME, {}, self.mock_logger)


class BurInputValidatorsValidateNumberOfProcessors(unittest.TestCase):
    """Class for unit testing the validate_CLI inputs function."""

    @classmethod
    def setUp(cls):
        """Set up test constants/variables."""
        with mock.patch(MOCK_LOGGER) as logger:
            cls.mock_logger = logger

    @mock.patch(MOCK_CPU_COUNT)
    def test_validate_number_of_processors_valid_cores_valid_arg_dflt_val(self, mock_cpu_count):
        """
        Validate the default value of num_processes_to_use which is 5.

        The default value is 5, the available cores is 5.

        Thus the num_processes_to_use should pass the validation with no alteration on its value.
        """
        mock_cpu_count.return_value = 5
        num_processes_to_use = DEFAULT_NUM_PROCESSORS
        altered_num_processors = validators.validate_number_of_processors(num_processes_to_use,
                                                                          self.mock_logger)
        self.assertIs(5, altered_num_processors)

    @mock.patch(MOCK_CPU_COUNT)
    def test_validate_number_of_processors_valid_arg_bigger_than_valid_cores(self, mock_cpu_count):
        """
        Validate the num_processes_to_use when it's bigger than the available cores.

        num_processes_to_use is 7, the available cores is 5.

        Thus the num_processes_to_use should pass the validation after modifying its value to be
        equal to the available cores.
        """
        mock_cpu_count.return_value = 5
        num_processes_to_use = 7
        altered_num_processors = validators.validate_number_of_processors(num_processes_to_use,
                                                                          self.mock_logger)
        self.assertIs(5, altered_num_processors)

    @mock.patch(MOCK_CPU_COUNT)
    def test_validate_number_of_processors_valid_arg_smaller_than_valid_cores(self, mock_cpu_count):
        """
        Validates the num_processes_to_use when it's smaller than the available cores.

        num_processes_to_use is 3, the available cores is 5.

        Thus the num_processes_to_use should pass the validation with no alteration on its value.
        """
        mock_cpu_count.return_value = 5
        num_processes_to_use = 3
        altered_num_processors = validators.validate_number_of_processors(num_processes_to_use,
                                                                          self.mock_logger)
        self.assertIs(3, altered_num_processors)

    @mock.patch(MOCK_CPU_COUNT)
    def test_validate_number_of_processors_invalid_arg_smaller_than_valid_cores(self,
                                                                                mock_cpu_count):
        """
        Validate the num_processes_to_use when it's an invalid value. More specifically less than 0.

        num_processes_to_use is -1, the available cores is 5.

        Thus the num_processes_to_use should pass the validation after modifying its value to be
        equal to the available cores.
        """
        mock_cpu_count.return_value = 5
        num_processes_to_use = -1
        altered_num_processors = validators.validate_number_of_processors(num_processes_to_use,
                                                                          self.mock_logger)
        self.assertIs(DEFAULT_NUM_PROCESSORS, altered_num_processors)

    @mock.patch(MOCK_CPU_COUNT)
    def test_validate_number_of_processors_invalid_arg_type_valid_cores(self, mock_cpu_count):
        """
        Assert if raises an Exception when trying to pass a null value for num_processes_to_use.

        :param mock_cpu_count: mock the available number of cores for multiprocessing.cpu_count().
        """
        mock_cpu_count.return_value = 5
        num_processes_to_use = None

        logger_error_msg = "Invalid number of processors: None. Changed to 5."

        validators.validate_number_of_processors(num_processes_to_use, self.mock_logger)

        self.mock_logger.warning.assert_called_with(logger_error_msg)

    @mock.patch(MOCK_CPU_COUNT)
    def test_validate_number_of_processors_valid_cores_str_arg(self, mock_cpu_count):
        """
        Validates the num_processes_to_use when it's an invalid value, more specifically a string.

        num_processes_to_use is "a", the available cores is 5.

        Thus the num_processes_to_use should pass the validation after modifying its value to be
        equal to the available cores.
        """
        mock_cpu_count.return_value = 5
        num_processes_to_use = "a"
        altered_num_processors = validators.validate_number_of_processors(num_processes_to_use,
                                                                          self.mock_logger)
        self.assertIs(DEFAULT_NUM_PROCESSORS, altered_num_processors)

    @mock.patch(MOCK_CPU_COUNT)
    def test_validate_number_of_processors_low_available_cores(self, mock_cpu_count):
        """
        Validate the num_processes_to_use when there's low number of available cores.

        num_processes_to_use is 7, the available cores is 1.

        Thus the num_processes_to_use should pass the validation after modifying its value to be
        equal to the available cores.
        """
        mock_cpu_count.return_value = 1
        num_processes_to_use = 7
        altered_num_processors = validators.validate_number_of_processors(num_processes_to_use,
                                                                          self.mock_logger)
        self.assertIs(1, altered_num_processors)

    @mock.patch(MOCK_CPU_COUNT)
    def test_validate_number_of_processors_no_cores_available(self, mock_cpu_count):
        """
        Validate the num_processes_to_use when there's no available cores at all.

        num_processes_to_use is 7, the available cores is 0.

        Thus the num_processes_to_use should pass the validation after modifying its value to be
        equal to the available cores, and the OS is expected to not do any processing for BUR.
        """
        mock_cpu_count.return_value = 0
        num_processes_to_use = 7
        altered_num_processors = validators.validate_number_of_processors(num_processes_to_use,
                                                                          self.mock_logger)
        self.assertIs(0, altered_num_processors)


class BurInputValidatorsValidateOnsiteOffsiteLocations(unittest.TestCase):
    """Class for unit testing the validate_onsite_offsite_locations function."""

    def setUp(self):
        """Set up the test constants."""
        with mock.patch(MOCK_BUR_INPUT_VALIDATORS + '.validate_script_settings') as script_objects:
            self.mock_script_objects = script_objects
            self.mock_script_objects.return_value = {
                validators.SCRIPT_OBJECTS.OFFSITE_CONFIG.name: 'offsite_config',
                validators.SCRIPT_OBJECTS.CUSTOMER_CONFIG_DICT.name: 'customer_config'}

        with mock.patch(MOCK_LOGGER) as logger:
            self.mock_logger = logger

    @mock.patch(MOCK_BUR_INPUT_VALIDATORS + '.validate_onsite_backup_locations')
    @mock.patch(MOCK_BUR_INPUT_VALIDATORS + '.validate_offsite_backup_server')
    def test_validate_onsite_offsite_locations(self, mock_validate_offsite, mock_validate_onsite):
        """
        Assert if returns True when all validations inside have been done successfully.

        :param mock_validate_offsite: mocking the validate_offsite_backup_server function.
        :param mock_validate_onsite: mocking the validate_onsite_backup_locations function.
        """
        mock_validate_onsite.return_value = True
        mock_validate_offsite.return_value = True

        result = validators.validate_onsite_offsite_locations(CONFIG_FILE_NAME,
                                                              self.mock_script_objects,
                                                              self.mock_logger)
        self.assertTrue(result)


class BurInputValidatorsValidateNumberOfThreads(unittest.TestCase):
    """Class for unit testing validate_number_of_threads function."""

    def setUp(self):
        """Set up the test constants."""
        with mock.patch(MOCK_LOGGER) as logger:
            self.mock_logger = logger

    def test_validate_number_of_threads(self):
        """Assert if returns a validated number of threads."""
        mock_thread_count = 2

        result = validators.validate_number_of_threads(mock_thread_count, self.mock_logger)

        self.assertEqual(mock_thread_count, result)
        self.mock_logger.info.assert_called_with("Valid number of threads: 2.")

    def test_validate_number_of_threads_invalid_value_to_parse(self):
        """
        Assert if updates the invalid informed value to DEFAULT_NUM_THREADS value.

        This scenario has a string informed as argument instead of a number.
        """
        mock_thread_count = "value"
        expected_value = DEFAULT_NUM_THREADS

        result = validators.validate_number_of_threads(mock_thread_count, self.mock_logger)

        self.assertEqual(expected_value, result)
        self.mock_logger.warning.assert_called_with("Invalid number of threads: value. "
                                                    "Changed to: {}.".format(DEFAULT_NUM_THREADS))

    def test_validate_number_of_threads_invalid_count(self):
        """
        Assert if updates the invalid informed value to DEFAULT_NUM_THREADS value.

        This scenario has number_thread as 0.
        """
        mock_thread_count = 0
        expected_value = DEFAULT_NUM_THREADS

        result = validators.validate_number_of_threads(mock_thread_count, self.mock_logger)

        self.assertEqual(expected_value, result)
        self.mock_logger.warning.assert_called_with("Invalid number of threads: 0. "
                                                    "Changed to: {}.".format(DEFAULT_NUM_THREADS))
