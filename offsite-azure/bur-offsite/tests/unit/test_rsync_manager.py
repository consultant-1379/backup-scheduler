##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""This is unit test module for the backup.rsync_manager script."""

import subprocess
import unittest

import mock

from backup.exceptions import RsyncException, UtilsException
from backup.rsync_manager import RsyncManager, RsyncOutput

MOCK_PACKAGE = 'backup.rsync_manager'

MOCK_NUMBER_FILES_FOLDERS_LOCAL = MOCK_PACKAGE + '.get_number_of_content_from_path'
MOCK_NUMBER_FILES_FOLDERS_REMOTE = MOCK_PACKAGE + '.get_number_of_content_from_remote_path'
MOCK_PARSE_OUTPUT = MOCK_PACKAGE + '.RsyncManager.parse_output'
MOCK_SEND = MOCK_PACKAGE + '.RsyncManager.send'
MOCK_RECEIVE = MOCK_PACKAGE + '.RsyncManager.receive'

MOCK_PATH = MOCK_PACKAGE + '.os.path'
MOCK_LIST_DIR = MOCK_PACKAGE + '.os.listdir'
MOCK_SUBPROCESS_CHECK_OUTPUT = MOCK_PACKAGE + '.subprocess.check_output'
MOCK_CHECK_REMOTE_PATH_EXISTS = MOCK_PACKAGE + '.check_remote_path_exists'

FAKE_TRIES = 1
FAKE_PATH = 'fake/path'
FAKE_HOST = 'fake_host@fake_ip'
FAKE_SOURCE = 'fake_source_path'
FAKE_TARGET = 'fake_target_path'
FAKE_FULL_HOST_SOURCE_PATH = "{}:{}".format(FAKE_HOST, FAKE_SOURCE)

RSYNC_OUTPUT = "Number of files: 2 (reg: 1, dir: 1)\n" \
               "Number of created files: 1\n" \
               "Number of deleted files: 2\n" \
               "Number of regular files transferred: 1\n" \
               "Total file size: 685 bytes\n" \
               "Total transferred file size: 787 bytes\n" \
               "Literal data: 680 bytes\n" \
               "Matched data: 787 bytes\n" \
               "File list size: 0\n" \
               "File list generation time: 0.001 seconds\n" \
               "File list transfer time: 0.000 seconds\n" \
               "Total bytes sent: 95\n" \
               "Total bytes received: 17\n\n" \
               "sent 95 bytes  received 17 bytes  74.67 bytes/sec\n" \
               "total size is 0  speedup is 0.00"

HALF_RSYNC_OUTPUT = "Number of files: 2 (reg: 1, dir: 1)\n" \
                    "Number of regular files transferred: 1\n" \
                    "Total file size: 685 bytes\n" \
                    "Total transferred file size: 787 bytes\n" \
                    "Literal data: 680 bytes\n" \
                    "Matched data: 787 bytes\n" \
                    "File list size: 0\n" \
                    "Total bytes sent: 95\n" \
                    "Total bytes received: 17\n\n" \
                    "sent 95 bytes  received 17 bytes  74.67 bytes/sec\n"


class RsyncManagerParseNumberOfFileKeyValueTestCase(unittest.TestCase):
    """These are scenarios when a line from the output result is read and parsed correctly."""

    def setUp(self):
        """Set up the test constants."""
        self.total_files_tuple = 'total_files', '2'
        self.created_tuple = 'created', '1'
        self.deleted_tuple = 'deleted', '2'
        self.transferred_tuple = 'transferred', '1'

    def test_parse_number_of_file_key_value_total_files(self):
        """Assert if the 'total files line' output is read and parsed."""
        line_output = RSYNC_OUTPUT.lower().split('\n')[0]
        result = RsyncManager.parse_number_of_file_key_value(line_output)
        self.assertEqual(self.total_files_tuple, result)

    def test_parse_number_of_file_key_value_created(self):
        """Assert if the 'created line' output is read and parsed."""
        line_output = RSYNC_OUTPUT.lower().split('\n')[1]
        result = RsyncManager.parse_number_of_file_key_value(line_output)
        self.assertEqual(self.created_tuple, result)

    def test_parse_number_of_file_key_value_deleted(self):
        """Assert if the 'deleted line' output is read and parsed."""
        line_output = RSYNC_OUTPUT.lower().split('\n')[2]
        result = RsyncManager.parse_number_of_file_key_value(line_output)
        self.assertEqual(self.deleted_tuple, result)

    def test_parse_number_of_file_key_value_transferred(self):
        """Assert if the 'transferred line' output is read and parsed."""
        line_output = RSYNC_OUTPUT.lower().split('\n')[3]
        result = RsyncManager.parse_number_of_file_key_value(line_output)
        self.assertEqual(self.transferred_tuple, result)


