##############################################################################
# COPYRIGHT Ericsson AB 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=too-many-arguments,undefined-variable,too-few-public-methods

# flake8: noqa=F821
# undefined name

"""Module for testing backup.gnupg_manager.py script."""

import logging
import unittest

import mock

from backup.exceptions import ExceptionCodes, GnupgException, UtilsException
from backup.gnupg_manager import GnupgManager

logging.disable(logging.CRITICAL)

MOCK_PACKAGE = 'backup.gnupg_manager.'
MOCK_CHECK_NOT_EMPTY = MOCK_PACKAGE + 'check_not_empty'
MOCK_IS_VALID_PATH = MOCK_PACKAGE + "is_valid_path"
MOCK_IS_DIR = MOCK_PACKAGE + "is_dir"

MOCK_GPG_KEY_PATH = 'mock_gpg_key_path'
MOCK_SOURCE_DIR = 'mock_path'
MOCK_EMAIL = 'mock_user_email'
MOCK_USER_NAME = 'mock_user_name'
MOCK_FILE_PATH = 'mock_file_path'
MOCK_OUTPUT_PATH = 'mock_output_path'
MOCK_COMPRESSED_FILE = 'mock_encrypted_file.gz'
MOCK_COMPRESSED_ENCRYPTED_FILE = 'mock_encrypted_file.gz.gpg'
MOCK_NUMBER_THREADS = 5


def get_gnupg_manager():
    """
    Get an instance of gnupg_manager to perform tests.

    :return: gnupg_manager instance.
    """
    with mock.patch(MOCK_PACKAGE + 'CustomLogger') as mock_logger:
        with mock.patch(MOCK_PACKAGE + 'GPG') as mock_gpg_handler:
            with mock.patch(MOCK_PACKAGE + 'GnupgManager.validate_encryption_key') as \
                    mock_validate_encryption_key:
                mock_validate_encryption_key.return_value = True
                gnupg_manager = GnupgManager(MOCK_USER_NAME, MOCK_EMAIL, mock_logger)
                gnupg_manager.gpg_handler = mock_gpg_handler
                gnupg_manager.gpg_key_path = MOCK_GPG_KEY_PATH

    return gnupg_manager


class GnupgManagerValidateEncryptionKeyTestCase(unittest.TestCase):
    """Class for testing validate_encryption_key() method from GnupgManager class."""

    def setUp(self):
        """Set up the test variables."""
        self.gnupg_manager = get_gnupg_manager()

    @mock.patch(MOCK_PACKAGE + 'Popen')
    def test_validate_encryption_key_already_exists(self, mock_popen):
        """Assert if returns True and log the info about an existing gpg key."""
        mock_popen.return_value.communicate.return_value = ('', '')

        calls = [mock.call("Validating GPG encryption key."),
                 mock.call("Backup key already exists.")]

        validation_result = self.gnupg_manager.validate_encryption_key()

        self.assertTrue(validation_result, "Should have returned true.")
        self.gnupg_manager.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'GnupgManager.create_gpg_key')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    def test_validate_encryption_key_creation_key_succeeded(self, mock_popen, mock_create_gpg_key):
        """Test when gpg key is not found and the system should create a new key successfully."""
        mock_popen.return_value.communicate.return_value = ('', 'error reading key')
        mock_create_gpg_key.return_value = True

        calls = [mock.call("GPG key not found in the system."),
                 mock.call("GPG key was created successfully.")]

        ret = self.gnupg_manager.validate_encryption_key()

        self.assertTrue(ret, "Should have returned true.")
        self.gnupg_manager.logger.warning.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'GnupgManager.create_gpg_key')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    def test_validate_encryption_key_creation_key_failed(self, mock_popen, mock_create_gpg_key):
        """Assert if an exception is raised when the GPG key cannot be created."""
        mock_popen.return_value.communicate.return_value = ('', 'error reading key')
        mock_create_gpg_key.return_value = False
        expected_error_msg = "GPG key could not be created."

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.validate_encryption_key()

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'get_current_user')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    def test_validate_encryption_key_permission_denied(self, mock_popen, mock_get_current_user):
        """Test to check when gpg key is not read due to permission issues."""
        mock_popen.return_value.communicate.return_value = ('', 'permission denied')
        mock_get_current_user.return_value = MOCK_USER_NAME

        with self.assertRaises(Exception) as cex:
            self.gnupg_manager.validate_encryption_key()

        expected_msg = "Error retrieving GPG keys. Check if the current user '{}' has permission " \
                       "to access '{}'".format(MOCK_USER_NAME, MOCK_GPG_KEY_PATH)

        self.assertEqual(cex.exception.message, expected_msg)


