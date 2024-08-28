##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=broad-except

"""Physical creation of files and folders in a filesystem layout."""

import datetime
import hashlib
import json
import os

from tests.system.config.props import ITEM_GPG_USER_EMAIL_VAL, ITEM_GPG_USER_NAME_VAL
from tests.system.scenario_simulator.constants import BACKUP_VOL_FILE_NAME, BINARY_FILE_TYPE_KEY, \
    DIRECTORY_OWNER_ACCESS, FILE_BLOCK_SIZE, FILE_DESCRIPTOR_BACKUP_ID, \
    FILE_DESCRIPTOR_CUSTOMER_ID, FILE_DESCRIPTOR_FILE_CONTENT, FILE_DESCRIPTOR_FILE_NAME, \
    FILE_DESCRIPTOR_FILE_PATH, FILE_DESCRIPTOR_FILE_SIZE, FILE_DESCRIPTOR_FILE_TYPE, \
    FILE_DESCRIPTOR_VOL_ID, METADATA_BACKUP_DESC_KEY, METADATA_BACKUP_ID_KEY, \
    METADATA_BACKUP_NAME_KEY, METADATA_CREATED_AT, METADATA_DESC_VALUE, METADATA_FILE_TYPE_KEY, \
    METADATA_OBJECTS_COMPRESSION, METADATA_OBJECTS_KEY, METADATA_OBJECTS_LENGTH, \
    METADATA_OBJECTS_MD5, METADATA_OBJECTS_OFFSET, METADATA_PARENT_ID_KEY, \
    METADATA_PARENT_ID_VALUE, METADATA_VERSION_KEY, METADATA_VERSION_VALUE, METADATA_VOL_ID_KEY, \
    METADATA_VOL_KEY, METADATA_VOL_VALUE, SYSTEM_TEST_LOGGER, TEXT_FILE_TYPE_KEY

from backup.gnupg_manager import GnupgManager
from backup.utils.compress import compress_file
from backup.utils.fsys import remove_path


def mk_dirs(base_directory, directory_layout):
    """
    Create folder structure based on a layout.

    :param base_directory: the place the filesystem layout resides in.
    :param directory_layout: filesystem layout structure information for simulation.
    :return: create filesystem layout structure.
    """
    if not os.path.exists(base_directory):
        try:
            os.makedirs(base_directory, DIRECTORY_OWNER_ACCESS)
        except OSError:
            return False

    for item in directory_layout:
        path = os.path.join(base_directory, item)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError:
                return False
    return True


def mk_files(base_path, required_files):
    """
    Create files according to given the layout structure.

    :param base_path: filesystem layout simulation base location.
    :param required_files : list of filename that is required to be created.
    :return: create files needed in the provided layout.
    """
    base_path = os.path.normpath(base_path)

    file_gen_mapper = {
        TEXT_FILE_TYPE_KEY: create_text_file,
        BINARY_FILE_TYPE_KEY: create_binary_file,
        METADATA_FILE_TYPE_KEY: create_metadata_file
    }

    for item in required_files:
        file_path = os.path.join(base_path, item[FILE_DESCRIPTOR_FILE_PATH])

        file_type = item[FILE_DESCRIPTOR_FILE_TYPE]

        try:
            file_gen_mapper[file_type](file_path, item)
        except Exception as env_exp:
            print("Error creating the environment: {}.".format(env_exp))


def create_binary_file(path, descriptor):
    """
    Create a binary file based on the given descriptor.

    :param path: path to create a binary file.
    :param descriptor: details of a required binary file.
    """
    filename = descriptor[FILE_DESCRIPTOR_FILE_NAME]
    file_size = descriptor[FILE_DESCRIPTOR_FILE_SIZE]
    file_content = descriptor[FILE_DESCRIPTOR_FILE_CONTENT]

    if not isinstance(file_content, str):
        raise TypeError("Invalid content type given")

    path = os.path.join(path, filename)

    with open(path, 'wb') as fopen:
        fopen.write(os.urandom(file_size))


def create_text_file(path, descriptor):
    """
    Create a text file based on the given descriptor.

    :param path: path to create a text file.
    :param descriptor: details of a required text file.
    """
    filename = descriptor[FILE_DESCRIPTOR_FILE_NAME]
    file_content = descriptor[FILE_DESCRIPTOR_FILE_CONTENT]

    if not isinstance(file_content, str):
        raise TypeError("Invalid content type given")

    path = os.path.join(path, filename)

    with open(path, "w") as fopen:
        fopen.write(file_content)


