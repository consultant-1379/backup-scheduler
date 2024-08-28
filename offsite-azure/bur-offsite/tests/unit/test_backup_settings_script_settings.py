##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=protected-access

"""Module for unit testing the class ScriptSettings from backup_settings.py script."""

from ConfigParser import ConfigParser, MissingSectionHeaderError, ParsingError
from StringIO import StringIO
import unittest

import mock

from backup.backup_settings import ScriptSettings
from backup.exceptions import ExceptionCodes

MOCK_OS_ACCESS = 'backup.backup_settings.os.access'
MOCK_CONFIG_PARSER = 'backup.backup_settings.ConfigParser.readfp'
MOCK_LOGGER = 'backup.backup_settings.CustomLogger'
MOCK_OPEN = 'backup.backup_settings.open'
MOCK_SCRIPT_SETTINGS = 'backup.backup_settings.ScriptSettings'

CONFIG_FILE_NAME = 'fake_config_file'


class ScriptSettingsGetConfigDetails(unittest.TestCase):
    """Class for unit testing the get_config_details from ScriptSetting class."""

    def setUp(self):
        """Set up the test variables."""
        with mock.patch(MOCK_LOGGER) as logger:
            with mock.patch(MOCK_SCRIPT_SETTINGS + '._get_config_details') as mock_get_config:
                mock_get_config.return_value = ConfigParser()
                self.script_settings = ScriptSettings(CONFIG_FILE_NAME, logger)
                self.script_settings.config_file_path = CONFIG_FILE_NAME

    @mock.patch(MOCK_CONFIG_PARSER)
    @mock.patch(MOCK_OPEN)
    @mock.patch(MOCK_OS_ACCESS)
    def test_get_config_details(self, mock_os_access, mock_open, mock_parser):
        """
        Assert if the methods returns an object when the file is valid and has valid information.

        :param mock_os_access: mocking if the file exists.
        :param mock_open: mocking opening a file.
        :param mock_parser: mocking reading and creating a configuration object.
        """
        mock_os_access.return_value = True
        mock_parser.return_value = None
        mock_open.return_value = StringIO(CONFIG_FILE_NAME)

        result = self.script_settings._get_config_details()
        self.assertIsNotNone(result)

    def test_get_config_file_cant_access_file(self):
        """Assert if raises an exception when the file isn't valid or readable."""
        with self.assertRaises(Exception) as cex:
            self.script_settings._get_config_details()

        self.assertEqual(ExceptionCodes.ConfigurationFileReadError, cex.exception.code)

    @mock.patch(MOCK_OS_ACCESS)
    def test_get_config_details_basic_exception(self, mock_os_access):
        """
        Assert if raises an exception when cannot read the file.

        :param mock_os_access: mocking if the file exists.
        """
        mock_os_access.return_value = True

        with self.assertRaises(Exception) as cex:
            self.script_settings._get_config_details()

        self.assertEqual(ExceptionCodes.ConfigurationFileReadError, cex.exception.code)

    @mock.patch(MOCK_OPEN)
    @mock.patch(MOCK_OS_ACCESS)
    def test_get_config_details_io_error_exception(self, mock_os_access, mock_open):
        """
        Assert if raises an exception when cannot read the file.

        :param mock_os_access: mocking if the file exists.
        """
        mock_os_access.return_value = True
        mock_open.side_effect = IOError

        with self.assertRaises(Exception) as cex:
            self.script_settings._get_config_details()

        self.assertEqual(ExceptionCodes.ConfigurationFileReadError, cex.exception.code)

    @mock.patch(MOCK_CONFIG_PARSER)
    @mock.patch(MOCK_OPEN)
    @mock.patch(MOCK_OS_ACCESS)
    def test_get_config_details_parser_exception(self, mock_os_access, mock_open, mock_parser):
        """
        Assert if raises an exception and said exception is caught in the correct except.

        :param mock_os_access: mocking if the file exists.
        :param mock_open: mocking opening a file.
        :param mock_parser: mocking reading and creating a configuration object.
        """
        mock_os_access.return_value = True
        mock_open.return_value = StringIO(CONFIG_FILE_NAME)
        mock_parser.side_effect = AttributeError("Test exception")

        with self.assertRaises(Exception) as cex:
            self.script_settings._get_config_details()

        self.assertEqual(ExceptionCodes.ConfigurationFileParsingError, cex.exception.code)

    @mock.patch(MOCK_CONFIG_PARSER)
    @mock.patch(MOCK_OPEN)
    @mock.patch(MOCK_OS_ACCESS)
    def test_get_config_details_parsing_error_exception(self, mock_open, mock_os_access,
                                                        mock_parser):
        """
        Assert if raises an exception and said exception is caught in the correct except.

        :param mock_os_access: mocking if the file exists.
        :param mock_open: mocking opening a file.
        :param mock_parser: mocking reading and creating a configuration object.
        """
        mock_os_access.return_value = True
        mock_open.return_value = StringIO(CONFIG_FILE_NAME)
        mock_parser.side_effect = ParsingError(CONFIG_FILE_NAME)

        with self.assertRaises(Exception) as cex:
            self.script_settings._get_config_details()

        self.assertEqual(ExceptionCodes.ConfigurationFileParsingError, cex.exception.code)

    @mock.patch(MOCK_CONFIG_PARSER)
    @mock.patch(MOCK_OPEN)
    @mock.patch(MOCK_OS_ACCESS)
    def test_get_config_details_missing_section_exception(self, mock_open, mock_os_access,
                                                          mock_parser):
        """
        Assert if raises an exception and said exception is caught in the correct except.

        :param mock_os_access: mocking if the file exists.
        :param mock_open: mocking opening a file.
        :param mock_parser: mocking reading and creating a configuration object.
        """
        mock_os_access.return_value = True
        mock_open.return_value = StringIO(CONFIG_FILE_NAME)
        mock_parser.side_effect = MissingSectionHeaderError(CONFIG_FILE_NAME, 1, 1)

        with self.assertRaises(Exception) as cex:
            self.script_settings._get_config_details()

        self.assertEqual(ExceptionCodes.ConfigurationFileParsingError, cex.exception.code)
