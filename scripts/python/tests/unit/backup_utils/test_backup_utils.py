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

# For the sake of without arguments tests
# pylint: disable=E1120

"""
This module contains the classes that do unit tests for the functions and
classes in backup_utils.py script
"""

import os
import unittest
import ConfigParser
import json
import mock
import requests
import scripts.python.backup_scheduler.backup_utils as utils

DIR = os.path.dirname(os.path.realpath(__file__))

CUSTOMER_NAME = 'fake_customer'

HALF_CONF_FILE = DIR + '/test_half_logging_config.ini'
FULL_CONF_FILE = DIR + '/test_full_logging_config.ini'
NO_LOGGING_SECTION_CONF_FILE = DIR + '/test_no_logging_section_config.ini'
CFG_CLASS_CONFIG_FILE = DIR + '/test_cfg_class_config.ini'

FAKE_URL = 'http://fakeyfakeyfakeyfakeyfakey'
REQUEST_DATA = 'fake request data'
JSON_DUMP = {'json_test': 'json_content'}

MOCK_PACKAGE = 'scripts.python.backup_scheduler.backup_utils.'
MOCK_SYS = MOCK_PACKAGE + 'sys'
MOCK_LOGGER = MOCK_PACKAGE + 'logging.getLogger'
MOCK_LOG = MOCK_PACKAGE + 'LOG'
MOCK_REQUESTS = MOCK_PACKAGE + 'requests'

MOCK_SLEEP = MOCK_PACKAGE + 'time.sleep'
MOCK_CMD = MOCK_PACKAGE + 'cmd'
MOCK_JSON = MOCK_PACKAGE + 'json'

KEYSTONE = DIR + '/test_keystone.rc'
PEM_FILE = DIR + '/test_private_key.pem'

STACK_LIST = """staging01_elasticsearch_bbc24adb-86e3-4b04-bdef-efae0f1a7b68
staging01_VNFLCM
staging01_cu_key
VNF_LAF_FOR_VMME
staging01_network_internal_stack
"""
# pylint: disable=protected-access


class ToSecondsFromHoursTestCase(unittest.TestCase):
    """
    This is a successful scenario when hours are passed as argument
    """

    def test_with_hours(self):
        """
        Test changing 1h hour to 3600 seconds
        """
        expected_result = 3600
        self.assertEqual(expected_result, utils.to_seconds('1h'))


class ToSecondsFromMinutesTestCase(unittest.TestCase):
    """
    This is a successful scenario when minutes are passed as argument
    """

    def test_with_minutes(self):
        """
        Test changing 1 minute to 60 seconds
        """
        expected_result = 60
        self.assertEqual(expected_result, utils.to_seconds('1m'))


class ToSecondsRaisesValueErrorTestCase(unittest.TestCase):
    """
    This is a failure scenario when hours and minutes are passed as argument
    Only one kind of unit is supported. Assert is to validate if the correct
    exception is raised
    """
    def test_invalid_format(self):
        """
        Raise exception test to validate the input
        """
        with self.assertRaises(ValueError):
            utils.to_seconds('2h30m')


class ToSecondsRaisesKeyErrorTestCase(unittest.TestCase):
    """
    This is a failure scenario when an argument is passed with an invalid unit.
    Only h (hours), m (minutes) and s (seconds) are supported as key values.
    Assert is to validate if the correct exception is raised
    """
    def setUp(self):
        """
        Set up for the test
        """
        self.error_message = "Unit invalid (must be 's', 'h' or 'm')"

    def test_invalid_unit(self):
        """
        Raise exception test to validate the unit passed as input
        """
        with self.assertRaises(KeyError) as err:
            utils.to_seconds('2v')
        self.assertEqual(self.error_message, err.exception.message)


class ToSecondsWithNoUnitTestCase(unittest.TestCase):
    """
    This is a failure scenario when an argument is passed without an unit.
    Assert is to validate if the correct exception is raised
    """
    def setUp(self):
        """
        Set up for the test
        """
        self.error_message = 'The value informed is in the wrong format'

    def test_invalid_argument_no_unit(self):
        """
        Raise exception test to validate the unit not passed within the input
        """
        with self.assertRaises(ValueError) as err:
            utils.to_seconds('4')
        self.assertEqual(self.error_message, err.exception.message)


class ErrExitCalledTestCase(unittest.TestCase):
    """
    This is successful scenario when just the 'msg' argument is passed
    """

    def setUp(self):
        """
        Set up arguments for the test
        """
        self.message = 'fake message'

    @mock.patch(MOCK_SYS)
    def test_code_and_msg(self, mock_sys):
        """
        Test with just the 'msg' param, using the default value for the
        function call
        :param mock_sys: mocking the sys package
        """
        utils.err_exit(self.message)
        mock_sys.exit.assert_called_with(1)


