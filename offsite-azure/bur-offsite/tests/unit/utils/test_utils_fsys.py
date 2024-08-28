##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=undefined-variable

# flake8: noqa=F821
# undefined name 'file'

"""The purpose of this module is to provide unit testing for fsys.py utility script."""

import getpass
import os
import unittest

import mock

import backup.constants as constants
from backup.utils import fsys

MOCK_PACKAGE = 'backup.utils.fsys.'
MOCK_LOGGER_PACKAGE = 'backup.logger.CustomLogger'

MOCK_PATH = 'mock/path'


def get_mock_logger():
    """Get a mock logger object."""
    with mock.patch(MOCK_LOGGER_PACKAGE) as mock_logger:
        mock_logger.log_root_path = ""
        mock_logger.log_file_name = ""

    return mock_logger


class GetHomeDirTestCase(unittest.TestCase):
    """Class for unit testing get_home_dir function."""

    def test_home_dir(self):
        """Test if the returned path is home directory."""
        current_home_directory = os.path.expanduser("~")
        result = fsys.get_home_dir()
        self.assertEqual(current_home_directory, result)


class GetPathToDocsTestCase(unittest.TestCase):
    """Class for unit testing get_path_to_docs function."""

    def test_get_path_to_docs(self):
        """Test if the returned path is Documents directory inside home directory."""
        home_directory = os.path.expanduser("~")
        current_doc_directory = os.path.join(home_directory, "Documents")
        result = fsys.get_path_to_docs()
        self.assertEqual(current_doc_directory, result)


class IsDirTestCase(unittest.TestCase):
    """Class for unit testing is_dir function."""

    def setUp(self):
        """Set up the test constants."""
        self.mock_logger = get_mock_logger()

    def test_is_dir(self):
        """Assert if result is True when the path is for a valid directory."""
        result = fsys.is_dir(os.path.expanduser("~"))
        self.assertTrue(result)

    @mock.patch(MOCK_PACKAGE + 'os.path.exists')
    def test_is_dir_path_does_not_exist(self, mock_os_path_exists):
        """Assert if result is False when the path is non existent."""
        home_directory = os.path.expanduser("~")
        mock_os_path_exists.return_value = False

        result = fsys.is_dir(home_directory)

        self.assertFalse(result)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_is_dir_path_is_not_dir(self, mock_os):
        """Assert if result is False when path is not for a dir."""
        home_directory = os.path.expanduser("~")
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False

        result = fsys.is_dir(home_directory)

        self.assertFalse(result)


class SplitFolderListTestCase(unittest.TestCase):
    """Class for unit testing split_folder_list function."""

    def test_split_folder_list_should_succeed(self):
        """Assert if the result is a list with all the items from the string."""
        directory_items = ['Desktop', 'Downloads', 'Pictures',
                           'PycharmProjects', 'Templates', 'workspace',
                           'Documents', 'Music', 'Public', 'Videos']
        sample_directory_string = '\n'.join(directory_items)
        result = fsys.split_folder_list(sample_directory_string)
        self.assertTrue(isinstance(result, list))
        self.assertEqual(len(directory_items), len(result))
        for name in directory_items:
            self.assertTrue(name in result)

    def test_split_folder_list_remove_trailing_slash_should_succeed(self):
        """Assert if the result list has all the items from the string, without backslash."""
        directory_items = ['Desktop/', 'Downloads/']
        sample_directory_string = '\n'.join(directory_items)

        result = fsys.split_folder_list(sample_directory_string)

        self.assertTrue(isinstance(result, list))
        self.assertEqual(len(directory_items), len(result))
        self.assertTrue('/' not in result[0])
        self.assertTrue('/' not in result[1])

    def test_split_folder_list_excluding_dot_from_result_should_succeed(self):
        """Assert if '.' is excluded from the final list."""
        directory_items = ['.', 'Desktop/', 'Downloads/']
        sample_directory_string = '\n'.join(directory_items)

        result = fsys.split_folder_list(sample_directory_string)

        self.assertTrue('.' not in result)


