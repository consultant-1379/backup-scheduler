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

# pylint: disable=protected-access

"""Module for unit testing NotificationHandler class."""

import logging
import unittest

import mock
from requests import RequestException

from backup import __version__
from backup.exceptions import ExceptionCodes
from backup.notification_handler import NotificationHandler

MOCK_LOGGER = 'backup.notification_handler.CustomLogger'
MOCK_REQUEST_POST = 'backup.notification_handler.requests.post'
MOCK_GET_CLI_ARGUMENTS = 'backup.notification_handler.NotificationHandler.' \
                         '_get_cli_arguments_into_email_body'
MOCK_UTILS_GET_CLI_ARGS = 'backup.notification_handler.get_cli_arguments'

CLI_ARGUMENTS = "BUR ran with the following arguments:<br>{}<br>" \
    .format(['--script_option', '1', '--customer_name', 'CUSTOMER_0'])

OUTPUT_LINE = "===================================================================================="

logging.disable(logging.CRITICAL)


class NotificationHandlerSendEmailTestCase(unittest.TestCase):
    """Class for testing send_mail function from backup.notification_handler.py script."""

    def setUp(self):
        """Set up for the tests."""
        self.email_to = 'mock@email'
        self.email_url = 'http://mock'
        self.from_name = 'mock'
        self.email_from = self.from_name + '@no-reply.ericsson.net'
        self.subject = 'mock_subject'
        self.message = 'mock_message'

        with mock.patch(MOCK_LOGGER) as logger:
            self.handler = NotificationHandler(self.email_to, self.email_url, logger)

    @mock.patch(MOCK_REQUEST_POST)
    def test_send_email_sending(self, mock_post):
        """Test to check the log to notify about the attempt to send the email is generated."""
        mock_post.return_value.status_code = 200

        result = self.handler.send_mail(self.subject, self.message, self.from_name)

        self.handler.logger.log_info.assert_called_with("Sending e-mail from "
                                                        "mock@no-reply.ericsson.net to "
                                                        "mock@email with subject 'mock_subject'.")
        self.handler.logger.info.assert_called_with("E-mail sent successfully to: 'mock@email'.")
        self.assertTrue(result)

    @mock.patch(MOCK_REQUEST_POST)
    def test_send_email_bad_response(self, mock_post):
        """Test to check the return value if the email was not sent due to bad response."""
        mock_post.return_value.raise_for_status.side_effect = RequestException

        with self.assertRaises(Exception) as cex:
            self.handler.send_mail(self.subject, self.message, self.from_name)

        self.assertEqual(ExceptionCodes.ErrorSendingEmail, cex.exception.code)

    @mock.patch(MOCK_REQUEST_POST)
    def test_send_email_sending_with_other_domain(self, mock_post):
        """Assert if the domain is changed from default."""
        with mock.patch(MOCK_LOGGER) as logger:
            self.handler = NotificationHandler(self.email_to, self.email_url, logger, "mock_domain")

        mock_post.return_value.status_code = 200

        result = self.handler.send_mail(self.subject, self.message, self.from_name)

        self.handler.logger.log_info.assert_called_with("Sending e-mail from mock@mock_domain to "
                                                        "mock@email with subject 'mock_subject'.")
        self.handler.logger.info.assert_called_with("E-mail sent successfully to: 'mock@email'.")
        self.assertTrue(result)