class GnupgManagerCreateGpgKeyTestCase(unittest.TestCase):
    """Class for testing create_gpg_key() method from GnupgManager class."""

    class MockGenKeyOutput:
        """Mock class of the GPG.gen_key output."""

        def __init__(self, stderr):
            self.stderr = stderr

    def setUp(self):
        """Setting up the test variables."""
        self.gnupg_manager = get_gnupg_manager()

    def test_create_gpg_key_succeeded(self):
        """Test when the gpg key was created successfully and the function should return true."""
        gen_key_call = [mock.call.gen_key_input(key_length=1024, key_type='RSA',
                                                name_email=MOCK_EMAIL,
                                                name_real=MOCK_USER_NAME)]

        self.gnupg_manager.gpg_handler.gen_key.return_value = \
            GnupgManagerCreateGpgKeyTestCase.MockGenKeyOutput('mock_output.KEY_CREATED.mock_output')

        ret = self.gnupg_manager.create_gpg_key()

        self.assertTrue(ret)
        self.gnupg_manager.gpg_handler.assert_has_calls(gen_key_call)

    def test_create_gpg_key_failed(self):
        """Test when the gpg key creation failed and the function should return false."""
        self.gnupg_manager.gpg_handler.return_value.gen_key_input.return_value = None

        self.gnupg_manager.gpg_handler.gen_key.return_value = \
            GnupgManagerCreateGpgKeyTestCase.MockGenKeyOutput(
                'mock_output.KEY_NOT_CREATED.mock_output')

        ret = self.gnupg_manager.create_gpg_key()

        self.assertFalse(ret)


class GnupgManagerEncryptFileTestCase(unittest.TestCase):
    """Class for testing encrypt_file() method from GnupgManager class."""

    def setUp(self):
        """Set up the test variables."""
        self.gnupg_manager = get_gnupg_manager()

    def test_encrypt_file_empty_file_path(self):
        """Assert if it raises an exception when file_path is empty."""
        with self.assertRaises(UtilsException) as raised:
            self.gnupg_manager.encrypt_file('', MOCK_OUTPUT_PATH)

        self.assertIn("Value not informed.", raised.exception.message)

    def test_encrypt_file_empty_output_path(self):
        """Assert if it raises an exception when output_path is empty."""
        with self.assertRaises(UtilsException) as raised:
            self.gnupg_manager.encrypt_file(MOCK_FILE_PATH, '')

        self.assertIn("Value not informed.", raised.exception.message)

    def test_encrypt_file_input_file_does_not_exists(self):
        """Assert if it raises an exception when file_path does not exist."""
        expected_error_msg = "Path informed is not a valid formatted folder or file."

        with self.assertRaises(UtilsException) as raised:
            self.gnupg_manager.encrypt_file(MOCK_FILE_PATH, MOCK_OUTPUT_PATH)

        self.assertIn(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_IS_VALID_PATH)
    def test_encrypt_file_encryption_failure(self, mock_is_valid_path, mock_os, mock_open,
                                             mock_popen):
        """Assert if it raises an exception when encryption could not be completed."""
        mock_is_valid_path.return_value = True
        mock_os.path.join.return_value = ''
        mock_os.path.basename.return_value = ''
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_popen.return_value.wait.return_value = 1
        expected_error_msg = "File encryption could not be completed."

        calls = [mock.call("Encrypting file '{}'".format(MOCK_FILE_PATH))]

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.encrypt_file(MOCK_FILE_PATH, MOCK_OUTPUT_PATH)

        self.assertIn(expected_error_msg, raised.exception.message)
        self.gnupg_manager.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_PACKAGE + 'open')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_IS_VALID_PATH)
    @mock.patch(MOCK_CHECK_NOT_EMPTY)
    def test_encrypt_file_return_value(self, mock_check_not_empty, mock_is_valid_path,
                                       mock_os, mock_open, mock_popen):
        """Assert if it returns the path of a encrypted file when attempting an encryption."""
        mock_file_input = '/path/to/mock_input'
        mock_output_path = '/path/to/output'
        mock_result_path = '/path/to/output/mock_input'

        mock_check_not_empty.return_value = True
        mock_is_valid_path.return_value = True

        mock_os.path.join.return_value = mock_result_path
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_popen.return_value.wait.return_value = 0

        calls = [mock.call("Encrypting file '{}'".format(mock_file_input))]

        encrypt_result = self.gnupg_manager.encrypt_file(mock_file_input, mock_output_path)

        self.assertEqual('/path/to/output/mock_input.gpg', encrypt_result)
        self.gnupg_manager.logger.info.assert_has_calls(calls)


