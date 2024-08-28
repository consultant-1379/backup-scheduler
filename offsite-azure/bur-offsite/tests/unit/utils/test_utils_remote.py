##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""The purpose of this module is to provide unit testing for remote.py utility script."""

import os
import shutil
import unittest

import mock

from backup.exceptions import UtilsException
from backup.utils.fsys import create_path
import backup.utils.remote as remote

MOCK_PACKAGE = 'backup.utils.remote.'

SCRIPT_PATH = os.path.dirname(__file__)
TMP_DIR = os.path.join(SCRIPT_PATH, "temp_dir")
VALID_USER = 'user'
VALID_HOST = '127.0.0.1'
INVALID_HOST = "2.3.4."
VALID_COMMAND = "echo Hello World!\n"
INVALID_COMMAND = 'bla'
MOCK_USER_HOST = VALID_USER + '@' + VALID_HOST


class RemoteCheckRemotePathTestCase(unittest.TestCase):
    """Test Cases for check_remote_path function in remote.py utility script."""

    @mock.patch.object(remote, 'run_ssh_command')
    def test_check_remote_path_attempt_run_remote_command(self, mock_popen):
        """
        Assert if Popen was called and executed correctly.

        :param mock_popen: mocking utils.run_ssh_command method.
        """
        mock_popen.return_value = "DIR_IS_AVAILABLE", ""
        result = remote.check_remote_path_exists(VALID_HOST, SCRIPT_PATH)

        mock_popen.assert_called_once()
        self.assertTrue(result)

    @mock.patch("backup.constants.TIMEOUT")
    def test_check_remote_path_non_existent_directory(self, mock_timeout):
        """
        Assert if returns False when remote path doesn't exist.

        :param mock_timeout: mocking backup.constants.TIMEOUT constant.
        """
        mock_timeout.return_value = 20
        self.assertFalse(remote.check_remote_path_exists(VALID_HOST, TMP_DIR))

    @mock.patch("backup.constants.TIMEOUT")
    def test_check_remote_path_existence(self, mock_timeout):
        """
        Assert if returns True when remote path exists.

        :param mock_timeout: mocking backup.constants.TIMEOUT constant.
        """
        mock_timeout.return_value = 20
        self.assertTrue(remote.check_remote_path_exists(VALID_HOST, SCRIPT_PATH))

    @mock.patch("backup.constants.TIMEOUT")
    def test_check_remote_path_in_invalid_host(self, mock_timeout):
        """
        Assert if returns False when remote host doesn't exist.

        :param mock_timeout: mocking backup.constants.TIMEOUT constant.
        """
        mock_timeout.return_value = 20
        self.assertFalse(remote.check_remote_path_exists(INVALID_HOST, SCRIPT_PATH))


class RemoteCreateRemoteDirTestCase(unittest.TestCase):
    """Test Cases for create_remote_dir function in remote.py utility script."""

    @mock.patch("backup.constants.TIMEOUT")
    @mock.patch.object(remote, 'run_ssh_command')
    def test_create_remote_dir_with_valid_host_and_path(self, mock_run_ssh_cmd, mock_timeout):
        """
        Assert if returns True when creating directory in remote valid host and path.

        :param mock_timeout: mocking backup.constants.TIMEOUT constant.
        :param mock_run_ssh_cmd: mocking utils.run_ssh_command method.
        """
        mock_timeout.return_value = 20
        mock_run_ssh_cmd.return_value = "DIR_IS_AVAILABLE\n", ""

        result = remote.create_remote_dir(VALID_HOST, TMP_DIR)
        self.assertTrue(result)
        mock_run_ssh_cmd.test_assert_called_once()