class NotificationHandlerGetLinesFromListTestCase(unittest.TestCase):
    """Class for unit testing the _get_lines_from_list private method."""

    def setUp(self):
        """Set up for the tests."""
        self.email_to = "test@email.com"
        self.email_url = "http://fake_url"

        with mock.patch(MOCK_LOGGER) as logger:
            self.handler = NotificationHandler(self.email_to, self.email_url, logger)

    def test_get_lines_from_list_one_level(self):
        """Assert if a simple list returns as a text."""
        error_list = ["error 1", "error 2", "error 3"]

        expected_message = "error 1<br>" \
                           "error 2<br>" \
                           "error 3<br>"

        result_message = self.handler._get_lines_from_list(error_list)

        self.assertEqual(expected_message, result_message)

    def test_get_lines_from_list_two_levels(self):
        """Assert if a list inside another list is added to the text."""
        error_list_level_two = ["error 1", "error 2", "error 3"]
        error_list_level_one = ["Exception 1", error_list_level_two, "Exception n"]

        expected_message = "Exception 1<br>" \
                           "error 1<br>" \
                           "error 2<br>" \
                           "error 3<br>" \
                           "Exception n<br>"

        result_message = self.handler._get_lines_from_list(error_list_level_one)

        self.assertEqual(expected_message, result_message)

    def test_get_lines_from_list_three_levels(self):
        """Assert if a list inside another list is added to the text."""
        error_list_level_three = ["Error a", "Error b"]
        error_list_level_two = ["error 1", "error 2", "error 3", error_list_level_three]
        error_list_level_one = ["Exception 1", error_list_level_two, "Exception n"]

        expected_message = "Exception 1<br>" \
                           "error 1<br>" \
                           "error 2<br>" \
                           "error 3<br>" \
                           "Error a<br>" \
                           "Error b<br>" \
                           "Exception n<br>"

        result_message = self.handler._get_lines_from_list(error_list_level_one)

        self.assertEqual(expected_message, result_message)

    def test_get_lines_from_list_no_list(self):
        """Assert that an empty text is returned when there is no elements within the list."""
        error_list = []

        expected_message = ""

        result_message = self.handler._get_lines_from_list(error_list)

        self.assertEqual(expected_message, result_message)

    def test_get_lines_from_list_no_list_as_none(self):
        """Assert that an empty text is returned when a None object is informed as argument."""
        error_list = None

        expected_message = ""

        result_message = self.handler._get_lines_from_list(error_list)

        self.assertEqual(expected_message, result_message)

    def test_get_lines_from_list_with_list_inside_string(self):
        """
        Assert that a text is returned when inside a string there is a parsed list.

        In some cases, error messages will have a list of errors already parsed as string inside
        a ([]) delimiter, so this string should go back as list type and be added to the e-mail
        body accordingly.
        """
        error_message = ["Error Code 30. Something went wrong. ([\"Error parsing value.\", "
                         "\"Error while reading file.\", \"Cannot create file.\")]"]

        expected_message = "Error Code 30. Something went wrong.<br>Error parsing value.<br>" \
                           "Error while reading file.<br>Cannot create file.<br>"

        result_message = self.handler._get_lines_from_list(error_message)

        self.assertEqual(expected_message, result_message)

    def test_get_lines_from_list_with_list_inside_string_without_end_delimiter(self):
        """
        Assert that a text is returned when inside a string there is a parsed list.

        In some cases, error messages will have a list of errors already parsed as string inside
        a ([ start delimiter only, so this string should go back as list type and be added to the
        e-mail body accordingly.
        """
        error_message = ["Error Code 30. Something went wrong. ([\"Error parsing value.\", "
                         "\"Error while reading file.\", \"Cannot create file.\""]

        expected_message = "Error Code 30. Something went wrong.<br>Error parsing value.<br>" \
                           "Error while reading file.<br>Cannot create file.<br>"

        result_message = self.handler._get_lines_from_list(error_message)

        self.assertEqual(expected_message, result_message)


