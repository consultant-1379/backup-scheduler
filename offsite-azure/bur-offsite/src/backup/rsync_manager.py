##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=too-few-public-methods,too-many-locals,unused-argument

"""Module for handling the rsync command tasks."""

from enum import Enum
import os
import subprocess

from backup.exceptions import ExceptionCodes, RsyncException
from backup.utils.decorator import timeit
from backup.utils.fsys import get_number_of_content_from_path
from backup.utils.remote import check_remote_path_exists, get_number_of_content_from_remote_path
from backup.utils.validator import check_not_empty

NUMBER_TRIES = 3
RSYNC_MODULE = "rsync://"
RSYNC_CMD = "rsync"
RSYNC_DAEMON_DESTINATION = "/rsyncd"
RSYNC_SSH_ARGS = "-ahce ssh"
RSYNC_DAEMON_ARGS = "-ahc"

RSYNC_OUTPUT_SUMMARY_ITEM = Enum('RSYNC_OUTPUT_SUMMARY_ITEM',
                                 'total_files, created, deleted, transferred, rate, speedup')


class RsyncOutput:
    """Class used to store relevant output information of rsync commands."""

    def __init__(self, summary_dic):
        """
        Initialize Rsync Output class.

        :param summary_dic: dictionary with data parsed from the rsync output.
        """
        self.n_files = summary_dic[RSYNC_OUTPUT_SUMMARY_ITEM.total_files.name]
        self.n_created_files = summary_dic[RSYNC_OUTPUT_SUMMARY_ITEM.created.name]
        self.n_deleted_files = summary_dic[RSYNC_OUTPUT_SUMMARY_ITEM.deleted.name]
        self.n_transferred_files = summary_dic[RSYNC_OUTPUT_SUMMARY_ITEM.transferred.name]
        self.speedup = summary_dic[RSYNC_OUTPUT_SUMMARY_ITEM.speedup.name]
        self.rate = summary_dic[RSYNC_OUTPUT_SUMMARY_ITEM.rate.name]

    def __str__(self):
        """Representation of stored data in object."""
        return "RsyncOutput:\n" \
               "Number of files: {}\n" \
               "Number of created files: {}\n" \
               "Number of deleted files: {}\n" \
               "Number of transferred files: {}\n" \
               "Speedup: {}\n" \
               "Transfer rate: {}\n".format(self.n_files, self.n_created_files,
                                            self.n_deleted_files, self.n_transferred_files,
                                            self.speedup, self.rate)