class ErrExitCalledWithCodeZeroTestCase(unittest.TestCase):
    """
    This is a successful scenario when the 'msg' argument is passed and a
    'code' error
    argument is passed as 0
    """

    def setUp(self):
        """
        Set up the arguments for the test
        """
        self.message = 'fake message'
        self.code = 0

    @mock.patch(MOCK_SYS)
    def test_called_with_code_zero(self, mock_sys):
        """
        Test with the 'msg' param and a 'code' error param
        :param mock_sys: mocking the sys package
        """
        utils.err_exit(self.message, self.code)
        mock_sys.exit.assert_called_with(self.code)


class ErrExitCalledWithNoneTestCase(unittest.TestCase):
    """
    This is a successful scenario when None is passed as arguments for 'msg'
    and 'code' error argument
    """

    def setUp(self):
        """
        Set up the arguments for the test
        """
        self.message = None
        self.code = None
        self.log = None

    @mock.patch(MOCK_SYS)
    def test_called_with_none(self, mock_sys):
        """
        Test with None as 'msg' and 'code' error param
        :param mock_sys: mocking the sys package
        """
        utils.err_exit(self.message, self.code, self.log)
        mock_sys.exit.assert_called_with(None)


class ErrExitWithLogObjectTestCase(unittest.TestCase):
    """
    This is a successful scenario when the 'log' object is passed as an
    argument and the error 'msg' passed as argument should be logged
    during script execution
    """
    def setUp(self):
        """Set up the 'msg' argument"""
        self.message = 'fake msg'

    @mock.patch(MOCK_SYS)
    @mock.patch(MOCK_LOGGER)
    def test_with_log_object(self, mock_logging, mock_sys):
        """
        Test for checking if the log method is called within the function
        :param mock_logging: mocking the log package
        :param mock_sys: mocking the sys package
        """
        utils.err_exit(self.message, log=mock_logging)
        mock_logging.error.assert_called_with(self.message)
        mock_sys.exit.assert_called_with(1)


class ErrExitInvalidArgumentsTestCase(unittest.TestCase):
    """
    This is a failure scenario when nothing is passed as argument and at least
     the 'msg' argument should be informed.
    Assert is to validate if the correct exception is raised
    """

    def test_without_any_argument(self):
        """
        Test for checking if the obligated arguments are passed
        """
        with self.assertRaises(TypeError):
            utils.err_exit()


class GetLoggerWithConfigurationFileTestCase(unittest.TestCase):
    """
    This is a successful scenario when all the configuration fields are
    correctly filled into the .ini file, so a configuration object is
    functional to the get_logger function
    """

    def setUp(self):
        """
        Set up configuration object with a configuration .ini file with the
        correct fields filled
        """
        self.cfg = utils.Cfg()
        self.cfg.read_config(FULL_CONF_FILE)

    def test_with_config_object(self):
        """
        Test with a fully useful configuration object and customer name
        """
        self.assertIsNotNone(utils.get_logger(self.cfg, CUSTOMER_NAME))


class GetLoggerWithoutCfgObjectTestCase(unittest.TestCase):
    """
    This is a failure scenario when the configuration object and customer
    aren't provided.
    Assert is to validate if the correct exception is raised
    """

    def test_without_config_object(self):
        """
        Raise exception test when a configuration object isn't provided
        """
        with self.assertRaises(TypeError):
            utils.get_logger()


class GetLoggerWithNoneArgumentsTestCase(unittest.TestCase):
    """
    This is a failure scenario when None is provided as configuration object
    and customer name arguments.
    Assert is to validate if the correct exception is raised
    """

    def test_with_none_arguments(self):
        """
        Raise exception test when None is provided as both arguments
        """
        with self.assertRaises(AttributeError):
            utils.get_logger(None, None)


class GetLoggerWithIncompleteLoggingSectionTestCase(unittest.TestCase):
    """
    This is a failure scenario when a configuration object has the 'logging'
    section, but 'logging' section doesn't have all the options (fields) used
    to set up the log.
    Assert is to validate if the correct exception is raised
    """

    def setUp(self):
        """
        Set up configuration object with a configuration .ini file with the
        correct section for logging, but without all the options filled
        """
        self.cfg = utils.Cfg()
        self.cfg.read_config(HALF_CONF_FILE)

    def test_incomplete_logging_section(self):
        """
        Raise exception test when a field for setting up the log isn't found
        into the configuration object
        """
        with self.assertRaises(ConfigParser.NoOptionError):
            utils.get_logger(self.cfg, CUSTOMER_NAME)