class GnupgManagerCompressEncryptFileTestCase(unittest.TestCase):
    """Class for testing compress_encrypt_file() method from GnupgManager class."""

    def setUp(self):
        """Set up the test variables."""
        self.gnupg_manager = get_gnupg_manager()

    @mock.patch(MOCK_PACKAGE + 'compress_file')
    def test_compress_encrypt_file_compress_failure_exception(self, mock_compress_file):
        """Assert if an exception is raised when an error occurs during compression."""
        expected_error_msg = "Error Code 30. Something went wrong."
        mock_compress_file.side_effect = UtilsException

        calls = [mock.call("Compressing file {}.".format(MOCK_FILE_PATH))]

        with self.assertRaises(UtilsException) as raised:
            self.gnupg_manager.compress_encrypt_file(MOCK_FILE_PATH, '')

        self.assertEqual(expected_error_msg, str(raised.exception))
        self.gnupg_manager.logger.info.assert_has_calls(calls)

    @mock.patch(MOCK_PACKAGE + 'GnupgManager.encrypt_file')
    @mock.patch(MOCK_PACKAGE + 'compress_file')
    def test_compress_encrypt_file_encrypt_failure_exception(
            self, mock_compress_file, mock_encrypt_file):
        """Assert if an exception is raised when an error occurs during encrypt."""
        mock_compress_file.return_value = ''
        expected_error_msg = "File encryption could not be completed."
        mock_encrypt_file.side_effect = GnupgException(ExceptionCodes.EncryptError)

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.compress_encrypt_file('', '')

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager.encrypt_file')
    @mock.patch(MOCK_PACKAGE + 'compress_file')
    def test_compress_encrypt_file_remove_failure_exception(
            self, mock_compress_file, mock_encrypt_file, mock_remove_path):
        """Assert if it raises an exception when removal step return False."""
        mock_compress_file.return_value = ''
        mock_encrypt_file.return_value = ''
        expected_error_msg = "File cannot be removed."

        mock_remove_path.return_value = False

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.compress_encrypt_file('', '')

        self.assertEqual(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager.encrypt_file')
    @mock.patch(MOCK_PACKAGE + 'compress_file')
    def test_compress_encrypt_file_success_case(
            self, mock_compress_file, mock_encrypt_file, mock_remove_path):
        """Assert if it returns the output correctly when the process is done successfully."""
        mock_output_file_name = 'output_file'
        mock_compress_file.return_value = ''
        mock_encrypt_file.return_value = mock_output_file_name
        mock_remove_path.return_value = True

        compress_encrypt_result = self.gnupg_manager.compress_encrypt_file('', '')
        self.assertEqual(mock_output_file_name, compress_encrypt_result)


class GnupgManagerCompressEncryptFileListTestCase(unittest.TestCase):
    """Class for testing compress_encrypt_file_list() method from GnupgManager class."""

    def setUp(self):
        """Set up the test variables."""
        self.gnupg_manager = get_gnupg_manager()

    @mock.patch(MOCK_PACKAGE + 'os')
    def test_compress_encrypt_file_list_invalid_source_path_failure_exception(self, mock_os):
        """Assert if it raises an exception when the source_path does not exist."""
        mock_os.path.exists.return_value = False

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.compress_encrypt_file_list(MOCK_SOURCE_DIR, '', MOCK_NUMBER_THREADS)

        self.assertIn("Path informed is not a valid existent folder.", raised.exception.message)

    @mock.patch(MOCK_IS_DIR)
    def test_compress_encrypt_file_list_path_is_not_dir(self, mock_is_dir):
        """Assert if it raises an exception when the source_path is not a folder."""
        mock_is_dir.return_value = False
        expected_error_msg = "Path informed is not a valid existent folder."

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.compress_encrypt_file_list(MOCK_SOURCE_DIR, '', MOCK_NUMBER_THREADS)

        self.assertIn(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_IS_DIR)
    def test_compress_encrypt_file_list_output_path_does_not_exist(self, mock_is_dir):
        """Assert if it raises an exception if output_path is not a directory."""
        mock_is_dir.return_value = True
        expected_error_msg = "Path informed is not a valid formatted folder or file."

        with self.assertRaises(UtilsException) as raised:
            self.gnupg_manager.compress_encrypt_file_list(MOCK_SOURCE_DIR, MOCK_OUTPUT_PATH,
                                                          MOCK_NUMBER_THREADS)

        self.assertIn(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'ThreadPool')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_IS_DIR)
    @mock.patch(MOCK_IS_VALID_PATH)
    def test_compress_encrypt_file_list_success_case(self, mock_is_valid_path, mock_is_dir,
                                                     mock_os, mock_thread_pool):
        """Assert if it returns True when all the files from list are encrypted and compressed."""
        mock_is_dir.return_value = True
        mock_is_valid_path.return_value = True
        mock_file_list = ['file0', 'file1', 'file2']
        mock_os.listdir.return_value = mock_file_list
        mock_thread_pool.create_thread.return_value = None
        mock_os.path.join.side_effect = ['mock_path/file0', 'mock_path/file1', 'mock_path/file2']
        mock_create_thread_calls = []

        for file_name in mock_file_list:
            source_file_path = "{}/{}".format(MOCK_SOURCE_DIR, file_name)

            mock_create_thread_calls.append(
                mock.call().create_thread("{}-Thread".format(file_name),
                                          self.gnupg_manager.compress_encrypt_file,
                                          source_file_path, MOCK_OUTPUT_PATH))

        result = self.gnupg_manager.compress_encrypt_file_list(MOCK_SOURCE_DIR, MOCK_OUTPUT_PATH,
                                                               MOCK_NUMBER_THREADS)
        self.assertTrue(result)
        mock_thread_pool.assert_has_calls(mock_create_thread_calls)