def get_file_md5(filename):
    """
    Md5 calculation of a file.

    :param filename: name of the file to calculate md5.
    :return: calculated md5 for the given file.
    """
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as fopen:
        for chunk in iter(lambda: fopen.read(FILE_BLOCK_SIZE), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def get_file_info_in_path(path):
    """
    Construct the objects item of a metadata.

    :param path: file parent's folder.
    :return: files details in the given path in a list.
    """
    files_info = []

    for item in os.listdir(path):
        filename = os.path.join(path, item)
        if os.path.isfile(filename) and (BACKUP_VOL_FILE_NAME in item):
            files_info.append({item: {
                METADATA_OBJECTS_LENGTH: os.stat(filename).st_size,
                METADATA_OBJECTS_OFFSET: 0,
                METADATA_OBJECTS_COMPRESSION: 'none',
                METADATA_OBJECTS_MD5: get_file_md5(filename)
            }})

    return files_info


def create_metadata_file(path, item):
    """
    Create metadata file descriptor inside a backup folder.

    :param path: metadata parent folder.
    :param item: metadata dictionary including file details.
    """
    now_iso_format = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    meta_backup_name = 'customer_deployment_{}_Backup_{}'. \
        format(item[FILE_DESCRIPTOR_CUSTOMER_ID],
               item[FILE_DESCRIPTOR_BACKUP_ID])

    metadata = {
        METADATA_BACKUP_ID_KEY: item[METADATA_BACKUP_ID_KEY],
        METADATA_VERSION_KEY: METADATA_VERSION_VALUE,
        METADATA_CREATED_AT: now_iso_format,
        METADATA_BACKUP_DESC_KEY: METADATA_DESC_VALUE,
        METADATA_PARENT_ID_KEY: METADATA_PARENT_ID_VALUE,
        METADATA_BACKUP_NAME_KEY: meta_backup_name,
        METADATA_VOL_KEY: METADATA_VOL_VALUE,
        METADATA_VOL_ID_KEY: item[FILE_DESCRIPTOR_VOL_ID],
        METADATA_OBJECTS_KEY: get_file_info_in_path(path)
    }

    metadata = json.dumps(metadata)
    item[FILE_DESCRIPTOR_FILE_CONTENT] = metadata
    create_text_file(path, item)


def process_path_list(root_path, path_list):
    """
    Process the list of paths according to the supported operations: encryption and/or archiving.

    :param root_path: directory where the mock environment is stored.
    :param path_list: list of paths to be processed.
    """
    if not path_list:
        return

    for mock_env_relative_path in path_list:
        try:
            extension_list = get_extension_list_from_path(mock_env_relative_path)

            if not extension_list:
                continue

            full_path = strip_extensions_from_path(os.path.join(root_path, mock_env_relative_path))

            for extension in extension_list:
                if extension == 'tar':
                    full_path = compress(full_path)
                elif extension == 'gpg':
                    full_path = compress_encrypt(full_path)
                else:
                    continue

        except Exception as compress_exp:
            print("Error processing the layout: {}.".format(compress_exp))


def get_extension_list_from_path(path=""):
    """
    Return the extension list of the path.

    :param path: path to be checked.
    :return: list of extensions after the basename of the path.
    """
    if not path.strip():
        return []

    path = os.path.normpath(path)

    return os.path.basename(path).split('.')[1:]


def strip_extensions_from_path(path):
    """
    Remove extensions from path and rename the file in the system.

    :param path: path to be renamed.
    :return: renamed full path.
    """
    if not path.strip():
        return path

    root_path = os.path.dirname(path)

    raw_file_name = os.path.basename(path).split('.')[0]

    renamed_file_path = os.path.join(root_path, raw_file_name)

    os.rename(path, renamed_file_path)

    return renamed_file_path


def compress(path):
    """
    Compress the informed path if it is a file or archive it if it is a folder.

    :param path: path to be archived.
    :return: archived file path.
    :raise Exception: if the original file could not be removed.
    """
    original_path = path

    compress_mode = "w:gz"
    if os.path.isdir(path):
        compress_mode = "w"

    path = compress_file(path, None, compress_mode)

    if not remove_path(original_path):
        raise Exception("Could not remove path: {}".format(original_path))

    return path


def compress_encrypt(path):
    """
    Compress and encrypt the content of the path using GnupgManager.

    If the path is a directory, process and remove the original files inside it and return the
    folder's name.

    If it is a file, process and remove the original file and return the encrypted file name.

    :param path: path to be encrypted.
    :return: original folder's name if the path is a folder, or the encrypted file name, otherwise.
    :raise Exception: if the temporary files could not be removed.
    """
    is_dir = os.path.isdir(path)

    file_list = [path]
    if is_dir:
        file_list = [os.path.join(path, file_name) for file_name in os.listdir(path)
                     if not os.path.isdir(os.path.join(path, file_name))]

    if not file_list:
        return path

    gpg_manager = GnupgManager(ITEM_GPG_USER_NAME_VAL, ITEM_GPG_USER_EMAIL_VAL, SYSTEM_TEST_LOGGER)

    encrypted_file_path = ""

    for file_path in file_list:
        root_path = os.path.dirname(file_path)

        compressed_file_path = compress(file_path)

        if not remove_path(file_path):
            raise Exception("Could not remove path: {}".format(file_path))

        encrypted_file_name = gpg_manager.encrypt_file(compressed_file_path, root_path)

        if not remove_path(compressed_file_path):
            raise Exception("Could not remove path: {}".format(file_path))

        encrypted_file_path = os.path.join(root_path, encrypted_file_name)

    if is_dir:
        return path

    return encrypted_file_path