class GetExistingRootPathTestCase(unittest.TestCase):
    """Class for unit testing the function."""

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_existing_root_path_should_succeed(self, mock_os):
        """Given a valid path this scenario should succeed."""
        mock_os.path.isdir.return_value = True
        mock_os.path.isabs.return_value = True
        mock_os.path.normpath.return_value = MOCK_PATH
        mock_os.path.exists.side_effect = [False, True]
        mock_os.path.split.return_value = os.path.split(MOCK_PATH)

        expected_path = 'mock'
        result_path = fsys.get_existing_root_path(MOCK_PATH)

        self.assertEqual(expected_path, result_path)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_existing_root_path_should_not_fail_with_invalid_path(self, mock_os):
        """Given an invalid path this scenario should return false."""
        mock_os.path.isdir.return_value = False
        mock_os.path.isabs.return_value = False

        mock_expected_exception_message = "Path informed is not a valid formatted folder or file."

        with self.assertRaises(Exception) as ex:
            fsys.get_existing_root_path(MOCK_PATH)

        self.assertIn(mock_expected_exception_message, ex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_existing_root_path_should_accept_starting_with_dot(self, mock_os):
        """Given a path that does not exists."""
        mock_os.path.isdir.return_value = True
        mock_os.path.isabs.return_value = True
        mock_os.path.normpath.return_value = MOCK_PATH
        mock_os.path.exists.side_effect = [False, False, False]
        mock_os.path.split.side_effect = [os.path.split(MOCK_PATH), ('', '')]

        mock_expected_exception_message = "Path informed is not a valid formatted folder or file."

        with self.assertRaises(Exception) as ex:
            fsys.get_existing_root_path(MOCK_PATH)

        self.assertIn(mock_expected_exception_message, ex.exception.message)


class GetFormattedSizeTestCase(unittest.TestCase):
    """Class for unit testing the get_formatted_size function."""

    @mock.patch(MOCK_PACKAGE + 'get_size_on_disk')
    def test_get_formatted_size_on_disk_should_succeed_log_with_mb(self, mock_get_size_on_disk):
        """Valid test scenario should succeed logging with MB size indicator."""
        mock_size_mb = 1000

        mock_get_size_on_disk.return_value = mock_size_mb

        sut_expected_result = "{}{}".format(mock_size_mb, constants.BLOCK_SIZE_MB_STR)

        result = fsys.get_formatted_size_on_disk(MOCK_PATH)

        self.assertEqual(sut_expected_result, result)

    @mock.patch(MOCK_PACKAGE + 'get_size_on_disk')
    def test_get_formatted_size_on_disk_should_succeed_log_with_gb(self, mock_get_size_on_disk):
        """Valid test scenario should succeed logging with GB size indicator."""
        mock_size_mb = 1024

        mock_get_size_on_disk.return_value = mock_size_mb

        sut_expected_result = "1GB"

        result = fsys.get_formatted_size_on_disk(MOCK_PATH)

        self.assertEqual(sut_expected_result, result)


class GetFreeDiskSpaceTestCase(unittest.TestCase):
    """Class for unit testing the get_free_disk_space function."""

    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'get_existing_root_path')
    def test_get_free_disk_space_should_succeed(self, mock_get_existing_root_path, mock_popen):
        """Valid test scenario should succeed."""
        mock_get_existing_root_path.return_value = ''

        free_space_size = 46415696
        expected_free_space = free_space_size / constants.BLOCK_SIZE_MB

        popen_output = "Filesystem 1K-blocks Used Available Use% Mounted on\n" \
                       "/dev/sda1 60211076 10707100 {} 19%".format(free_space_size)

        mock_popen.return_value.stdout.readlines.return_value = popen_output.split('\n')
        mock_popen.return_value.stderr = None

        ret_free_space = fsys.get_free_disk_space(MOCK_PATH)

        self.assertEqual(expected_free_space, ret_free_space)

    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'get_existing_root_path')
    def test_get_free_disk_space_no_readlines(self, mock_get_existing_root_path, mock_popen):
        """
        Assert if an Exception is raised when Popen doesn't return a value for stdout.

        :param mock_get_existing_root_path: mock an existing path.
        :param mock_popen: mock the result of Popen.
        """
        mock_get_existing_root_path.return_value = ''
        mock_popen.return_value.stderr = None
        mock_popen.return_value.stdout = []

        with self.assertRaises(Exception):
            fsys.get_free_disk_space(MOCK_PATH)