class GnupgManagerDecryptFileTestCase(unittest.TestCase):
    """Class for testing decrypt_file() method from GnupgManager class."""

    def setUp(self):
        """Set up the test variables."""
        self.gnupg_manager = get_gnupg_manager()

    def test_decrypt_file_empty_file_path(self):
        """Assert if it raises an exception when encrypted_file_path is empty."""
        with self.assertRaises(UtilsException) as raised:
            self.gnupg_manager.decrypt_file('')

        self.assertIn("Value not informed.", raised.exception.message)

    @mock.patch(MOCK_IS_VALID_PATH)
    def test_decrypt_file_invalid_file_extension(self, mock_is_valid_path):
        """Assert if it raises an exception when encrypted_file_path doesn't have .gpg extension."""
        mock_input_file = 'file.dat'
        mock_is_valid_path.return_value = True

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.decrypt_file(mock_input_file)

        self.assertIn("Not a valid GPG encrypted file.", raised.exception.message)

    def test_decrypt_file_path_does_not_exist(self):
        """Assert if it raises an exception when encrypted_file_path does not exist."""
        mock_input_file = 'file.gpg'
        expected_error_msg = "Path informed is not a valid formatted folder or file."

        with self.assertRaises(UtilsException) as raised:
            self.gnupg_manager.decrypt_file(mock_input_file)

        self.assertIn(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_IS_VALID_PATH)
    @mock.patch(MOCK_IS_DIR)
    def test_decrypt_file_input_path_is_dir(self, mock_is_dir, mock_is_valid_path):
        """Assert if it raises an exception when encrypted_file_path is not a file."""
        mock_input_file = 'file.gpg'
        mock_is_valid_path.return_value = True
        mock_is_dir.return_value = True
        expected_error_msg = "Path informed is not a valid existent file."

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.decrypt_file(mock_input_file)

        self.assertIn(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'open')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_IS_VALID_PATH)
    @mock.patch(MOCK_IS_DIR)
    def test_decrypt_file_decryption_failure_exception(self, mock_is_dir, mock_is_valid_path,
                                                       mock_popen, mock_open):
        """Assert if raises an exception when an error happens when trying to decrypt the file."""
        mock_input_file = 'file.gpg'
        mock_is_valid_path.return_value = True
        mock_is_dir.return_value = False
        mock_popen.return_value.wait.return_value = 1
        mock_open.return_value = mock.MagicMock(spec=file)
        expected_error_msg = "File decryption could not be completed."

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.decrypt_file(mock_input_file)

        self.assertIn(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'open')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_IS_VALID_PATH)
    @mock.patch(MOCK_IS_DIR)
    def test_decrypt_file_decryption_success_case(self, mock_is_dir, mock_is_valid_path,
                                                  mock_popen, mock_open):
        """Test when the file is decrypted successfully."""
        mock_input_file = 'file.gpg'
        mock_is_valid_path.return_value = True
        mock_is_dir.return_value = False
        mock_popen.return_value.wait.return_value = 0
        mock_open.return_value = mock.MagicMock(spec=file)

        decrypt_file_result = self.gnupg_manager.decrypt_file(mock_input_file)
        self.assertEqual('file', decrypt_file_result)

    @mock.patch(MOCK_PACKAGE + 'remove_path')
    @mock.patch(MOCK_PACKAGE + 'open')
    @mock.patch(MOCK_PACKAGE + 'Popen')
    @mock.patch(MOCK_IS_VALID_PATH)
    @mock.patch(MOCK_IS_DIR)
    def test_decrypt_file_decryption_success_case_remove_flag(
            self, mock_is_dir, mock_is_valid_path, mock_popen, mock_open, mock_remove_path):
        """Test when the file is decrypted successfully and the original file is removed."""
        mock_input_file = 'file.gpg'
        mock_is_valid_path.return_value = True
        mock_is_dir.return_value = False
        mock_popen.return_value.wait.return_value = 0
        mock_open.return_value = mock.MagicMock(spec=file)
        mock_remove_path.return_value = True

        decrypt_file_result = self.gnupg_manager.decrypt_file(mock_input_file, True)

        self.assertEqual('file', decrypt_file_result)
        self.gnupg_manager.logger.info.assert_called_with("Removing file '{}'.".format(
            mock_input_file))