class GetLoggerWithoutLoggingSectionTestCase(unittest.TestCase):
    """
    This is a failure scenario when the configuration object doesn't have the
    logging section set up into it.
    Assert is to validate if the correct exception is raised
    """

    def setUp(self):
        """
        Set up configuration object with a configuration .ini file without the
        logging section
        """
        self.cfg = utils.Cfg()
        self.cfg.read_config(NO_LOGGING_SECTION_CONF_FILE)

    def test_section_non_existent(self):
        """
        Raise exception test with no logging section
        """
        with self.assertRaises(ConfigParser.NoSectionError):
            utils.get_logger(self.cfg, CUSTOMER_NAME)


class PostHttpTestCase(unittest.TestCase):
    """
    Successful scenario of getting a response from 'post_http' function
    """

    @mock.patch(MOCK_REQUESTS)
    @mock.patch(MOCK_LOGGER)
    def test_simple_post(self, mock_logging, mock_requests):
        """
        Test a simple post http request
        :param mock_logging: mocking the log object
        :param mock_requests: mocking the requests lib
        :return:
        """
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'}
        result = utils.post_http(FAKE_URL, REQUEST_DATA, mock_logging)
        mock_requests.post.assert_called_with(FAKE_URL,
                                              data=REQUEST_DATA,
                                              headers=headers)
        self.assertIsNotNone(result)


class PostHttpWithInfoLogTestCase(unittest.TestCase):
    """
    To validate if the log.info is being called within the 'post_http'
    function
    """

    @mock.patch(MOCK_LOGGER)
    def test_check_logging(self, mock_logging):
        """
        Test to assert log.info being called
        :param mock_logging: mocking the log object
        """
        result = utils.post_http(FAKE_URL, REQUEST_DATA, mock_logging)
        mock_logging.info.assert_called_once()
        self.assertIsNotNone(result)


class PostHttpValidateReturnTestCase(unittest.TestCase):
    """
    This is a scenario to validate the return of the call
    """

    @mock.patch(MOCK_LOGGER)
    def test_simple_post_return(self, mock_logging):
        """
        Test if the result from calling post_http is not none
        :param mock_logging: mocking the log object
        """
        result = utils.post_http(FAKE_URL, REQUEST_DATA, mock_logging)
        self.assertIsNotNone(result)


class PostHttpLogErrorTestCase(unittest.TestCase):
    """
    This is a scenario when the request has an error that needs to be logged
    into the system log
    """

    @mock.patch(MOCK_LOGGER)
    def test_error_logging(self, mock_logging):
        """
        Test to validate if log.error was called
        :param mock_logging: mocking the log object
        """
        result = utils.post_http(FAKE_URL, REQUEST_DATA, mock_logging)
        mock_logging.error.assert_called_once()
        self.assertIsNotNone(result)


class PostHttpRaisesTypeErrorTestCase(unittest.TestCase):
    """
    This is a scenario when the basic arguments aren't passed to the function
    Asserts if the correct exception was raised
    """

    def test_without_arguments(self):
        """
        Raise exception test when arguments aren't provided
        """
        with self.assertRaises(TypeError):
            utils.post_http()


class PostHttpRaisesAttributeErrorTestCase(unittest.TestCase):
    """
    This is a scenario when the arguments are passed as None
    """

    def test_arguments_with_none(self):
        """
        Raise exception test when the arguments are none
        """
        with self.assertRaises(AttributeError):
            utils.post_http(None, None, None)


class PostHttpJsonResultTestCase(unittest.TestCase):
    """
    This is a scenario for checking if a valid json result is returned when a
    post request is successfully finished
    """

    @mock.patch(MOCK_LOGGER)
    @mock.patch(MOCK_REQUESTS + '.post')
    def test_simple_post_check_response(self, mock_json, mock_logging):
        """
        Test to validate the json return
        :param mock_json: mocking the json result from requests.post
        :param mock_logging: mocking the log object
        """
        json_result = json.dumps(JSON_DUMP)
        mock_json.return_value.json.return_value = json_result
        result = utils.post_http(FAKE_URL, REQUEST_DATA, mock_logging)
        self.assertEqual(result, json_result)