class GetFolderFileListsFromDirTestCase(unittest.TestCase):
    """Class for unit testing the get_folder_file_lists_from_dir function."""

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_folder_file_lists_from_dir_should_succeed_collect_all_directories(self, mock_os):
        """Test should collect all folders and not files."""
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = True

        mock_os.listdir.return_value = ['vol0', 'vol1']

        mock_expected_dir_list = ['path/vol0', 'path/vol1']
        mock_os.path.join.side_effect = mock_expected_dir_list

        mock_os.path.isfile.return_value = False

        result_dir_list, result_file_list = fsys.get_folder_file_lists_from_dir(MOCK_PATH)

        self.assertEqual(mock_expected_dir_list, result_dir_list)

        self.assertEqual(0, len(result_file_list))

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_folder_file_lists_from_dir_should_succeed_collect_all_files(self, mock_os):
        """Test should return just files."""
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = True

        mock_os.listdir.return_value = ['file0', 'file1']

        mock_expected_file_list = ['path/file0', 'path/file1']
        mock_os.path.join.side_effect = mock_expected_file_list

        mock_os.path.isfile.return_value = True

        result_dir_list, result_file_list = fsys.get_folder_file_lists_from_dir(MOCK_PATH)

        self.assertEqual(mock_expected_file_list, result_file_list)

        self.assertEqual(0, len(result_dir_list))

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_folder_file_lists_from_dir_should_succeed_collect_files_folders(self, mock_os):
        """Test should return files and folders."""
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = True

        mock_os.listdir.return_value = ['file0', 'file1', 'folder0', 'folder1']

        mock_expected_file_list = ['path/file0', 'path/file1']
        mock_expected_dir_list = ['path/folder0', 'path/folder1']
        mock_os.path.join.side_effect = mock_expected_file_list + mock_expected_dir_list

        mock_os.path.isfile.side_effect = [True, True, False, False]

        result_dir_list, result_file_list = fsys.get_folder_file_lists_from_dir(MOCK_PATH)

        self.assertEqual(mock_expected_dir_list, result_dir_list)

        self.assertEqual(mock_expected_file_list, result_file_list)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_folder_file_lists_from_dir_should_fail_when_path_is_not_directory(self, mock_os):
        """Test when the informed path is not a folder."""
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False

        mock_expected_exception_message = "Path informed is not a valid existent folder."
        with self.assertRaises(Exception) as ex:
            fsys.get_folder_file_lists_from_dir(MOCK_PATH)

        self.assertIn(mock_expected_exception_message, ex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_folder_file_lists_from_dir_should_fail_when_path_not_exists(self, mock_os):
        """Test when the informed path does not exist."""
        mock_os.path.exists.return_value = False

        mock_expected_exception_message = "Path informed is not a valid existent folder."
        with self.assertRaises(Exception) as ex:
            fsys.get_folder_file_lists_from_dir(MOCK_PATH)

        self.assertIn(mock_expected_exception_message, ex.exception.message)


class CreatePickleFileTestCase(unittest.TestCase):
    """Class for unit testing the create_pickle_file function."""

    @mock.patch(MOCK_PACKAGE + 'pickle')
    @mock.patch(MOCK_PACKAGE + 'open')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_create_pickle_file_should_succeed(self, mock_os, mock_open, mock_pickle):
        """Testing scenario should proceed creating the file."""
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_pickle.return_value.dump.return_value = None
        mock_os.path.exists.return_value = True

        result = fsys.create_pickle_file([], MOCK_PATH)

        self.assertEqual(MOCK_PATH, result)

    def test_create_pickle_file_should_fail_with_empty_file_param(self):
        """Testing scenario should fail creating the file with empty filename."""
        mock_expected_exception_message = "Value not informed."

        with self.assertRaises(Exception) as ex:
            fsys.create_pickle_file([], '')

        self.assertIn(mock_expected_exception_message, ex.exception.message)


class LoadPickleFileTestCase(unittest.TestCase):
    """Class for unit testing the load_pickle_file function."""

    @mock.patch(MOCK_PACKAGE + 'pickle')
    @mock.patch(MOCK_PACKAGE + 'open')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_load_pickle_file_should_succeed(self, mock_os, mock_open, mock_pickle):
        """Testing scenario should proceed loading the file."""
        mock_os.path.exists.return_value = True
        mock_open.return_value = mock.MagicMock(spec=file)

        mock_file_content = 'file content'
        mock_pickle.load.return_value = mock_file_content

        sut_data_result = fsys.load_pickle_file(MOCK_PATH)

        self.assertEqual(mock_file_content, sut_data_result)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_load_pickle_file_should_fail_with_invalid_path(self, mock_os):
        """Testing scenario should proceed creating the file."""
        mock_os.path.exists.return_value = False

        mock_expected_exception_message = "Path informed is not a valid formatted folder or file."
        with self.assertRaises(Exception) as ex:
            fsys.load_pickle_file(MOCK_PATH)

        self.assertIn(mock_expected_exception_message, ex.exception.message)

    def test_load_pickle_file_should_fail_with_empty_file_param(self):
        """Testing scenario should proceed creating the file."""
        mock_expected_exception_message = "Value not informed."

        with self.assertRaises(Exception) as ex:
            fsys.load_pickle_file('')

        self.assertIn(mock_expected_exception_message, ex.exception.message)


class GetCurrentUserTestCase(unittest.TestCase):
    """Class for unit testing the get_current_user function."""

    def test_get_current_user_should_succeed(self):
        """Test scenario should successfully get current user."""
        expected_current_user = getpass.getuser()

        sut_user_result = fsys.get_current_user()

        self.assertEqual(expected_current_user, sut_user_result)


class GetNumberOfFilesFromPathTestCase(unittest.TestCase):
    """Class for unit testing get_number_of_content_from_path function."""

    @mock.patch(MOCK_PACKAGE + 'is_valid_path')
    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_number_of_content_from_path_has_folder(self, mock_os, mock_valid_path):
        """Assert if there are files to be transferred from the source path."""
        mock_valid_path.return_value = True
        mock_os.path.join.return_value = ''
        mock_os.path.isdir.side_effect = [True, False, True, False, False]
        mock_os.listdir.side_effect = [['file0', 'folder1', 'file2'], ['file1']]

        files, folders = fsys.get_number_of_content_from_path(MOCK_PATH)

        self.assertEqual(3, files)
        self.assertEqual(1, folders)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_number_of_content_from_path_is_folder(self, mock_os):
        """Test when the source path is a folder with 3 files."""
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.side_effect = [True, False, False, False]
        mock_os.listdir.return_value = ['file0', 'file1', 'file2']

        files, _ = fsys.get_number_of_content_from_path(MOCK_PATH)

        self.assertEqual(3, files)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_number_of_content_from_path_is_file(self, mock_os):
        """Assert if the informed path is a file."""
        mock_os.path.exists.return_value = True
        mock_os.path.isdir.return_value = False

        files, _ = fsys.get_number_of_content_from_path(MOCK_PATH)

        self.assertEqual(1, files)

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_get_number_of_content_from_path_invalid_dir(self, mock_os):
        """Assert if an Exception with the expected message is raised."""
        mock_os.path.exists.return_value = False

        exception_message = "Path informed is not a valid formatted folder or file."
        with self.assertRaises(Exception) as cex:
            fsys.get_number_of_content_from_path(MOCK_PATH)

        self.assertIn(exception_message, cex.exception.message)