class RsyncManager:
    """Class used to encapsulate rsync commands to transfer files over the network."""

    def __init__(self, source_path, destination_path, retry=NUMBER_TRIES, rsync_ssh=True):
        """
        Initialize Rsync Manager class.

        :param source_path: path of the source file to be transferred.
        :param destination_path: destination location to send the file.
        :param retry: number of tries in case of failure.
        :param rsync_ssh: boolean to determine whether to use rsync over ssh or rsync daemon.
        """
        self.source_path = source_path
        self.destination_path = destination_path
        self.retry = retry
        self.rsync_ssh = rsync_ssh

    @staticmethod
    def parse_number_of_file_key_value(rsync_output_line):
        """
        Parse umber of files key-value.

        Given a line from the rsync output, this function gets the number of file measurement as
        well as the text field it is being referred.

        :param rsync_output_line: rsync output line with the 'number of' measurement.
        :return: measurement string, number of files.
        :raise RsyncException: if an error happens.
        """
        if "number of" not in rsync_output_line:
            raise RsyncException(ExceptionCodes.MissingNumberOfParameter, rsync_output_line)

        par = rsync_output_line.find('(')
        if par != -1:
            rsync_output_line = rsync_output_line[0:par - 1]

        if rsync_output_line.find(":") == -1:
            raise RsyncException(ExceptionCodes.CannotParseValue, rsync_output_line)

        number_of_files = rsync_output_line.split(':')[1].strip()

        key = RSYNC_OUTPUT_SUMMARY_ITEM.total_files.name

        if RSYNC_OUTPUT_SUMMARY_ITEM.transferred.name in rsync_output_line:
            key = RSYNC_OUTPUT_SUMMARY_ITEM.transferred.name
        elif RSYNC_OUTPUT_SUMMARY_ITEM.deleted.name in rsync_output_line:
            key = RSYNC_OUTPUT_SUMMARY_ITEM.deleted.name
        elif RSYNC_OUTPUT_SUMMARY_ITEM.created.name in rsync_output_line:
            key = RSYNC_OUTPUT_SUMMARY_ITEM.created.name

        return key, number_of_files

    @staticmethod
    def parse_output(output):
        """
        Parse the output of a rsync execution.

        Collect relevant information to be stored in a RsyncOutput object.

        :param output: output after a rsync execution.
        :return: RsyncOutput with the retrieved information.
        :raise RsyncException: if an error happens during the process.
        """
        check_not_empty(output)

        lines = str(output).lower().split('\n')

        summary_dic = {}
        for summary_item in RSYNC_OUTPUT_SUMMARY_ITEM:
            summary_dic[summary_item.name] = None

        for line in lines:
            if "number of" in line:

                key, number_of_files = RsyncManager.parse_number_of_file_key_value(line)
                summary_dic[key] = number_of_files

            elif "bytes/sec" in line:
                line_split = line.split(" ")

                item_index = 0
                for item in line_split:
                    if "bytes/sec" in item.strip():
                        break
                    item_index += 1

                summary_dic[RSYNC_OUTPUT_SUMMARY_ITEM.rate.name] = line_split[item_index - 1]

            elif RSYNC_OUTPUT_SUMMARY_ITEM.speedup.name in line:

                speedup_value = line[line.find(RSYNC_OUTPUT_SUMMARY_ITEM.speedup.name) + len(
                    RSYNC_OUTPUT_SUMMARY_ITEM.speedup.name) + len(" is "):]

                summary_dic[RSYNC_OUTPUT_SUMMARY_ITEM.speedup.name] = speedup_value

        for item in summary_dic:
            if summary_dic[item] is None:
                raise RsyncException(ExceptionCodes.CannotParseValue, summary_dic[item])

        return RsyncOutput(summary_dic)

    def receive(self):
        """
        Try to receive files from a remote location.

        :return: RsyncOutput object with the output information of the command.
        :raise RsyncException: if an error happens during the process.
        """
        try:
            if self.rsync_ssh:
                rsync_args = RSYNC_SSH_ARGS
                source_path = self.source_path
            else:
                rsync_args = RSYNC_DAEMON_ARGS
                source_path = "{}{}".format(RSYNC_MODULE,
                                            self.source_path.replace(":", RSYNC_DAEMON_DESTINATION))
            source_path_split = self.source_path.split(':')

            if len(source_path_split) != 2:
                raise RsyncException(ExceptionCodes.InvalidPath, source_path_split)

            host = source_path_split[0]
            remote_path = source_path_split[1]

            if not check_remote_path_exists(host, remote_path):
                raise RsyncException(ExceptionCodes.InvalidPath, source_path)

            output = subprocess.check_output([RSYNC_CMD, rsync_args, '--stats', source_path,
                                              self.destination_path], stderr=subprocess.PIPE)

            rsync_output = self.parse_output(output)

            destination_basename = os.path.basename(remote_path)
            destination_path = os.path.join(self.destination_path, destination_basename)

            origin_number_files, _ = get_number_of_content_from_remote_path(host, remote_path)
            destination_number_files, _ = get_number_of_content_from_path(destination_path)

            if (int(rsync_output.n_transferred_files) != origin_number_files) or \
                    (int(rsync_output.n_transferred_files) != destination_number_files):
                values = {'n_transferred_files': rsync_output.n_transferred_files,
                          'destination_number_files': destination_number_files,
                          'origin_number_files': origin_number_files}
                raise RsyncException(ExceptionCodes.RsyncTransferNumberFilesDiffer, values)

            return rsync_output

        except subprocess.CalledProcessError as process_error:
            raise RsyncException(parameters=process_error)

        except (TypeError, ValueError) as error:
            raise RsyncException(parameters=error)

    def send(self):
        """
        Try to send local file(s) referred by source_path to the destination_path location.

        It will try to send the file as many times as specified by the retry variable.

        :return: RsyncOutput object with the output information of the command.
        :raise RsyncException: if the maximum number of tries is reached without success.
        """
        try:
            n_files, _ = get_number_of_content_from_path(self.source_path)
            if n_files == 0:
                raise RsyncException(ExceptionCodes.NoFilesToSend, self.source_path)

            if self.rsync_ssh:
                rsync_args = RSYNC_SSH_ARGS
                destination_path = self.destination_path
            else:
                rsync_args = RSYNC_DAEMON_ARGS
                destination_path = self.destination_path.replace(":", RSYNC_DAEMON_DESTINATION)
                destination_path = "{}{}".format(RSYNC_MODULE, destination_path)

            for current_try in range(1, self.retry + 1):
                process = [RSYNC_CMD, rsync_args, '--stats', self.source_path, destination_path]
                output = subprocess.check_output(process, stderr=subprocess.PIPE)

                rsync_output = self.parse_output(output)

                if int(rsync_output.n_transferred_files) == int(n_files):
                    return rsync_output

                if current_try == self.retry:
                    raise RsyncException(ExceptionCodes.ExceedTryOuts,
                                         [self.retry, rsync_output.__str__()])
            return False

        except subprocess.CalledProcessError as process_error:
            raise RsyncException(parameters=process_error.__str__())

        except (TypeError, ValueError) as error:
            raise RsyncException(parameters=error.__str__())

    @staticmethod
    @timeit
    def transfer_file(source_path, target_path, rsync_ssh=True, **kwargs):
        """
        Transfer a file from the source to a target location by using RsyncManager.

        If the source_path refers to a remote location, the following format is expected:

            e.g. host@ip:/path/to/remote/file

        In this case the receive function will be called, otherwise, the send function is used.

        :param source_path: file name to be transferred or retrieved.
        :param target_path: remote location.
        :param rsync_ssh: boolean to determine whether to use rsync over ssh or rsync daemon,
        default value is true, which means use rsync ssh by default.
        :return: RsyncOutput object with details of the transfer process.
        :raise Exception: if an error happens during the transferring.
        """
        check_not_empty(source_path)
        check_not_empty(target_path)

        if '@' in source_path:
            rsync_output = RsyncManager(source_path, target_path, NUMBER_TRIES, rsync_ssh).receive()
        else:
            rsync_output = RsyncManager(source_path, target_path, NUMBER_TRIES, rsync_ssh).send()

        return rsync_output