class GetHttpRequestTestCase(unittest.TestCase):
    """
    To validate if the get method from requests is being called
    """

    @mock.patch(MOCK_LOGGER)
    @mock.patch(MOCK_REQUESTS)
    def test_get_called(self, mock_requests, mock_logging):
        """
        Test get method is called with the informed arguments
        :param mock_requests: mocking the requests lib
        :param mock_logging: mocking the log object
        """
        result = utils.get_http_request(FAKE_URL, mock_logging)
        mock_requests.get.assert_called_with(FAKE_URL)
        self.assertIsNotNone(result)


class GetHttpRequestLoggingTestCase(unittest.TestCase):
    """
    This is a scenario to validate if the log object is being called to inform
    that a get request was initiated
    """

    @mock.patch(MOCK_LOGGER)
    def test_check_logging(self, mock_logging):
        """
        Test if the log.info was called
        :param mock_logging: mocking the log object
        """
        result = utils.get_http_request(FAKE_URL, mock_logging)
        mock_logging.info.assert_called_with('GET request: %s', FAKE_URL)
        self.assertIsNotNone(result)


class GetHttpRequestReturnTestCase(unittest.TestCase):
    """
    To validate if the request was fully processed and returned something
    """

    @mock.patch(MOCK_LOGGER)
    def test_request_return(self, mock_logging):
        """
        Test if the result is being returned
        :param mock_logging: mocking the log object
        """
        result = utils.get_http_request(FAKE_URL, mock_logging)
        self.assertIsNotNone(result)


class GetHttpRequestArgumentsTestCase(unittest.TestCase):
    """
    This is a failure scenario when none of the arguments are informed.
    Asserts if the correct exception was raised
    """

    def test_check_arguments(self):
        """
        Raise exception test to validate the arguments
        :return:
        """
        with self.assertRaises(TypeError):
            utils.get_http_request()


class GetHttpRequestArgumentsNoneTestCase(unittest.TestCase):
    """
    This is a failure scenario when the arguments are informed as None type.
    Asserts if the correct exception was raised.
    """

    def test_arguments_with_none(self):
        """
        Raise exception test when the arguments are 'None'
        """
        with self.assertRaises(AttributeError):
            utils.get_http_request(None, None)


class GetHttpRequestJsonResultTestCase(unittest.TestCase):
    """
    This is a successful scenario when the function should return a valid json
    """

    @mock.patch(MOCK_LOGGER)
    @mock.patch(MOCK_REQUESTS + '.get')
    def test_check_response(self, mock_json, mock_logging):
        """
        Test to mock a json result after a successful request
        :param mock_json: mocking the result from the 'requests.get' method
        :param mock_logging: mocking the log object
        """
        json_result = json.dumps(JSON_DUMP)
        mock_json.return_value.json.return_value = json_result
        result = utils.get_http_request(FAKE_URL, mock_logging)
        self.assertEqual(result, json_result)


class CommandLineTestCase(unittest.TestCase):
    """
    Class for testing the cmd function from backup_utils.py script
    """

    def setUp(self):
        """
        Set up the valid and invalid commands being used by the tests
        """
        self.command = 'echo Hello World'
        self.invalid_command = 'cho Hello World'

    def test_simple_command(self):
        """
        Test a valid command to ensure it was performed and had a valid
        result
        """
        result = utils.cmd(self.command, True)
        self.assertEquals(result[1], b"Hello World\n")

    @mock.patch(MOCK_LOG)
    def test_check_logging(self, mock_logging):
        """
        Test with a valid command to check if the log.info method was called
        :param mock_logging: mocking the log object
        """
        result = utils.cmd(self.command, True)
        mock_logging.info.assert_called()
        self.assertNotEqual(result, 1)

    @mock.patch(MOCK_LOG)
    def test_invalid_command(self, mock_logging):
        """
        Test with an invalid command to check if the correct log is called and
        if the stderr from return is not empty
        :param mock_logging: mocking the log object
        """
        result = utils.cmd(self.invalid_command, True)
        mock_logging.info.assert_called_with('STDERR: %s',
                                             '/bin/sh: 1: cho: not found\n')
        self.assertFalse(len(result[2]) == 0)

    @mock.patch(MOCK_LOG)
    def test_false_logging(self, mock_logging):
        """
        Test to check if log is not being called when is_logging is False
        Assert validates the LAST call of the log.info method, so the last
        call should be informing the return code
        :param mock_logging: mocking the log object
        """
        result = utils.cmd(self.command, False)
        mock_logging.info.assert_called_with("Return code: " + str(result[0]))
        self.assertNotEqual(result, 1)

    @mock.patch(MOCK_LOG)
    def test_invalid_command_false_log(self, mock_logging):
        """
        Test to check if log is not being called when is_logging is False even
        with an invalid command.
        Assert validates the LAST call of the log.info method, so the last call
        should be informing the return code
        :param mock_logging: mocking the log object
        """
        result = utils.cmd(self.invalid_command, False)
        mock_logging.info.assert_called_with("Return code: " + str(result[0]))
        self.assertNotEqual(result, 1)

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_PACKAGE + 'subprocess.Popen.communicate')
    def test_raises_exception(self, mock_cmd, mock_logging):
        """
        Raise exception test to validate if the Exception is being catch and
        dealt properly.
        Asserts if the log.error method is called when an exception is raised
        :param mock_cmd: mocking the Popen lib
        :param mock_logging: mocking the log object
        :return:
        """
        mock_cmd.side_effect = OSError
        result = utils.cmd(self.command, False)
        mock_logging.error.assert_called_with("Failed to run echo Hello World")
        self.assertEqual(result, 1)


