##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module is for adding any utilities related to the remote connections."""

import os
from subprocess import PIPE, Popen
from threading import Timer

from backup.constants import LOG_LEVEL, TIMEOUT
from backup.exceptions import ExceptionCodes, UtilsException
from backup.utils.validator import check_not_empty


def run_ssh_command(host, command, timeout=TIMEOUT):
    """
    Use Popen library to issue commands to the informed host by using ssh protocol.

    :param host: address to connect in user@ip format.
    :param command: command to be executed.
    :param timeout: timeout to wait for the process to finish.
    :return: pair stdout, stderr from communicate command; empty string pair, otherwise.
    """
    if not host.strip() or not command.strip():
        return "", ""

    ssh = Popen(['ssh', '-o', LOG_LEVEL, host, 'bash'],
                stdin=PIPE, stdout=PIPE, stderr=PIPE)

    timer = Timer(timeout, lambda process: process.kill(), [ssh])

    try:
        timer.start()
        stdout, stderr = ssh.communicate(command)
    finally:
        if not timer.is_alive():
            stderr = "Command '{}' timeout.".format(command)
        timer.cancel()

    return stdout, stderr


def check_remote_path_exists(host, path, timeout=TIMEOUT):
    """
    Check if a remote path exists.

    First check what kind of path is being looked for, whether it is a directory or a file,
    in order to run the proper command.

    :param host: remote host address, e.g. user@host_ip
    :param path: remote path to be verified.
    :param timeout: timeout to wait for the process to finish.
    :return: false, if the path does not exist; true, otherwise
    """
    if not host.strip() or not path.strip():
        return False

    ssh_check_dir_command = """
    if [ -d {0} ] || [ -f {0} ]; then echo "DIR_IS_AVAILABLE"; fi\n
    """.format(path)

    stdout, _ = run_ssh_command(host, ssh_check_dir_command, timeout)

    if stdout.strip() != "DIR_IS_AVAILABLE":
        return False

    return True


def create_remote_dir(host, full_path, timeout=TIMEOUT):
    """
    Try to create a remote directory with ssh commands.

    :param host: remote host address, e.g. user@host_ip
    :param full_path: full path to be created.
    :param timeout: timeout to wait for the process to finish.
    :return: true, if directory was successfully created; false, otherwise.
    """
    ssh_create_dir_commands = """
    if [ -d {0} ]; then\n
        echo "DIR_IS_AVAILABLE\n"
    else\n
        mkdir {0}\n
        if [ -d {0} ]; then\n
            echo "DIR_IS_AVAILABLE";\n
        fi\n
    fi\n
    """.format(full_path)

    stdout, stderr = run_ssh_command(host, ssh_create_dir_commands, timeout)

    if stderr.strip():
        return False

    if stdout.strip() != "DIR_IS_AVAILABLE":
        return False

    return True


def remove_remote_dir(host, dir_list=None, timeout=TIMEOUT):
    """
    Remove the informed directory list from the remote server.

    :param host: remote host address, e.g. user@host_ip
    :param dir_list: directory list.
    :param timeout: timeout to wait for the process to finish.
    :return: tuple (list of not removed directories, list of validated removed directories).
    :raise UtilsException: if the params are empty or if the command cannot be executed.
    """
    check_not_empty(host)
    check_not_empty(dir_list)

    if isinstance(dir_list, str):
        dir_list = [dir_list]

    remove_dir_cmd = ""

    for folder_path in dir_list:
        folder_path = folder_path.strip()
        remove_dir_cmd += "rm -rf {}\n".format(folder_path)

    _, stderr = run_ssh_command(host, remove_dir_cmd, timeout)

    if stderr.strip():
        raise UtilsException(ExceptionCodes.CannotRemovePath, [dir_list, stderr])

    return validate_removed_dir_list(host, dir_list)


def validate_removed_dir_list(host, remove_dir_list=None):
    """
    Check the list of removed dirs, to validate if they were successfully deleted from off-site.

    :param host: remote host to do the validation.
    :param remove_dir_list: list of directories supposed to be removed.
    :return: list of not removed directories, list of validated removed directories.
    """
    if remove_dir_list is None:
        remove_dir_list = []

    not_removed_list = []
    validated_removed_list = []
    for removed_path in remove_dir_list:
        if not check_remote_path_exists(host, removed_path):
            validated_removed_list.append(removed_path)
        else:
            not_removed_list.append(removed_path)

    return not_removed_list, validated_removed_list


def get_remote_folder_content(host, remote_path, filtering_criteria='*'):
    r"""
    Get a list of relative paths of files from the informed remote directory.

    Before calling this function, the remote_path must be checked if it exists first.

    :param host: user@remote_ip string.
    :param remote_path: full remote path, used to get all files and folder names within it.
    :param filtering_criteria: filter of find command (e.g. \\*, \\*.tar, \\*.txt).
    :return: relative paths list of files and folders inside the remote directory, if any;
             empty list otherwise.
    :raise UtilsException: if the command returned an error.
    """
    check_not_empty(host)
    check_not_empty(remote_path)

    find_command = "find {} -name {}".format(remote_path, filtering_criteria)

    result, error = run_ssh_command(host, find_command)

    if error:
        raise UtilsException(ExceptionCodes.CannotAccessHost, [host, remote_path, error])

    files_folders_names = []
    if result.strip():
        result_list = result.split('\n')
        for files_folders_full_path in result_list:
            files_folders_names.append(os.path.basename(files_folders_full_path))

    return files_folders_names