class NotificationHandlerPrepareEmailBodyTestCase(unittest.TestCase):
    """Class for unit testing the prepare_email_body method."""

    def setUp(self):
        """Set up for the tests."""
        self.email_to = "test@email.com"
        self.email_url = "http://fake_url"

        with mock.patch(MOCK_LOGGER) as logger:
            self.handler = NotificationHandler(self.email_to, self.email_url, logger)

    @mock.patch(MOCK_GET_CLI_ARGUMENTS)
    def test_prepare_email_body_error_email(self, mock_cli_args):
        """
        Assert if the formatted e-mail has the list errors and the message with code error.

        :param mock_cli_args: mocking the message with the CLI arguments.
        """
        mock_cli_args.return_value = CLI_ARGUMENTS
        error_list = ["error 1", "error 2", "error 3"]

        expected_message = "BUR ran with the following arguments:<br>" \
                           "['--script_option', '1', '--customer_name', 'CUSTOMER_0']<br>" \
                           "The following errors happened during this operation:<br>" \
                           "error 1<br>" \
                           "error 2<br>" \
                           "error 3<br>" \
                           "System stopped with error code: 1." \
                           "<br><br>BUR Version: " + __version__

        result = self.handler._prepare_email_body(NotificationHandler.ERROR, error_list, 1)

        self.assertEqual(expected_message, result)

    @mock.patch(MOCK_GET_CLI_ARGUMENTS)
    def test_prepare_email_body_success_email(self, mock_cli_args):
        """
        Assert if the formatted e-mail has the list errors and the message with code error.

        :param mock_cli_args: mocking the message with the CLI arguments.
        """
        mock_cli_args.return_value = CLI_ARGUMENTS
        message_list = ["Upload finished.", "Elapsed time: 2"]

        expected_message = "BUR ran with the following arguments:<br>" \
                           "['--script_option', '1', '--customer_name', 'CUSTOMER_0']<br>" \
                           "The following operations were successfully finished:<br>" \
                           "Upload finished.<br>" \
                           "Elapsed time: 2<br>" \
                           "<br><br>BUR Version: " + __version__

        result = self.handler._prepare_email_body(NotificationHandler.SUCCESS, message_list)

        self.assertEqual(expected_message, result)

    @mock.patch(MOCK_GET_CLI_ARGUMENTS)
    def test_prepare_email_body_error_list_none(self, mock_cli_args):
        """
        Assert if the formatted e-mail has no list errors and the message with code error.

        :param mock_cli_args: mocking the message with the CLI arguments.
        """
        mock_cli_args.return_value = CLI_ARGUMENTS
        error_list = None
        expected_message = "BUR ran with the following arguments:<br>" \
                           "['--script_option', '1', '--customer_name', 'CUSTOMER_0']<br>" \
                           "System stopped with error code: 1." \
                           "<br><br>BUR Version: " + __version__

        result = self.handler._prepare_email_body(NotificationHandler.ERROR, error_list, 1)

        self.assertEqual(expected_message, result)

    @mock.patch(MOCK_GET_CLI_ARGUMENTS)
    def test_prepare_email_body_error_list_none_error_code_none(self, mock_cli_args):
        """
        Assert if the formatted e-mail has no list errors and no message with code error.

        :param mock_cli_args: mocking the message with the CLI arguments.
        """
        mock_cli_args.return_value = CLI_ARGUMENTS
        error_list = None
        expected_message = "BUR ran with the following arguments:<br>" \
                           "['--script_option', '1', '--customer_name', 'CUSTOMER_0']<br>" \
                           "<br><br>BUR Version: " + __version__

        result = self.handler._prepare_email_body(NotificationHandler.ERROR, error_list)

        self.assertEqual(expected_message, result)

    @mock.patch(MOCK_GET_CLI_ARGUMENTS)
    def test_prepare_email_body_message_list_none(self, mock_cli_args):
        """
        Assert if the formatted e-mail has just the contents of CLI arguments when list is None.

        :param mock_cli_args: mocking the message with the CLI arguments.
        """
        mock_cli_args.return_value = CLI_ARGUMENTS
        message_list = None
        expected_message = "BUR ran with the following arguments:<br>" \
                           "['--script_option', '1', '--customer_name', 'CUSTOMER_0']<br>" \
                           "<br><br>BUR Version: " + __version__

        result = self.handler._prepare_email_body(NotificationHandler.SUCCESS,
                                                  message_list, 1)

        self.assertEqual(expected_message, result)


class NotificationHandlerGetCliArgumentsIntoEmailBodyTestCase(unittest.TestCase):
    """Class for unit testing _get_cli_arguments_into_email_body method."""

    def setUp(self):
        """Set up for the tests."""
        self.email_to = "test@email.com"
        self.email_url = "http://fake_url"

        with mock.patch(MOCK_LOGGER) as logger:
            self.handler = NotificationHandler(self.email_to, self.email_url, logger)

    @mock.patch(MOCK_UTILS_GET_CLI_ARGS)
    def test_get_cli_arguments_into_email_body(self, mock_cli_args):
        """
        Assert if the message returned has the arguments from the get_cli_arguments function.

        :param mock_cli_args: mocking the utils.get_cli_arguments function.
        """
        mock_cli_args.return_value = ['--script_option', '1', '--customer_name', 'CUSTOMER_0']
        expected_result = "BUR ran with the following arguments:<br>" \
                          "['--script_option', '1', '--customer_name', 'CUSTOMER_0']<br><br>"

        result = self.handler._get_cli_arguments_into_email_body()

        self.assertEqual(expected_result, result)

    @mock.patch(MOCK_UTILS_GET_CLI_ARGS)
    def test_get_cli_arguments_into_email_body_empty_list(self, mock_cli_args):
        """
        Assert if the result informs BUR had no arguments get_cli_arguments returns empty list.

        :param mock_cli_args: mocking the utils.get_cli_arguments function.
        """
        mock_cli_args.return_value = []
        expected_result = "BUR ran with no arguments.<br>"

        result = self.handler._get_cli_arguments_into_email_body()

        self.assertEqual(expected_result, result)

    @mock.patch(MOCK_UTILS_GET_CLI_ARGS)
    def test_get_cli_arguments_into_email_body_none_list(self, mock_cli_args):
        """
        Assert if the result informs BUR had no arguments get_cli_arguments returns None.

        :param mock_cli_args: mocking the utils.get_cli_arguments function.
        """
        mock_cli_args.return_value = None
        expected_result = "BUR ran with no arguments.<br>"

        result = self.handler._get_cli_arguments_into_email_body()

        self.assertEqual(expected_result, result)
