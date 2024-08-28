##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""The purpose of this module is to provide unit testing for utils.compress.py script."""

import binascii
import os
import shutil
from subprocess import PIPE, Popen
import unittest

import mock

import backup.utils.compress as ucompress
import backup.utils.fsys as fsys

SCRIPT_PATH = os.path.dirname(__file__)
FILE_NAME = "volume_file"
DEFAULT_FILE_SIZE = 100 * 1024
TMP_DIR = os.path.join(SCRIPT_PATH, "temp_dir")
MOCK_BASE_PACKAGE = 'backup.utils.compress'


class UtilsCompressTestCase(unittest.TestCase):
    """Test Cases for compress utility methods located in utils.compress.py."""

    def setUp(self):
        """Create testing scenario."""
        self.test_file_path = os.path.join(SCRIPT_PATH, FILE_NAME)
        self.compressed_file = self.test_file_path + ".gz"
        self.tar_file = self.compressed_file + ".tar"
        self.test_dir = os.path.dirname(self.test_file_path)
        self.extract_destination_dir = os.path.join(os.path.dirname(__file__), 'extract_dir')

        if not os.path.exists(self.test_file_path):
            with open(self.test_file_path, 'wb') as file_path:
                file_path.write(os.urandom(DEFAULT_FILE_SIZE))

    def tearDown(self):
        """Tear down created scenario."""
        fsys.remove_path(self.test_file_path)
        fsys.remove_path(self.compressed_file)
        fsys.remove_path(self.tar_file)
        shutil.rmtree(self.extract_destination_dir, ignore_errors=True)

    def test_compress_file_is_gzip_compressed_cross_platform(self):
        """Test if file is gzip compressed in cross_platform."""
        ucompress.compress_file(self.test_file_path)
        with open(self.compressed_file, 'rb') as test_f:
            self.assertEqual(b'1f8b', binascii.hexlify(test_f.read(2)))

    @mock.patch.object(ucompress, 'gzip_file')
    def test_gzip_file_function_is_being_called(self, mock_gzip_file):
        """
        Test if compress file function is being called.

        :param mock_gzip_file: mocking gzip_file method
        """
        ucompress.compress_file(self.test_file_path)
        self.assertEqual(1, mock_gzip_file.call_count)

    @mock.patch.object(ucompress, 'tar_file')
    def test_tar_file_function_is_being_called(self, mock_tar_file):
        """
        Test if compress file function is being called.

        :param mock_tar_file: mocking tar_file method
        """
        ucompress.compress_file(self.test_file_path, None, "w")
        self.assertEqual(1, mock_tar_file.call_count)

    def test_compress_file_files_inside_compressed_volume_are_not_corrupted(self):
        """Test if files inside compressed volume are not corrupted."""
        ucompress.compress_file(self.test_file_path)
        ucompress.compress_file(self.compressed_file, None, "w")
        ucompress.remove_path(self.compressed_file)
        ucompress.remove_path(self.test_file_path)

        ret = Popen(['tar', '-C', self.test_dir, '-xf', self.tar_file], stdout=PIPE,
                    stderr=PIPE).wait()
        self.assertEqual(0, ret)

        ret = Popen(['gunzip', self.compressed_file], stdout=PIPE, stderr=PIPE).wait()
        self.assertEqual(0, ret)

    def test_compress_file_gzip_file_is_not_corrupted(self):
        """Test gzip file is not corrupted."""
        ucompress.compress_file(self.test_file_path)
        gzip_process = Popen(['gunzip', '-t', self.compressed_file], stdout=PIPE, stderr=PIPE)
        out, err = gzip_process.communicate()
        exitcode = gzip_process.returncode
        self.assertEqual('', err)
        self.assertEqual("", out.strip())
        self.assertEqual(0, exitcode)

    def test_compress_file_invalid_source_path_is_provided(self):
        """Test if exception is raised when invalid source path is provided."""
        expected_exception_message = "Path informed is not a valid formatted folder or file."
        with self.assertRaises(Exception) as raised:
            ucompress.compress_file(TMP_DIR)

        self.assertIn(expected_exception_message, raised.exception.message)

    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'is_gzip_file']))
    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'is_tar_file']))
    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'gunzip_file']))
    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'os', 'path', 'exists']))
    def test_decompress_file_should_succeed(self,
                                            mock_os_path_exists,
                                            mock_gunzip_file,
                                            mock_is_tar_file,
                                            mock_is_gzip_file):
        """Test scenario should pass without a problem with descent parameters."""
        mock_os_path_exists.return_value = True
        mock_is_tar_file.return_value = False
        mock_is_gzip_file.return_value = True
        test_compressed_file = self.test_file_path + ".gz"
        mock_gunzip_file.return_value = test_compressed_file
        sut_decompressed_file_path = ucompress.decompress_file(self.compressed_file, self.test_dir)
        self.assertIsNotNone(sut_decompressed_file_path)

    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'is_gzip_file']))
    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'is_tar_file']))
    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'os', 'path', 'exists']))
    @mock.patch.object(ucompress, 'gunzip_file')
    def test_decompress_file_should_call_gzip(self, mock_gunzip_file,
                                              mock_os_path_exists,
                                              mock_is_tar_file,
                                              mock_is_gzip_file):
        """
        For gz file gunzip_file should be called.

        :param mocking gunzip_file function
        """
        mock_os_path_exists.return_value = True
        mock_is_tar_file.return_value = False
        mock_is_gzip_file.return_value = True
        test_compressed_file = self.test_file_path + ".gz"
        mock_gunzip_file.return_value = test_compressed_file
        sut_decompressed_file_path = ucompress.decompress_file(self.compressed_file, self.test_dir)
        self.assertEqual(1, mock_gunzip_file.call_count)
        self.assertIsNotNone(sut_decompressed_file_path)

    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'is_gzip_file']))
    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'is_tar_file']))
    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'os', 'path', 'exists']))
    @mock.patch.object(ucompress, 'untar_file')
    def test_decompress_file_should_call_untar(self, mock_untar_file,
                                               mock_os_path_exists,
                                               mock_is_tar_file,
                                               mock_is_gzip_file):
        """
        For gz file gunzip_file should be called.

        :param mocking gunzip_file function
        """
        mock_os_path_exists.return_value = True
        mock_is_tar_file.return_value = True
        mock_is_gzip_file.return_value = False
        test_compressed_file = self.test_file_path + ".gz"
        sut_decompressed_file_path = ucompress.decompress_file(test_compressed_file, self.test_dir)
        self.assertEqual(1, mock_untar_file.call_count)
        self.assertIsNotNone(sut_decompressed_file_path)

    @mock.patch('.'.join([MOCK_BASE_PACKAGE, 'os', 'path', 'exists']))
    def test_decompress_file_invalid_source_path_is_provided(self, mock_os_path_exists):
        """Test if exception is raised when invalid source path is provided."""
        mock_os_path_exists.return_value = False
        expected_exception_message = "Path informed is not a valid formatted folder or file."
        with self.assertRaises(Exception) as raised:
            ucompress.compress_file(TMP_DIR)

        self.assertIn(expected_exception_message, raised.exception.message)

    def test_decompress_file_invalid_decompressed_file(self):
        """Test if raises exception on invalid decompressed file."""
        with self.assertRaises(Exception):
            ucompress.decompress_file(__file__, self.extract_destination_dir)