class RsyncManagerParseNumberOfFileKeyValueRsyncExceptionTestCase(unittest.TestCase):
    """
    Failed scenario for cases when invalid line from output is not parsed and exceptions are raised.

    A line is considered invalid when it doesn't have the 'number of' or a valid value
    """

    def test_parse_number_of_file_key_value_no_number(self):
        """Assert if an exception is raised when the line doesn't have 'number of' string on it."""
        line_output = RSYNC_OUTPUT.lower().split('\n')[4]
        exception_message = "Line does not contain a number of measurement."

        with self.assertRaises(RsyncException) as raised:
            RsyncManager.parse_number_of_file_key_value(line_output)

        self.assertIn(exception_message, raised.exception.message)

    def test_parse_number_of_file_key_value_no_value(self):
        """Assert if an exception is raised if a line doesn't have a value following 'number of'."""
        line_output = "Number of regular files transferred"
        exception_message = "Value informed cannot be parsed."

        with self.assertRaises(RsyncException) as raised:
            RsyncManager.parse_number_of_file_key_value(line_output.lower())

        self.assertIn(exception_message, raised.exception.message)


class RsyncManagerParseOutputValidateDictionaryTestCase(unittest.TestCase):
    """This is a scenario when a rsync output is correctly parsed to a rsync output dictionary."""

    def test_parse_output(self):
        """Assert if the rsync_output passed is correctly parsed."""
        summary_dic = {'total_files': '2',
                       'created': '1',
                       'deleted': '2',
                       'transferred': '1',
                       'rate': '74.67',
                       'speedup': '0.00'}
        rsync_output = RsyncOutput(summary_dic)

        result = RsyncManager.parse_output(RSYNC_OUTPUT)
        self.assertEqual(str(rsync_output), str(result))


class RsyncManagerParseOutputInvalidOutputRsyncExceptionTestCase(unittest.TestCase):
    """This is scenario when an output has no valid tags to create a RsyncOutput object."""

    def setUp(self):
        """Set up the test constants."""
        self.exception_message = "Value informed cannot be parsed."

    def test_parse_output_empty_input(self):
        """Assert if an exception is raised when an invalid output is informed."""
        with self.assertRaises(RsyncException) as raised:
            RsyncManager.parse_output("This is an invalid output with text but no tags!")

        self.assertEqual(self.exception_message, raised.exception.message)

    def test_parse_output_half_dictionary(self):
        """Assert if an exception is raised when an incomplete output is informed."""
        with self.assertRaises(RsyncException) as raised:
            RsyncManager.parse_output(HALF_RSYNC_OUTPUT)

        self.assertEqual(self.exception_message, raised.exception.message)


class RsyncManagerParseOutputEmptyRsyncExceptionTestCase(unittest.TestCase):
    """
    Scenario when an invalid line from output is not read and exceptions are raised.

    A line is considered invalid when it is empty or None.
    """

    def setUp(self):
        """Set up the test constants."""
        self.exception_message = "Value not informed."

    def test_parse_output_empty_input(self):
        """Assert if an exception is raised when an empty output is informed as an argument."""
        with self.assertRaises(UtilsException) as raised:
            RsyncManager.parse_output(" ")

        self.assertEqual(self.exception_message, raised.exception.message)

    def test_parse_output_none_input(self):
        """Assert if an exception is raised when a None object is informed as an argument."""
        with self.assertRaises(UtilsException) as raised:
            RsyncManager.parse_output(None)

        self.assertEqual(self.exception_message, raised.exception.message)