class SendEmailTestCase(unittest.TestCase):
    """
    This is a successful scenario for the 'send_mail' function
    """

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_REQUESTS + '.post')
    def test_send_email(self, mock_email, mock_logging):
        """
        Test if when the email is sent, the action with the receiver is logged
        into the system log
        :param mock_email: mocking the urlopen method
        :param mock_logging: mocking the log object
        """
        mock_response = mock_email.return_value
        mock_response.raise_for_status.return_value = None

        result = utils.send_mail('service_email',
                                 'sender@mail',
                                 'receiver@mail',
                                 'subject',
                                 'message')
        mock_logging.info.assert_called_with("Sent e-mail to: '%s'.",
                                             'receiver@mail')
        self.assertTrue(result)


class SendEmailFailTestCase(unittest.TestCase):
    """
    This is a failure scenario for the 'send_mail' function
    """

    @mock.patch(MOCK_LOG)
    @mock.patch(MOCK_REQUESTS + '.post')
    def test_send_email_fail(self, mock_email, mock_logging):
        """
        Test if when the send_email fails, the error is logged into the system
        log with the error status code and error return value
        :param mock_email: mocking the urlopen method
        :param mock_logging: mocking the log object
        """
        mock_response = mock_email.return_value
        mock_response.raise_for_status.side_effect = \
            requests.exceptions.RequestException

        result = utils.send_mail('service_email',
                                 'sender@mail',
                                 'receiver@mail',
                                 'subject',
                                 'message')

        mock_logging.error.assert_called_with("Failed to send e-mail to: '%s'",
                                              'receiver@mail')
        self.assertFalse(result)


class SendEmailRaisesTypeErrorExceptionTestCase(unittest.TestCase):
    """
    This is a scenario when no argument is passed
    Asserts if the correct exception was raised
    """

    def test_without_arguments(self):
        """
        Raise exception test without obligated arguments
        :return:
        """
        with self.assertRaises(TypeError):
            utils.send_mail()


class TestGetKeystoneEnv(unittest.TestCase):
    """
    Class to test function get_keystone_env
    """

    def test_get_keystone_env_ok(self):
        """
        Test keystone file is read ok.
        """

        my_env = utils.get_keystone_env(KEYSTONE)

        # File has 10 valid lines out of 12
        self.assertEqual(len(my_env), 10)
        self.assertEqual(my_env['OS_USERNAME'], 'edders')

    def test_get_keystone_env_no_file(self):
        """
        Test empty dictionary is returned if file not found.
        """
        fake_file = '/blah/blah/file_does_not_exist'
        my_env = utils.get_keystone_env(fake_file)
        self.assertEqual(len(my_env), 0)


class TestPing(unittest.TestCase):
    """
    Class to test function ping
    """

    @mock.patch(MOCK_SLEEP)
    @mock.patch(MOCK_CMD)
    def test_ping_args(self, mock_cmd, mock_sleep):
        """
        Test ping arguments are used correctly
        """
        count = 5
        duration = 20
        host = 'machine1'
        mock_cmd.return_value = (1, "", "")

        result = utils.ping(host, count, duration)

        self.assertFalse(result)
        self.assertEqual(count, mock_cmd._mock_call_count)
        mock_sleep.assert_called_with(duration)
        mock_cmd.assert_called_with('ping -c 1 ' + host, is_logging=False)

    @mock.patch(MOCK_SLEEP)
    @mock.patch(MOCK_CMD)
    def test_ping_ok_on_retry(self, mock_cmd, mock_sleep):
        """
        Test ping returns True when ping succeeds after
        several faiures
        """
        count = 5
        duration = 20
        host = 'machine1'
        ping_fail = (1, "", "")
        ping_ok = (0, "", "")
        pings = [ping_fail, ping_fail, ping_ok]

        mock_cmd.side_effect = pings

        result = utils.ping(host, count, duration)
        self.assertTrue(result)
        self.assertEqual(len(pings), mock_cmd._mock_call_count)
        mock_sleep.assert_called_with(duration)


