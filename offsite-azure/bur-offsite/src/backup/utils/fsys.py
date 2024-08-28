##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module is for adding any utilities related to the filesystem."""

import os
import pickle
import pwd
import shutil
from subprocess import PIPE, Popen

from backup.constants import BLOCK_SIZE_GB, BLOCK_SIZE_GB_STR, BLOCK_SIZE_MB, BLOCK_SIZE_MB_STR, \
    DF_COMMAND_AVAILABLE_SPACE_INDEX
from backup.exceptions import ExceptionCodes, UtilsException
from backup.utils.validator import check_not_empty


def remove_path(path):
    """
    Delete a path from local storage.

    :param path: file name to be removed.
    :return: true if path does not exist or was successfully deleted; false otherwise.
    """
    if not os.path.exists(path):
        return True

    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    except OSError:
        return False

    return True


def create_path(path):
    """
    Create a path in the local storage.

    :param path: path to be created.
    :return: true if path already exists or was successfully created; false otherwise.
    """
    if os.path.exists(path):
        return True

    try:
        os.makedirs(path)
    except OSError:
        return False

    return True


def get_home_dir():
    """
    Get home directory for the current user.

    :return: home directory.
    """
    return os.path.expanduser("~")


def get_path_to_docs():
    """
    Get documents directory for the current user.

    :return: documents directory.
    """
    return os.path.join(get_home_dir(), "Documents")


def is_dir(root_path):
    """
    Check whether the informed path is a directory or not.

    :param root_path: string path.
    :return: true, if path exists and is a directory; false otherwise.
    """
    if not os.path.exists(root_path):
        return False

    if not os.path.isdir(root_path):
        return False

    return True


def split_folder_list(folder_list_string=""):
    r"""
    Split a string of paths separated by \\n returned from an ls command.

    :param folder_list_string: list of path in string format separated by \\n.
    :return: parsed list of path.
    """
    folder_list = []
    for folder_path in folder_list_string.split('\n'):
        folder_path = folder_path.strip()

        if not folder_path or folder_path == '.':
            continue

        # Removing last slash to avoid errors while handling this path.
        if folder_path[len(folder_path) - 1] == '/':
            folder_path = folder_path[0:len(folder_path) - 1]

        folder_list.append(folder_path)

    return folder_list


def get_existing_root_path(folder_path):
    """
    Get the first existing path in the informed file tree.

    :param folder_path: path to be verified.
    :return: first existing path after splitting.
    :raise UtilsException: if the folder_path param is invalid or doesn't exist.
    """
    if check_not_empty(folder_path):
        if not (os.path.isdir(folder_path) or str(folder_path)[0] == '.' or os.path.isabs(
                folder_path)):
            raise UtilsException(ExceptionCodes.InvalidPath, folder_path)

    normalized_folder_path = os.path.normpath(folder_path.strip())
    folder_path = normalized_folder_path

    while not os.path.exists(folder_path):
        if folder_path:
            folder_path, _ = os.path.split(folder_path)
            continue

        raise UtilsException(ExceptionCodes.InvalidPath, normalized_folder_path)

    return folder_path


def get_free_disk_space(folder_path):
    """
    Get free space in the informed path.

    :param folder_path: the full path on disk.
    :return: free disk space in the informed path in MB.
    :raise UtilsException: if the process isn't concluded or has any errors.
    """
    folder_path = get_existing_root_path(folder_path)

    try:
        get_disk_space_process = Popen(["df", "-k", folder_path], stdout=PIPE)
        if get_disk_space_process.stderr:
            raise UtilsException(parameters=get_disk_space_process.stderr)
    except (TypeError, ValueError) as error:
        raise UtilsException(parameters=error)

    try:
        # ignore header line
        disk_space_output = []
        for line in get_disk_space_process.stdout.readlines():
            disk_space_output = line.split()

        free_disk_space = int(disk_space_output[DF_COMMAND_AVAILABLE_SPACE_INDEX])
        free_disk_space_mb = free_disk_space / BLOCK_SIZE_MB

        return free_disk_space_mb

    except (IndexError, AttributeError) as error:
        raise UtilsException(parameters=error)