class RsyncManagerReceiveTestCase(unittest.TestCase):
    """This is a scenario when a rsync process receives files successfully from remote to local."""

    def setUp(self):
        """Set up the test constants."""
        self.rsync = RsyncManager(FAKE_FULL_HOST_SOURCE_PATH, FAKE_TARGET, FAKE_TRIES)

        self.summary_dic = {'total_files': '2',
                            'created': '1',
                            'deleted': '2',
                            'transferred': '1',
                            'rate': '74.67',
                            'speedup': '0.00'}
        self.rsync_output = RsyncOutput(self.summary_dic)

    @mock.patch(MOCK_CHECK_REMOTE_PATH_EXISTS)
    @mock.patch(MOCK_SUBPROCESS_CHECK_OUTPUT)
    @mock.patch(MOCK_NUMBER_FILES_FOLDERS_LOCAL)
    @mock.patch(MOCK_NUMBER_FILES_FOLDERS_REMOTE)
    def test_receive(self, mock_number_files_folders_remote, mock_number_files_folders_local,
                     mock_check_output, mock_check_remote_path_exists):
        """
        Assert if the receive process was successful and returned the rsync output correctly.

        :param mock_number_files_folders_remote: mock a result for counting files and folders.
        :param mock_number_files_folders_local: mock a result for counting files and folders.
        :param mock_check_output: mocking a valid result from subprocess.check_output.
        :param mock_check_remote_path_exists: mocking a valid result from
        utils.check_remote_path_exists.
        """
        mock_number_files_folders_remote.return_value = 1, 0
        mock_number_files_folders_local.return_value = 1, 0
        mock_check_remote_path_exists.return_value = True
        mock_check_output.return_value = RSYNC_OUTPUT

        result = self.rsync.receive()
        self.assertEqual(str(self.rsync_output), str(result))


class RsyncManagerReceiveCalledProcessErrorTestCase(unittest.TestCase):
    """Scenario when CalledProcessError is raised while checking the rsync output."""

    def setUp(self):
        """Set up the test constants."""
        self.rsync = RsyncManager(FAKE_FULL_HOST_SOURCE_PATH, FAKE_TARGET, FAKE_TRIES)
        self.exception_message = "returned non-zero"

    @mock.patch(MOCK_SUBPROCESS_CHECK_OUTPUT)
    @mock.patch(MOCK_CHECK_REMOTE_PATH_EXISTS)
    def test_receive(self, mock_check_remote_path_exists, mock_check_output):
        """
        Assert if an exception is raised when the CalledProcessError exception is caught.

        :param mock_check_remote_path_exists: mocking a valid result from
        utils.check_remote_path_exists.
        """
        mock_check_remote_path_exists.return_value = True
        mock_check_output.side_effect = subprocess.CalledProcessError(1, ["", ""])

        with self.assertRaises(RsyncException) as raised:
            self.rsync.receive()

        self.assertIn(self.exception_message, raised.exception.message)