class TestCheckPrivateKey(unittest.TestCase):
    """
    Class to test function check_private_key
    """

    @mock.patch(MOCK_CMD)
    def test_check_key_ok(self, mock_cmd):
        """
        key is present and ssh succeeds, function returns True
        """
        user = 'stephen'
        host = '10.2.10.10'

        opts = '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no '
        opts += '-o BatchMode=Yes'
        ssh_cmd = 'ssh -i %s %s %s@%s hostname' % (PEM_FILE, opts, user, host)

        mock_cmd.return_value = (0, "", "")
        result = utils.check_private_key(user, PEM_FILE, host)
        self.assertTrue(result)
        mock_cmd.assert_called_with(ssh_cmd, is_logging=False)

    @mock.patch(MOCK_CMD)
    def test_check_key_file_not_found(self, mock_cmd):
        """
        key is present and ssh succeeds, function returns True
        """
        user = 'stephen'
        host = '10.2.10.10'

        result = utils.check_private_key(user, '/no/such/file/here', host)
        self.assertFalse(result)

        # Ensure ssh comand was not called
        self.assertEqual(0, mock_cmd._mock_call_count)

    @mock.patch(MOCK_CMD)
    def test_check_key_fails(self, mock_cmd):
        """
        key is present and ssh succeeds, function returns True
        """
        user = 'stephen'
        host = '10.2.10.10'

        opts = '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no '
        opts += '-o BatchMode=Yes'
        ssh_cmd = 'ssh -i %s %s %s@%s hostname' % (PEM_FILE, opts, user, host)

        mock_cmd.return_value = (1, "", "")
        result = utils.check_private_key(user, PEM_FILE, host)
        self.assertFalse(result)
        mock_cmd.assert_called_with(ssh_cmd, is_logging=False)


class TestOpenStack(unittest.TestCase):
    """
    Class to test function openstack
    """
    @mock.patch(MOCK_CMD)
    def test_openstack(self, mock_cmd):
        """
        check openstack command is called correctly with correct prefix,
        and returning the return values from cmd.
        """
        os_cmd = 'server list'
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        ret_val = (0, "", "")
        mock_cmd.return_value = ret_val

        result = utils.openstack(os_cmd, env)
        self.assertEqual(ret_val, result)
        mock_cmd.assert_called_with('openstack --insecure ' + os_cmd,
                                    env=env, is_logging=False)


class TestGetKeyNamesFromStack(unittest.TestCase):
    """
    Class to test function get_key_names_from_stack
    """
    @mock.patch(MOCK_CMD)
    def test_get_key_names_ok(self, mock_cmd):
        """
        get key name from stack list
        """
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        os_cmd = "openstack --insecure stack list -c 'Stack Name' -f value"
        expected_key = ['staging01_cu_key']
        mock_cmd.return_value = (0, STACK_LIST, "")

        result = utils.get_key_names_from_stack(env)
        self.assertEqual(result, expected_key)
        mock_cmd.assert_called_with(os_cmd, env=env, is_logging=False)

    @mock.patch(MOCK_CMD)
    def test_get_key_names_several(self, mock_cmd):
        """
        get multiple matching key names
        """
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        os_cmd = "openstack --insecure stack list -c 'Stack Name' -f value"
        expected_keys = ['staging01_cu_key', 'second_cu_key']
        mock_cmd.return_value = (0, STACK_LIST + 'second_cu_key', "")

        result = utils.get_key_names_from_stack(env)
        self.assertEqual(result, expected_keys)
        mock_cmd.assert_called_with(os_cmd, env=env, is_logging=False)

    @mock.patch(MOCK_CMD)
    def test_get_key_names_fails(self, mock_cmd):
        """
        Openstack command fails
        """
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        os_cmd = "openstack --insecure stack list -c 'Stack Name' -f value"
        mock_cmd.return_value = (1, '', 'Openstack Failed')

        result = utils.get_key_names_from_stack(env)
        self.assertEqual(result, [])
        mock_cmd.assert_called_with(os_cmd, env=env, is_logging=False)

    @mock.patch(MOCK_CMD)
    def test_get_key_names_no_match(self, mock_cmd):
        """
        OpenStack command okay but  does not return key
        """
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        os_cmd = "openstack --insecure stack list -c 'Stack Name' -f value"
        mock_cmd.return_value = (0, 'no matching key', '')

        result = utils.get_key_names_from_stack(env)
        self.assertEqual(result, [])
        mock_cmd.assert_called_with(os_cmd, env=env, is_logging=False)