class GnupgManagerDecryptDecompressFileTestCase(unittest.TestCase):
    """Class for testing decrypt_decompress_file() method from GnupgManager class."""

    def setUp(self):
        """Set up the test variables."""
        self.gnupg_manager = get_gnupg_manager()

    @mock.patch(MOCK_PACKAGE + 'GnupgManager.decrypt_file')
    def test_decrypt_decompress_file_decryption_failure_exception(self, mock_gpg_decrypt_file):
        """Test when there is an error during the decryption."""
        mock_decrypt_exception_msg = "Mock decryption exception error."
        mock_gpg_decrypt_file.side_effect = Exception(mock_decrypt_exception_msg)

        with self.assertRaises(Exception) as cex:
            self.gnupg_manager.decrypt_decompress_file('')

        self.assertEqual(mock_decrypt_exception_msg, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'decompress_file')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager.decrypt_file')
    def test_decrypt_decompress_file_decompression_failure_exception(
            self, mock_gpg_decrypt_file, mock_decompress_file):
        """Test when there is an error during the decompression."""
        mock_gpg_decrypt_file.return_value = ''

        mock_decompression_exception_msg = "Mock decompression exception error."
        mock_decompress_file.side_effect = Exception(mock_decompression_exception_msg)

        with self.assertRaises(Exception) as cex:
            self.gnupg_manager.decrypt_decompress_file('')

        self.assertEqual(mock_decompression_exception_msg, cex.exception.message)

    @mock.patch(MOCK_PACKAGE + 'decompress_file')
    @mock.patch(MOCK_PACKAGE + 'GnupgManager.decrypt_file')
    def test_decrypt_decompress_file_success_case(
            self, mock_gpg_decrypt_file, mock_decompress_file):
        """Test to check the file was decrypted and decompressed successfully."""
        mock_gpg_decrypt_file.return_value = MOCK_COMPRESSED_FILE
        mock_decompress_file.return_value = MOCK_OUTPUT_PATH

        processed_file_path = self.gnupg_manager.decrypt_decompress_file(
            MOCK_COMPRESSED_ENCRYPTED_FILE)

        self.assertEqual(MOCK_OUTPUT_PATH, processed_file_path)

        self.gnupg_manager.logger.info.assert_called_with("Decompressing file {}.".format(
            MOCK_COMPRESSED_FILE))