class RsyncManagerReceiveRsyncExceptionTestCase(unittest.TestCase):
    """Scenario when any other kind of exception is raised as RsyncException."""

    def setUp(self):
        """Set up the test constants."""
        self.rsync = RsyncManager(FAKE_FULL_HOST_SOURCE_PATH, FAKE_TARGET, FAKE_TRIES)
        self.command_exception_message = "Path informed is not a valid formatted folder or file."

    @mock.patch(MOCK_NUMBER_FILES_FOLDERS_LOCAL)
    def test_receive_invalid_source_path(self, mock_number_files):
        """Assert if an exception is raised when an invalid source path is informed."""
        self.rsync.source_path = FAKE_SOURCE
        mock_number_files.return_value = 1, 1
        expected_error_msg = "Path informed is not a valid formatted folder or file."

        with self.assertRaises(RsyncException) as raised:
            self.rsync.receive()

        self.assertIn(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_CHECK_REMOTE_PATH_EXISTS)
    @mock.patch(MOCK_NUMBER_FILES_FOLDERS_LOCAL)
    def test_receive_remote_path_does_not_exist(self, mock_number_files,
                                                mock_check_remote_path_exists):
        """
        Assert if raises an exception when the remote path is not existent.

        :param mock_check_remote_path_exists: mocking a valid output for the
        utils.check_remote_path_exists method.
        """
        mock_number_files.return_value = 1, 1
        self.rsync.source_path = "fake:remote_path"
        mock_check_remote_path_exists.return_value = False

        with self.assertRaises(RsyncException) as raised:
            self.rsync.receive()

        self.assertIn("Path informed is not a valid formatted folder or file.",
                      raised.exception.message)

    @mock.patch(MOCK_SUBPROCESS_CHECK_OUTPUT)
    @mock.patch(MOCK_NUMBER_FILES_FOLDERS_LOCAL)
    def test_receive(self, mock_number_files, mock_check_output):
        """
        Assert if the RsyncException raised has the custom message.

        :param mock_check_output: mocking a valid output for the subprocess.check_output method.
        """
        mock_number_files.return_value = 1, 1
        mock_check_output.side_effect = RsyncException

        with self.assertRaises(RsyncException) as raised:
            self.rsync.receive()

        self.assertIn(self.command_exception_message, raised.exception.message)

    @mock.patch(MOCK_CHECK_REMOTE_PATH_EXISTS)
    @mock.patch(MOCK_SUBPROCESS_CHECK_OUTPUT)
    @mock.patch(MOCK_NUMBER_FILES_FOLDERS_LOCAL)
    @mock.patch(MOCK_NUMBER_FILES_FOLDERS_REMOTE)
    def test_receive_different_number_files(self, mock_number_files_folders_remote,
                                            mock_number_files_folders_local, mock_check_output,
                                            mock_check_remote_path_exists):
        """
        Assert if an RsyncException is raised.

        The situation observed in this case is when the number of files from remote source
        differs from the number of files on destination when the transfer is over.

        :param mock_number_files_folders_remote: mock a result for counting files and folders
        :param mock_number_files_folders_local: mock a result for counting files and folders
        :param mock_check_output: mocking a valid result from subprocess.check_output.
        :param mock_check_remote_path_exists: mocking a valid result from check_remote_path_exists.
        """
        expected_exception_message = "Number of files transferred differs from files on origin " \
                                     "path and destination path."

        mock_number_files_folders_remote.return_value = 1, 0
        mock_number_files_folders_local.return_value = 2, 0
        mock_check_remote_path_exists.return_value = True
        mock_check_output.return_value = RSYNC_OUTPUT

        with self.assertRaises(RsyncException) as raised:
            self.rsync.receive()

        self.assertIn(expected_exception_message, raised.exception.message)


class RsyncManagerSendTestCase(unittest.TestCase):
    """This is scenario when files are successfully send from local to remote."""

    def setUp(self):
        """Set up the test constants."""
        self.rsync = RsyncManager(FAKE_SOURCE, FAKE_TARGET, FAKE_TRIES)

        self.summary_dic = {'total_files': '2',
                            'created': '1',
                            'deleted': '2',
                            'transferred': '1',
                            'rate': '74.67',
                            'speedup': '0.00'}
        self.rsync_output = RsyncOutput(self.summary_dic)

    @mock.patch(MOCK_SUBPROCESS_CHECK_OUTPUT)
    @mock.patch(MOCK_NUMBER_FILES_FOLDERS_LOCAL)
    def test_send(self, mock_number_files, mock_check_output):
        """
        Assert if the rsync_output is returned correctly.

        :param mock_number_files: mocking the number of files that should be transferred.
        :param mock_check_output: mocking a valid subprocess.check_output return.
        """
        mock_check_output.return_value = RSYNC_OUTPUT
        mock_number_files.return_value = 1, 1

        result = self.rsync.send()
        self.assertEqual(str(self.rsync_output), str(result))


