##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=unused-argument

"""Module to handle gnupg functions."""

import os
from subprocess import PIPE, Popen

from gnupg import GPG

from backup.constants import GPG_SUFFIX, PLATFORM_NAME
from backup.exceptions import ExceptionCodes, GnupgException
from backup.logger import CustomLogger
from backup.thread_pool import THREAD_OUTPUT_INDEX, ThreadPool
from backup.utils.compress import compress_file, decompress_file
from backup.utils.decorator import timeit
from backup.utils.fsys import get_current_user, get_home_dir, is_dir, is_valid_path, remove_path
from backup.utils.validator import check_not_empty

GPG_KEY_PATH = os.path.join(get_home_dir(), ".gnupg")

GPG_KEY_CREATED_STR = 'KEY_CREATED'
GPG_ERROR_READING_KEY_STR = "error reading key"

GPG_KEY_LENGTH = 1024
GPG_KEY_TYPE = 'RSA'
GPG_CIPHER_ALG = 'AES256'
GPG_COMPRESS_ALG = 'none'
GPG_PERMISSION_DENIED = "permission denied"
GPG_ENCRYPTED_FILE_ENDS_WITH = ".{}".format(GPG_SUFFIX)

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]


class GnupgManager:
    """Class used to store sourced information about gnupg current settings."""

    def __init__(self, gpg_user_name, gpg_user_email, logger, gpg_key_path=GPG_KEY_PATH):
        """
        Initialize GPG Manager class setting gnupg handler according to the underlying platform.

        :param gpg_user_name: gpg configured user name.
        :param gpg_user_email: gpg configured email.
        :param logger: logger object.
        :param gpg_key_path: gpg key path, usually is ~/.gnupg.
        :raise GnupgException: if gnupg is not supported by the system.
        """
        self.gpg_user_name = gpg_user_name
        self.gpg_user_email = gpg_user_email
        self.gpg_key_path = gpg_key_path

        self.logger = CustomLogger(SCRIPT_FILE, logger.log_root_path, logger.log_file_name,
                                   logger.log_level)

        if 'linux' in PLATFORM_NAME:
            self.gpg_cmd = 'gpg'
            self.gpg_handler = GPG(homedir=self.gpg_key_path)
        elif 'sun' in PLATFORM_NAME:
            self.gpg_cmd = 'gpg2'
            self.gpg_handler = GPG(self.gpg_cmd, gnupghome=self.gpg_key_path)
        else:
            raise GnupgException(ExceptionCodes.PlatformNotSupportedForGPG, PLATFORM_NAME)

        self.validate_encryption_key()

    def validate_encryption_key(self):
        """
        Check the system for the encryption key.

        Create a new key if there is no one for the informed user.

        :return: true if the key already exists or if a new one was created.
        :raise GnupgException: if gnupg keys could not be created properly.
        """
        self.logger.info("Validating GPG encryption key.")

        _, stderr = Popen([self.gpg_cmd, "--list-keys", self.gpg_user_email], stdout=PIPE,
                          stderr=PIPE).communicate()

        get_key_err = stderr.strip().lower()

        if GPG_ERROR_READING_KEY_STR in get_key_err:
            self.logger.warning("GPG key not found in the system.")

            if not self.create_gpg_key():
                raise GnupgException(ExceptionCodes.CannotCreateGPGKey)

            self.logger.warning("GPG key was created successfully.")
            return True

        if GPG_PERMISSION_DENIED in get_key_err:
            raise Exception(
                "Error retrieving GPG keys. Check if the current user '{}' has permission to "
                "access '{}'".format(get_current_user(), self.gpg_key_path))

        self.logger.info("Backup key already exists.")

        return True

    def create_gpg_key(self):
        """
        Create a new GPG key in the system.

        :return: true if key was created, false otherwise.
        """
        self.logger.warning("Creating GPG key for '{}'.".format(self.gpg_user_email))

        gpg_key = self.gpg_handler.gen_key_input(key_type=GPG_KEY_TYPE, key_length=GPG_KEY_LENGTH,
                                                 name_real=self.gpg_user_name,
                                                 name_email=self.gpg_user_email)

        gen_key_ret = self.gpg_handler.gen_key(gpg_key)

        if GPG_KEY_CREATED_STR in gen_key_ret.stderr:
            return True

        return False

    @timeit
    def encrypt_file(self, file_path, output_path, **kwargs):
        """
        Encrypt a file using the gpg strategy.

        :param file_path: file path to be encrypted.
        :param output_path: path where the encrypted file will be stored.
        :return: encrypted file name ending with .gpg suffix.
        :raise GnupgException: if an error happened during the encryption process.
        """
        check_not_empty(output_path)
        is_valid_path(file_path)

        self.logger.info("Encrypting file '{}'".format(file_path))

        with open(os.devnull, "w") as devnull:
            output = "{}{}".format(os.path.join(output_path, os.path.basename(file_path)),
                                   GPG_ENCRYPTED_FILE_ENDS_WITH)

            try:
                ret_code = Popen([self.gpg_cmd, "--output", output, "-r", self.gpg_user_email,
                                  "--cipher-algo", GPG_CIPHER_ALG, "--compress-algo",
                                  GPG_COMPRESS_ALG, "--encrypt", file_path], stdout=devnull,
                                 stderr=devnull).wait()
                if ret_code != 0:
                    raise GnupgException(ExceptionCodes.EncryptError, file_path)
            except (TypeError, ValueError) as error:
                raise GnupgException(ExceptionCodes.EncryptError, error)

        return output

    def compress_encrypt_file(self, file_path, output_path):
        """
        Compress and encrypt a file using gpg and gz strategies.

        :param file_path: file path to be encrypted and compressed.
        :param output_path: path where the encrypted and compressed file will be stored.
        :return: path of the processed file.
        :raise GnupgException: if an error happened during the process.
        """
        self.logger.info("Compressing file {}.".format(file_path))

        file_compression_time = []
        compressed_file_path = compress_file(file_path, output_path,
                                             get_elapsed_time=file_compression_time)

        if file_compression_time:
            self.logger.log_time("Elapsed time to compress file '{}'".format(file_path),
                                 file_compression_time[0])

        file_encryption_time = []
        encrypted_file_path = self.encrypt_file(compressed_file_path, output_path,
                                                get_elapsed_time=file_encryption_time)

        if file_encryption_time:
            self.logger.log_time("Elapsed time to encrypt file '{}'".format(compressed_file_path),
                                 file_encryption_time[0])

        if not remove_path(compressed_file_path):
            raise GnupgException(ExceptionCodes.CannotRemoveFile, compressed_file_path)

        return encrypted_file_path

    @timeit
    def compress_encrypt_file_list(self, source_dir, output_path, number_threads, **kwargs):
        """
        Compress and encrypt a list of files in parallel using a thread pool.

        :param source_dir: folder where the files to be encrypted are located.
        :param output_path: folder to store encrypted files.
        :param number_threads: number of threads to process the source dir.
        :return: true if success.
        :raise GnupgException: if an error happened during the process.
        """
        if not is_dir(source_dir):
            raise GnupgException(ExceptionCodes.InvalidFolder, source_dir)

        is_valid_path(output_path)

        job_error_list = []
        job_thread_pool = ThreadPool(self.logger, number_threads, GnupgManager.on_file_processed,
                                     job_error_list)

        for file_name in os.listdir(source_dir):
            source_file_path = os.path.join(source_dir, file_name)

            job_thread_pool.create_thread("{}-Thread".format(file_name), self.compress_encrypt_file,
                                          source_file_path, output_path)
        job_thread_pool.start_pool()

        if job_error_list:
            raise GnupgException(parameters=job_error_list)

        return True

    @timeit
    def decrypt_file(self, encrypted_file_path, remove_encrypted=False, **kwargs):
        """
        Decrypt a file using the gpg strategy.

        :param encrypted_file_path: file to be decrypted in the format <file_name>.gpg.
        :param remove_encrypted: whether the encrypted file should be deleted after decryption.
        :return: decrypted file name.
        :raise Exception: if an error happened during the process.
        """
        if is_valid_path(encrypted_file_path):
            if GPG_ENCRYPTED_FILE_ENDS_WITH not in encrypted_file_path:
                raise GnupgException(ExceptionCodes.InvalidGPGFile, encrypted_file_path)

        if is_dir(encrypted_file_path):
            raise GnupgException(ExceptionCodes.InvalidFile, encrypted_file_path)

        self.logger.info("Decrypting file {}.".format(encrypted_file_path))

        dec_filename = \
            encrypted_file_path[0:len(encrypted_file_path) - len(GPG_ENCRYPTED_FILE_ENDS_WITH)]

        with open(os.devnull, "w") as devnull:
            ret_code = Popen([self.gpg_cmd, "--output", dec_filename, "--decrypt",
                              encrypted_file_path], stdout=devnull, stderr=devnull).wait()
            if ret_code != 0:
                raise GnupgException(ExceptionCodes.DecryptError, encrypted_file_path)

        if remove_encrypted:
            self.logger.info("Removing file '{}'.".format(encrypted_file_path))
            if not remove_path(encrypted_file_path):
                raise GnupgException(ExceptionCodes.CannotRemoveFile, encrypted_file_path)

        return dec_filename

    def decrypt_decompress_file(self, file_path):
        """
        Decrypt and decompress a file using gpg and gz strategies.

        :param file_path: file path to be decompressed and decrypted.
        :return: path of the processed file.
        :raise Exception: if an error happened during the process.
        """
        file_decryption_time = []
        decrypted_file_name = self.decrypt_file(file_path, True,
                                                get_elapsed_time=file_decryption_time)

        if file_decryption_time:
            self.logger.log_time("Elapsed time to decrypt file '{}'".format(file_path),
                                 file_decryption_time[0])

        self.logger.info("Decompressing file {}.".format(decrypted_file_name))

        file_decompression_time = []
        decompressed_file_path = decompress_file(decrypted_file_name, os.path.dirname(
            decrypted_file_name), True, get_elapsed_time=file_decompression_time)

        if file_decompression_time:
            self.logger.log_time("Elapsed time to decompress file '{}'".format(decrypted_file_name),
                                 file_decompression_time[0])

        return decompressed_file_path

    @timeit
    def decrypt_decompress_file_list(self, source_dir, number_threads, **kwargs):
        """
        Decrypt and decompress a list of files in parallel using a thread pool.

        :param source_dir: folder where the files to be encrypted are located.
        :param number_threads: number of threads to process the source dir.
        :return: true if success.
        :raise Exception: if an error happened during the process.
        """
        if not is_dir(source_dir):
            raise GnupgException(ExceptionCodes.InvalidFolder, source_dir)

        job_error_list = []
        decryption_thread_pool = ThreadPool(self.logger, number_threads,
                                            GnupgManager.on_file_processed, job_error_list)

        for file_name in os.listdir(source_dir):
            source_file_path = os.path.join(source_dir, file_name)

            decryption_thread_pool.create_thread("{}-Thread".format(file_name),
                                                 self.decrypt_decompress_file, source_file_path)
        decryption_thread_pool.start_pool()

        if job_error_list:
            raise GnupgException(parameters=job_error_list)

        return True

    @staticmethod
    def on_file_processed(thread_output, job_error_list):
        """
        Execute Callback function after a successful file encryption/decryption.

        :param thread_output: thread output after processing the file [thread name, elapsed time].
        :param job_error_list: list to keep track of each thread error.
        :return: false, if an error was found; true otherwise.
        """
        error_message = thread_output[THREAD_OUTPUT_INDEX.TH_ERROR.value - 1]
        if error_message is not None:
            job_error_list.append(error_message)

            return False

        return True

    def __str__(self):
        """Represent GnupgManager object as string."""
        return "({}, {}, {})".format(self.gpg_user_name, self.gpg_user_email, self.gpg_key_path)

    def __repr__(self):
        """Represent GnupgManager object."""
        return self.__str__()