class GnupgManagerDecryptDecompressFileListTestCase(unittest.TestCase):
    """Class for testing decrypt_decompress_file_list() method from GnupgManager class."""

    def setUp(self):
        """Set up the test variables."""
        self.gnupg_manager = get_gnupg_manager()

    @mock.patch(MOCK_IS_DIR)
    def test_decrypt_decompress_file_list_path_not_exists(self, mock_is_dir):
        """Test to check the raise of exception if source_dir path does not exist."""
        mock_is_dir.return_value = False
        expected_error_msg = "Path informed is not a valid existent folder."

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.decrypt_decompress_file_list(MOCK_SOURCE_DIR, MOCK_NUMBER_THREADS)

        self.assertIn(expected_error_msg, raised.exception.message)

    @mock.patch(MOCK_IS_DIR)
    def test_decrypt_decompress_file_list_path_is_not_dir(self, mock_is_dir):
        """Test to check the raise of exception if source_dir path does not exist."""
        mock_is_dir.return_value = False

        with self.assertRaises(GnupgException) as raised:
            self.gnupg_manager.decrypt_decompress_file_list(MOCK_SOURCE_DIR, MOCK_NUMBER_THREADS)

        self.assertIn("Path informed is not a valid existent folder.", raised.exception.message)

    @mock.patch(MOCK_PACKAGE + 'ThreadPool')
    @mock.patch(MOCK_PACKAGE + 'os')
    @mock.patch(MOCK_IS_DIR)
    def test_decrypt_decompress_file_list_success_case(self, mock_is_dir, mock_os,
                                                       mock_thread_pool):
        """Test when the list of files were successfully processed by the pool."""
        mock_is_dir.return_value = True
        mock_file_list = ['file0', 'file1', 'file2']
        mock_os.listdir.return_value = mock_file_list
        mock_thread_pool.create_thread.return_value = None
        mock_os.path.join.side_effect = ['mock_path/file0', 'mock_path/file1', 'mock_path/file2']
        mock_create_thread_calls = []

        for file_name in mock_file_list:
            source_file_path = "{}/{}".format(MOCK_SOURCE_DIR, file_name)

            mock_create_thread_calls.append(mock.call().create_thread("{}-Thread".format(
                file_name), self.gnupg_manager.decrypt_decompress_file, source_file_path))

        decrypt_decompress_result = self.gnupg_manager.decrypt_decompress_file_list(
            MOCK_SOURCE_DIR, MOCK_NUMBER_THREADS)

        self.assertTrue(decrypt_decompress_result)

        mock_thread_pool.assert_has_calls(mock_create_thread_calls)


class GnupgManagerOnFileProcessedTestCase(unittest.TestCase):
    """Class for testing on_file_processed() method from GnupgManager class."""

    def setUp(self):
        """Set up the test variables."""
        self.gnupg_manager = get_gnupg_manager()

    def test_on_file_processed_error_message(self):
        """Test to check the return value if error_message is not empty."""
        mock_thread_output = ['mock_thread_name', 'mock_elapsed_time', 'mock_result',
                              'mock_error_message']

        on_file_processed_result = self.gnupg_manager.on_file_processed(mock_thread_output, [])
        self.assertFalse(on_file_processed_result)

    def test_on_file_processed_no_error_message(self):
        """Test to check the return value if error_message is not empty."""
        mock_thread_output = ['mock_thread_name', 'mock_elapsed_time', 'mock_result',
                              None]
        on_file_processed_result = self.gnupg_manager.on_file_processed(mock_thread_output, [])
        self.assertTrue(on_file_processed_result)