class RemoteRemoveRemoteDirTestCase(unittest.TestCase):
    """Test Cases for remove_remote_path function in remote.py utility script."""

    def setUp(self):
        """Create testing scenario."""
        self.dir_list = ['bkps/CUSTOMER/2018-09-10',
                         'bkps/CUSTOMER/2018-09-11',
                         'bkps/CUSTOMER/2018-09-12']

        self.remove_dir_list = []

        for directory in self.dir_list:
            self.remove_dir_list.append(os.path.join(SCRIPT_PATH, directory))
            create_path(self.remove_dir_list[-1])

    def tearDown(self):
        """Tear down created scenario."""
        shutil.rmtree(os.path.join(SCRIPT_PATH, 'bkps'))

    @mock.patch("backup.constants.TIMEOUT")
    def test_remove_remote_dir_list(self, mock_timeout):
        """
        Assert if not removed list is empty and the to remove and removed dirs are the same.

        :param mock_timeout: mocking backup.constants.TIMEOUT constant.
        """
        mock_timeout.return_value = 20
        not_removed_list, validated_removed_list = remote.remove_remote_dir(VALID_HOST,
                                                                            self.remove_dir_list)

        self.assertFalse(bool(not_removed_list))
        self.assertEqual(self.remove_dir_list, validated_removed_list)

    def test_remove_remote_dir_empty_list(self):
        """Assert if raises an exception when the list of dirs to be removed is empty."""
        with self.assertRaises(Exception) as exception:
            remote.remove_remote_dir(VALID_HOST, [])
        self.assertEqual("Value not informed.", exception.exception.message)

    @mock.patch("backup.constants.TIMEOUT")
    def test_remove_remote_dir_single_directory(self, mock_timeout):
        """
        Assert if returns a list of removed with a single dir and not removed list is empty.

        :param mock_timeout: mocking backup.constants.TIMEOUT constant.
        """
        mock_timeout.return_value = 20
        not_removed_list, validated_removed_list = remote.remove_remote_dir(VALID_HOST,
                                                                            self.remove_dir_list[0])
        self.assertFalse(bool(not_removed_list))
        self.assertEqual(1, len(validated_removed_list))

    @mock.patch("backup.constants.TIMEOUT")
    def test_remove_remote_dir_invalid_directory(self, mock_timeout):
        """
        Test remove invalid directory from valid remote_machine.

        :param mock_timeout: mocking backup.constants.TIMEOUT constant.
        """
        # needs rewrite
        mock_timeout.return_value = 20
        not_removed_list, validated_removed_list = remote.remove_remote_dir(VALID_HOST, TMP_DIR)

        self.assertFalse(bool(not_removed_list))
        self.assertEqual(1, len(validated_removed_list))

    @mock.patch("backup.constants.TIMEOUT")
    def test_remove_remote_dir_from_invalid_remote(self, mock_timeout):
        """
        Assert if an exception is raised when host is invalid.

        :param mock_timeout: mocking backup.constants.TIMEOUT constant.
        """
        mock_timeout.return_value = 20
        with self.assertRaises(UtilsException) as exception:
            remote.remove_remote_dir(INVALID_HOST, self.remove_dir_list)
        self.assertIn("Path(s) informed cannot be removed.", exception.exception.message)


class RemoteRunSshCommandTestCase(unittest.TestCase):
    """Test Cases for run_ssh_command function in remote.py utility script."""

    @mock.patch("backup.constants.TIMEOUT")
    def test_run_remote_command_valid_host_and_command(self, mock_timeout):
        """
        Assert if returns a valid stdout when executing a valid command in a valid host.

        :param mock_timeout: mocking backup.utils.TIMEOUT constant.
        """
        mock_timeout.return_value = 20
        stdout, _ = remote.run_ssh_command(VALID_HOST, VALID_COMMAND)
        self.assertEqual(b"Hello World!\n", stdout)
        stdout, _ = remote.run_ssh_command('localhost', VALID_COMMAND)
        self.assertEqual(b"Hello World!\n", stdout)

    def test_run_remote_command_invalid_host(self):
        """Assert if returns an empty stdout and stderr has the error about the invalid host."""
        stdout, stderr = remote.run_ssh_command(INVALID_HOST, VALID_COMMAND)

        expected_error = "ssh: Could not resolve hostname {}: Name or service not known" \
            .format(INVALID_HOST)

        self.assertIn(expected_error, stderr)
        self.assertEqual("", stdout)

    def test_run_remote_command_invalid_command(self):
        """Assert if returns an empty stdout and stderr has the error about the invalid command."""
        stdout, stderr = remote.run_ssh_command(VALID_HOST, INVALID_COMMAND)

        expected_error = "bash: line 1: {}: command not found\n".format(INVALID_COMMAND)

        self.assertIn(expected_error, stderr)
        self.assertEqual("", stdout)


class RemoteIsRemoteFolderEmpty(unittest.TestCase):
    """Test Cases for is_remote_folder_empty function in remote.py utility script."""

    @mock.patch(MOCK_PACKAGE + 'get_number_of_content_from_remote_path')
    def test_is_remote_folder_empty_dir_is_empty(self, mock_get_number_of_content_from_remote_path):
        """Assert if the function returns true when the remote folder is empty."""
        mock_get_number_of_content_from_remote_path.return_value = (0, 0)
        result = remote.is_remote_folder_empty(MOCK_USER_HOST, 'remote/path')

        self.assertTrue(result)

    @mock.patch(MOCK_PACKAGE + 'get_number_of_content_from_remote_path')
    def test_is_remote_folder_empty_dir_is_not_empty(
            self, mock_get_number_of_content_from_remote_path):
        """Assert if the function returns false when the remote folder is not empty."""
        mock_get_number_of_content_from_remote_path.return_value = (1, 0)
        result = remote.is_remote_folder_empty(MOCK_USER_HOST, 'remote/path')

        self.assertFalse(result)

    @mock.patch(MOCK_PACKAGE + 'get_number_of_content_from_remote_path')
    def test_is_remote_folder_empty_invalid_path(self, mock_get_number_of_content_from_remote_path):
        """Assert if the function raises an exception if the input was invalid."""
        mock_get_number_of_content_from_remote_path.side_effect = UtilsException

        expected_error_msg = "Something went wrong."

        with self.assertRaises(UtilsException) as raised:
            remote.is_remote_folder_empty(MOCK_USER_HOST, 'remote/path')

        self.assertEqual(expected_error_msg, raised.exception.message)