class TestGetPrivateKey(unittest.TestCase):
    """
    Class to test function get_private_key
    """
    @mock.patch(MOCK_CMD)
    def test_get_private_key_ok(self, mock_cmd):
        """
        Key is retrieved from OpenStack
        """
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        expected_key = 'Dummy\nPrivate\nKey\n----END RSA PRIVATE KEY-----\n'
        key_output = r'''{
  "description": "Key Pair Template",
  "stack_name": "staging01_cu_key",
  "outputs": [
    {
      "output_value": "ssh-rsa blahblah dummy public key",
      "output_key": "cloud_user_public_key",
      "description": "No description given"
    },
    {
      "output_value": "Dummy\nPrivate\nKey\n----END RSA PRIVATE KEY-----\n",
      "output_key": "cloud_user_private_key",
      "description": "No description given"
    }
  ],
  "stack_status": "CREATE_COMPLETE",
  "id": "9e189216-2164-4c81-af97-6a79961f55a8"
}
'''
        mock_cmd.return_value = (0, key_output, '')
        result = utils.get_private_key('staging01_cu_key', env)
        import sys
        print >> sys.stderr, result
        self.assertEqual(result, expected_key)

    @mock.patch(MOCK_JSON + '.loads')
    @mock.patch(MOCK_CMD)
    def test_get_private_key_os_fails(self, mock_cmd, mock_json):
        """
        OpenStack command fails with error
        """
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        mock_cmd.return_value = (1, '', 'OpenStack Failed')
        result = utils.get_private_key('staging01_cu_key', env)

        self.assertEqual(result, None)
        # Ensure the None return occured before the json call
        self.assertEqual(0, mock_json._mock_call_count)

    @mock.patch(MOCK_JSON + '.loads')
    @mock.patch(MOCK_CMD)
    def test_get_private_key_val_err(self, mock_cmd, mock_json):
        """
        Json parsing of OpenStack output raises a ValueError
        """
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        mock_cmd.return_value = (0, '', '')
        mock_json.side_effect = ValueError()
        result = utils.get_private_key('staging01_cu_key', env)

        self.assertEqual(result, None)
        self.assertEqual(1, mock_json._mock_call_count)

    @mock.patch(MOCK_JSON + '.loads')
    @mock.patch(MOCK_CMD)
    def test_get_private_key_not_found(self, mock_cmd, mock_json):
        """
        Json object does not contain key
        """
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        mock_cmd.return_value = (0, '', '')
        mock_json.return_value = {'outputs': ['1', '2'], 'b': 'a', 'c': 'a'}
        result = utils.get_private_key('staging01_cu_key', env)
        self.assertEqual(1, mock_json._mock_call_count)
        self.assertEqual(result, None)

    @mock.patch(MOCK_JSON + '.loads')
    @mock.patch(MOCK_CMD)
    def test_get_private_key_bad_data(self, mock_cmd, mock_json):
        """
        Json object does not have the 'outputs' key
        """
        env = {'OS_ENDPOINT_TYPE': 'internalURL'}
        mock_cmd.return_value = (0, '', '')
        mock_json.return_value = {'a': 1, 'b': 2, 'c': 3}
        result = utils.get_private_key('staging01_cu_key', env)
        self.assertEqual(1, mock_json._mock_call_count)
        self.assertEqual(result, None)


class TestCreateTempKeyFile(unittest.TestCase):
    """
    Class to test function create_temp_key_file
    """
    @mock.patch(MOCK_PACKAGE + 'os.chmod')
    @mock.patch(MOCK_PACKAGE + 'tempfile.NamedTemporaryFile')
    def test_create_temp_key_ok(self, mock_tmp, mock_chmod):
        """
        Check that temp file is created with expected contents.
        """
        key_to_write = 'Here are the key contents'
        result = utils.create_temp_key_file(key_to_write)

        # Check that the contents match what was passed
        self.assertEqual(result.write.call_args, mock.call(key_to_write))

        # Check correct permissions were applied
        self.assertEqual(mock_chmod.call_args, mock.call(result.name, 0600))

        # Check expected call counts
        self.assertEqual(result.write.call_count, 1)
        self.assertEqual(result.flush.call_count, 1)
        self.assertEqual(mock_chmod.call_count, 1)