def get_number_of_content_from_remote_path(host, remote_path):
    """
    Calculate the number of files and folders from the informed remote path.

    It considers that the path can be either a single file or a folder with other
    files or folders inside.

    :param host: where the remote_path is.
    :param remote_path: folder or file from remote.
    :return: number of files and folders from remote_path.
    :raise UtilsException: if the commands executed return errors or if it can't parse the result.
    """
    check_not_empty(host)
    check_not_empty(remote_path)

    count_files_command = "find {} -type f | wc -l".format(remote_path)
    files_out, error = run_ssh_command(host, count_files_command)
    if error:
        raise UtilsException(ExceptionCodes.CannotAccessHost, [host, remote_path, error])

    count_folders_command = "find {} -mindepth 1 -type d | wc -l".format(remote_path)
    folders_out, error = run_ssh_command(host, count_folders_command)
    if error:
        raise UtilsException(ExceptionCodes.CannotAccessHost, [host, remote_path, error])

    try:
        total_files = int(files_out)
        total_folders = int(folders_out)

        return total_files, total_folders
    except (TypeError, ValueError) as exception:
        raise UtilsException(ExceptionCodes.CannotParseValue, [files_out, folders_out, exception])


def is_remote_folder_empty(host, remote_path):
    """
    Check if the remote folder is empty or not based on the number of files and folders.

    :param host: where the remote_path is.
    :param remote_path: folder or file from remote.
    :return: boolean whether the folder is empty or not.
    """
    n_files, n_folders = get_number_of_content_from_remote_path(host, remote_path)

    return n_files + n_folders == 0


def get_remote_folder_size(host, remote_path, timeout_value=TIMEOUT):
    """
    Get the size of the informed remote folder.

    :param host: remote host connect to in the format user@remote_ip.
    :param remote_path: the full remote path to be checked.
    :param timeout_value: timeout to wait for the process to finish.
    :return: size of the remote folder.
    :raise UtilsException: if the command executed return errors or if it can't parse the result.
    """
    command = "du -bms " + remote_path
    stdout, stderr = run_ssh_command(host, command, timeout_value)

    if stderr:
        raise UtilsException(ExceptionCodes.CannotAccessHost, [host, remote_path, stderr])

    std_output_list = stdout.split('\t')

    try:
        backup_size = int(std_output_list[0])

    except (IndexError, ValueError) as error:
        raise UtilsException(ExceptionCodes.CannotParseValue, [error, std_output_list])

    return backup_size


def sort_remote_folders_by_content(host, remote_folder_list):
    """
    Sort the list of folders based on the oldest file inside the directory.

    Note that empty directories will not be considered for sorting. As a result they will be
    filtered out the result list.

    :param host: remote host connect to in the format user@remote_ip.
    :param remote_folder_list: list of remote folders to be sorted.
    :return: list of folders sorted by date, from the newest to the oldest directory.
    :raise UtilsException: if the command executed return errors or if it can't parse the result.
    """
    if not remote_folder_list:
        return []

    # The output of the command below should be one line for each folder in the following format:
    # file_timestamp file_path
    # END_OF_COMMAND
    find_cmd = ""
    for remote_folder in remote_folder_list:
        find_cmd += "find {0} ! -path {0} -printf \"%T+\t%p\n\" | sort | head -1\necho " \
                    "END_OF_COMMAND\n".format(remote_folder)

    stdout, stderr = run_ssh_command(host, find_cmd)

    if stderr:
        raise UtilsException(ExceptionCodes.ErrorSortingOffsiteBackupList,
                             [host, remote_folder_list, stderr])

    file_timestamp_list = []

    for find_cmd_result in stdout.split('END_OF_COMMAND'):
        if not find_cmd_result.strip():
            continue

        find_cmd_result_split = find_cmd_result.split()

        if len(find_cmd_result_split) != 2:
            raise UtilsException(ExceptionCodes.ErrorSortingOffsiteBackupList,
                                 [host, remote_folder_list, find_cmd_result.strip()])

        first_file_timestamp = find_cmd_result_split[0].strip()
        first_file_full_path = find_cmd_result_split[1].strip()

        file_timestamp_list.append((os.path.dirname(first_file_full_path), first_file_timestamp))

    if not file_timestamp_list:
        return []

    list.sort(file_timestamp_list, key=lambda elem: elem[1], reverse=True)

    # Retrieving only the full path from the tuples of the list.
    return [file_timestamp_tuple[0] for file_timestamp_tuple in file_timestamp_list]