class RemoteSortRemoteFoldersByContent(unittest.TestCase):
    """Test Cases for sort_remote_folders_by_content function in remote.py utility script."""

    def test_sort_remote_folders_by_content_empty_list(self):
        """Assert if the function returns an empty list in case of empty input."""
        result = remote.sort_remote_folders_by_content(MOCK_USER_HOST, [])
        self.assertEqual([], result)

    @mock.patch(MOCK_PACKAGE + 'run_ssh_command')
    def test_sort_remote_folders_by_content_ssh_cmd_error(self, mock_run_ssh_command):
        """Assert if the function raises an exception in case ssh command failed."""
        mock_path_list = ['path/folder1', 'path/folder2']
        mock_ssh_error_msg = 'ssh error'
        mock_run_ssh_command.return_value = '', mock_ssh_error_msg
        with self.assertRaises(UtilsException) as cex:
            remote.sort_remote_folders_by_content(MOCK_USER_HOST, mock_path_list)

        expected_error_msg = "Couldn't sort the list of backups from the offsite location. " \
                             "(['{}', {}, '{}'])"\
            .format(MOCK_USER_HOST, mock_path_list, mock_ssh_error_msg)

        self.assertEqual(expected_error_msg, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'run_ssh_command')
    def test_sort_remote_folders_by_content_folder_list_sorted(self, mock_run_ssh_command):
        """Assert if the list of folders is sorted correctly by the date of their oldest files."""
        mock_path_list = ['path/folder1', 'path/folder2', 'path/folder3']

        mock_ssh_stdout = '2000-01-01+10:30:00 path/folder1/oldest_file\nEND_OF_COMMAND\n' \
                          '2000-01-01+10:45:00 path/folder2/oldest_file\nEND_OF_COMMAND\n' \
                          '2000-01-01+11:00:00 path/folder3/oldest_file\nEND_OF_COMMAND\n'

        mock_run_ssh_command.return_value = mock_ssh_stdout, ''

        result = remote.sort_remote_folders_by_content(MOCK_USER_HOST, mock_path_list)

        expected_result = ['path/folder3', 'path/folder2', 'path/folder1']
        self.assertEqual(expected_result, result)

    @mock.patch(MOCK_PACKAGE + 'run_ssh_command')
    def test_sort_remote_folders_by_content_folder_parse_error(self, mock_run_ssh_command):
        """Assert if the function raises an exception in case of error parsing the stdout."""
        mock_path_list = ['path/folder1', 'failed/path/folder2', 'path/folder3']

        mock_ssh_stdout = '2000-01-01+10:30:00 path/folder1/oldest_file\nEND_OF_COMMAND\n' \
                          'failed\nEND_OF_COMMAND\n' \
                          '2000-01-01+11:00:00 path/folder3/oldest_file\nEND_OF_COMMAND\n'

        mock_run_ssh_command.return_value = mock_ssh_stdout, ''

        with self.assertRaises(UtilsException) as cex:
            remote.sort_remote_folders_by_content(MOCK_USER_HOST, mock_path_list)

        expected_error_msg = "Couldn't sort the list of backups from the offsite location. " \
                             "(['{}', {}, '{}'])"\
            .format(MOCK_USER_HOST, mock_path_list, 'failed')

        self.assertEqual(expected_error_msg, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'run_ssh_command')
    def test_sort_remote_folders_by_content_folder_empty_path(self, mock_run_ssh_command):
        """Assert if the list of folders is sorted correctly when one of the folders is empty."""
        mock_path_list = ['path/folder1', 'empty/path/folder2', 'path/folder3']

        mock_ssh_stdout = '2000-01-01+10:30:00 path/folder1/oldest_file\nEND_OF_COMMAND\n' \
                          '\nEND_OF_COMMAND\n' \
                          '2000-01-01+11:00:00 path/folder3/oldest_file\nEND_OF_COMMAND\n'

        mock_run_ssh_command.return_value = mock_ssh_stdout, ''

        result = remote.sort_remote_folders_by_content(MOCK_USER_HOST, mock_path_list)

        expected_result = ['path/folder3', 'path/folder1']
        self.assertEqual(expected_result, result)

    @mock.patch(MOCK_PACKAGE + 'run_ssh_command')
    def test_sort_remote_folders_by_content_folder_all_empty_path(self, mock_run_ssh_command):
        """Assert if an empty list is returned when all folders from input are empty."""
        mock_path_list = ['empty/path/folder1', 'empty/path/folder2', 'empty/path/folder3']

        mock_ssh_stdout = '\nEND_OF_COMMAND\n' \
                          '\nEND_OF_COMMAND\n' \
                          '\nEND_OF_COMMAND\n'

        mock_run_ssh_command.return_value = mock_ssh_stdout, ''

        result = remote.sort_remote_folders_by_content(MOCK_USER_HOST, mock_path_list)

        expected_result = []
        self.assertEqual(expected_result, result)