class CfgClassTestCase(unittest.TestCase):
    """
    The tests are all scenarios to validate the get methods from the
    configuration object
    """

    def setUp(self):
        """
        Set up a configuration object with a configuration .ini file
        """
        self.cfg = utils.Cfg()
        self.cfg.read_config(CFG_CLASS_CONFIG_FILE)

    def test_read_config_file(self):
        """
        Test to assert if the 'get' method can read a key (section.option) and
        the read_config method created the object correctly.
        """
        self.assertEqual(self.cfg.get('general.test'), 'cfg_class')

    def test_reading_boolean_true(self):
        """
        Test to assert if the 'get_bool' method can read a key (section.option)
        correctly and return a True boolean value.
        """
        self.assertTrue(self.cfg.get_bool('boolean_values.success'))

    def test_reading_boolean_false(self):
        """
        Test to assert if the 'get_bool' method can read a key (section.option)
        correctly and return a False boolean value.
        """
        self.assertFalse(self.cfg.get_bool('boolean_values.fail'))

    def test_reading_integer(self):
        """
        Test to assert if the 'get_int' method can read a key (section.option)
        correctly and return an int value.
        """
        self.assertIsInstance(self.cfg.get_int('int_values.timer_min'), int)

    def test_reading_list(self):
        """Test to assert if the 'get' method returns a list correctly
        """
        test_list = ['customer1', 'customer2', 'customer3']
        self.assertEqual(self.cfg.get('list_values.customers').split(','),
                         test_list)

    def test_not_existing_section(self):
        """Raise exception test when a non existing section is called
        """
        with self.assertRaises(ConfigParser.NoSectionError):
            self.cfg.get('not_existing_section.customers')

    def test_not_existing_option(self):
        """Raise exception test when a non existing option is called
        """
        with self.assertRaises(ConfigParser.NoOptionError):
            self.cfg.get('general.not_existing_option')


class CfgClassUsingMockTestCase(unittest.TestCase):
    """
    The tests are all scenarios to validate the get methods from the
    configuration object using the mock library
    """

    @mock.patch(MOCK_PACKAGE + 'Cfg')
    def test_get_method(self, mock_cfg):
        """
        Test to assert that the method returns a valid value
        :param mock_cfg: mocking the Cfg object
        """
        cfg = utils.Cfg()
        mock_cfg.return_value.get.call_args = 'section.key1'
        mock_cfg.return_value.get.return_value = 123
        self.assertEqual(cfg.get('section.key1'), 123)

    @mock.patch(MOCK_PACKAGE + 'Cfg')
    def test_get_int(self, mock_cfg):
        """
        Test to assert that the method returns an int value
        :param mock_cfg: mocking the Cfg object
        """
        cfg = utils.Cfg()
        mock_cfg.return_value.get_int.call_args = 'section.key2'
        mock_cfg.return_value.get_int.return_value = 456

        self.assertIsInstance(cfg.get_int('section.key2'), int)

    @mock.patch(MOCK_PACKAGE + 'Cfg')
    def test_get_boolean_true(self, mock_cfg):
        """
        Test to assert that the method returns a boolean value (True)
        :param mock_cfg: mocking the Cfg object
        """
        cfg = utils.Cfg()
        mock_cfg.return_value.get_bool.call_args = 'section.key3'
        mock_cfg.return_value.get_bool.return_value = True

        self.assertTrue(cfg.get_bool('section.key3'))

    @mock.patch(MOCK_PACKAGE + 'Cfg')
    def test_get_boolean_false(self, mock_cfg):
        """
        Test to assert that the method returns a boolean value (False)
        :param mock_cfg: mocking the Cfg object
        """
        cfg = utils.Cfg()
        mock_cfg.return_value.get_bool.call_args = 'section.key4'
        mock_cfg.return_value.get_bool.return_value = False

        self.assertFalse(cfg.get_bool('section.key4'))

    @mock.patch(MOCK_PACKAGE + 'ConfigParser.SafeConfigParser')
    def test_config_parser_instance(self, mock_conf):
        """
        Test if the instance of SafeConfigParser is being properly set up
        Values 'section.option' are set directly into a SCP object, but
        read through the Cfg object
        :param mock_conf: mocking the SafeConfigParser object
        """
        cfg = utils.Cfg()
        mock_conf.return_value.get.call_args = 'general.test'
        mock_conf.return_value.get.return_value = 123

        result = cfg.get('general.test')
        self.assertEqual(result, 123)