class RsyncManagerSendRetryRsyncExceptionTestCase(unittest.TestCase):
    """
    Scenario for send method in RsyncManager.

    This scenario applies when the maximum number of tries has been reached and not all the files
    have been transferred, so an RsyncException is raised.
    """

    def setUp(self):
        """Set up the test constants."""
        self.number_files_to_transfer = 7
        self.rsync = RsyncManager(FAKE_SOURCE, FAKE_TARGET, FAKE_TRIES)
        self.exception_message = "The limit of tries has been reached."

    @mock.patch(MOCK_NUMBER_FILES_FOLDERS_LOCAL)
    @mock.patch(MOCK_SUBPROCESS_CHECK_OUTPUT)
    def test_send(self, mock_check_output, mock_number_files):
        """
        Assert if an exception is raised when the maximum tries are reached.

        :param mock_check_output: mocking a valid subprocess.check_output return value.
        :param mock_number_files: mocking the number of files that should be transferred.
        """
        mock_check_output.return_value = RSYNC_OUTPUT
        mock_number_files.return_value = self.number_files_to_transfer, 1

        with self.assertRaises(RsyncException) as raised:
            self.rsync.send()

        self.assertIn(self.exception_message, raised.exception.message)


class RsyncManagerTransferFileTestCases(unittest.TestCase):
    """This is a scenario to test the behavior of the static transfer file method."""

    def setUp(self):
        """Set up the test constants."""
        self.summary_dic = {'total_files': '2',
                            'created': '1',
                            'deleted': '2',
                            'transferred': '1',
                            'rate': '74.67',
                            'speedup': '0.00'}

        self.rsync_output = RsyncOutput(self.summary_dic)

    def test_transfer_file_empty_source_and_target(self):
        """Assert if an exception is raised when empty parameters are informed."""
        with self.assertRaises(UtilsException) as raised:
            RsyncManager.transfer_file("", "")

        empty_input_exception_message = "Value not informed."

        self.assertEqual(empty_input_exception_message, raised.exception.message)

    def test_transfer_file_receive_mode_invalid_source(self):
        """Assert if an exception is raised when source path is invalid."""
        with self.assertRaises(RsyncException) as raised:
            RsyncManager.transfer_file(FAKE_FULL_HOST_SOURCE_PATH, FAKE_TARGET)

        expected_exception_msg = "Path informed is not a valid formatted folder or file."

        self.assertIn(expected_exception_msg, raised.exception.message)

    def test_transfer_file_send_mode_invalid_source(self):
        """Assert if an exception is raised when source path is invalid."""
        with self.assertRaises(UtilsException) as raised:
            RsyncManager.transfer_file(FAKE_PATH, FAKE_TARGET)

        expected_exception_message = "Path informed is not a valid formatted folder or file."

        self.assertIn(expected_exception_message, raised.exception.message)

    @mock.patch(MOCK_SEND)
    def test_transfer_file_valid_send(self, mock_send):
        """
        Assert if returns True when in send mode with valid parameters.

        :param mock_send: mock of RsyncManager send function.
        """
        mock_send.return_value = self.rsync_output

        send_result = RsyncManager.transfer_file(FAKE_PATH, FAKE_TARGET)

        self.assertTrue(isinstance(send_result, RsyncOutput))

    @mock.patch(MOCK_RECEIVE)
    def test_transfer_file_valid_receive(self, mock_receive):
        """
        Assert if returns True when in receive mode with valid parameters.

        :param mock_receive: mock of RsyncManager receive function.
        """
        mock_receive.return_value = self.rsync_output

        receive_result = RsyncManager.transfer_file(FAKE_FULL_HOST_SOURCE_PATH, FAKE_TARGET)

        self.assertTrue(isinstance(receive_result, RsyncOutput))