def get_size_on_disk(content_path):
    """
    Get the size on disk of the informed content path.

    :param content_path: the full path on disk.
    :return: size of the informed path.
    :raise UtilsException: if the process isn't concluded or has any errors.
    """
    is_valid_path(content_path)

    try:
        get_size_process = Popen(["du", "-sm", content_path.strip()], stdout=PIPE)
        if get_size_process.stderr:
            raise UtilsException(parameters=get_size_process.stderr)
    except (TypeError, ValueError) as error:
        raise UtilsException(parameters=error)

    try:
        # ignore header line
        disk_space_output = []
        for line in get_size_process.stdout.readlines():
            disk_space_output = line.split()

        content_size = int(disk_space_output[0])

        return content_size

    except (IndexError, AttributeError) as error:
        raise UtilsException(parameters=error)


def get_formatted_size_on_disk(file_or_dir_path):
    """
    Get the formatted size on disk of the informed path.

    :param file_or_dir_path: directory to calculate the size.
    :return: string with the calculated size.
    """
    try:
        block_size = BLOCK_SIZE_MB_STR

        content_size = get_size_on_disk(file_or_dir_path)

        if content_size >= BLOCK_SIZE_GB:
            content_size = content_size / BLOCK_SIZE_GB
            block_size = BLOCK_SIZE_GB_STR

        return "{}{}".format(content_size, block_size)

    except UtilsException:
        return ""


def get_folder_file_lists_from_dir(dir_path):
    """
    Run over the content of the input path separating files from directories.

    :param dir_path: folder to be searched.
    :return: tuple (list of directories, list of files).
    :raise UtilsException: if the dir_path param is invalid or is not a folder.
    """
    if is_dir(dir_path):
        dir_list = []
        file_list = []
        for dir_item in os.listdir(dir_path):
            dir_item_path = os.path.join(dir_path, dir_item)

            if os.path.isfile(dir_item_path):
                file_list.append(dir_item_path)
                continue

            dir_list.append(dir_item_path)

        return dir_list, file_list
    raise UtilsException(ExceptionCodes.InvalidFolder, dir_path)


def create_pickle_file(data, file_path=""):
    """
    Create a file with the serialized content of the input data structure.

    :param data: data structure to be serialized.
    :param file_path: file path to dump the content of the data.
    :return: newly created file path.
    :raise UtilsException: if the file_path param is invalid or cannot be created.
    """
    check_not_empty(file_path)

    with open(file_path, 'wb') as file_data:
        pickle.dump(data, file_data)

    if not os.path.exists(file_path):
        raise UtilsException(ExceptionCodes.CannotCreatePath, file_path)

    return file_path


def load_pickle_file(file_path):
    """
    Load a pickle file and return the data structure.

    :param file_path: path to the pickle file.
    :return: loaded data structure.
    :raise UtilsException: if the file_path param is invalid or does not exist.
    """
    is_valid_path(file_path)

    with open(file_path, 'rb') as file_data:
        data = pickle.load(file_data)

    return data


def get_current_user():
    """
    Get current user name.

    :return: current user.
    """
    for name in ('LOGNAME', 'USER', 'LNAME', 'USERNAME'):
        user = os.environ.get(name)
        if user:
            return user
    return pwd.getpwuid(os.getuid())[0]


def get_number_of_content_from_path(source_path):
    """
    Calculate the number of files and folders inside the informed source_path.

    It considers that the path can be either a single file or a folder with other
    files or folders inside.
    If source_path refers to a single file, returns 1, otherwise go through the folder's
    content and count the number of files and folders, recursively.

    :return: number of files and folders inside source_path.
    """
    is_valid_path(source_path)

    total_files = 0
    total_folders = 0

    if os.path.isdir(source_path):
        for file_name in os.listdir(source_path):
            new_path = os.path.join(source_path, file_name)
            if os.path.isdir(new_path):
                total_folders += 1
                files, folders = get_number_of_content_from_path(new_path)
                total_folders += folders
                total_files += files
            else:
                total_files += 1
    else:
        total_files = 1

    return total_files, total_folders


def is_valid_path(path):
    """
    Check if the informed path is valid and exists.

    :param path: path to be validated.
    :return: True if valid.
    :raise UtilsException: if the path param does not exist.
    """
    check_not_empty(path)

    if not os.path.exists(path):
        raise UtilsException(ExceptionCodes.InvalidPath, path)

    return True
