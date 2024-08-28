##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module to collect and format performance data during BUR operations."""

from enum import Enum
import os
import sys

import backup.constants as constants
from backup.utils.datetime import format_time
from backup.utils.fsys import create_path, get_home_dir

SCRIPT_PATH = os.path.dirname(__file__)

PERFORMANCE_PER_BACKUP_FILE_NAME = "performance_per_backup.csv"
PERFORMANCE_PER_VOLUME_SUFFIX_FILE_NAME = "_performance_per_volume.csv"

PERFORMANCE_TIME_INDEX = Enum('PERFORMANCE_TIME_INDEX', 'COMPRESS_TIME, ENCRYPT_TIME')
DEFAULT_PERFORMANCE_ROOT_PATH = os.path.join(get_home_dir(), "backup")


class BURPerformance:
    """
    Handle data about the performance of the backup process.

    It also provides functions to calculate and generate a csv report.
    """

    def __init__(self, bur_id, backup_output_dict, total_time):
        """
        Initialize Backup Performance class.

        Identification depends on the current operation, if upload it uses customer_id, if download
        it uses the backup_tag.

        :param bur_id: id of the backup according to the operation.
        :param backup_output_dict: dictionary with the output of the backup operation process.
        :param total_time: total time to process whole backup..
        """
        self.bur_id = bur_id
        self.backup_output_dict = backup_output_dict
        self.total_time = total_time

    def __str__(self):
        """
        To string method.

        :return: string with the string representation of the class.
        """
        total_time = format_time(self.total_time)

        return "{}, {}\n".format(self.bur_id, total_time)

    def update_csv_reports(self):
        """
        Store collected performance data from the backup process into csv files.

        Two csv files will be updated: Consolidated data per backup, Time data per volume.

        The report contains the following consolidated data:
        """
        passed_args = sys.argv
        is_log_root_path_provided, log_root_path_value = \
            BURPerformance.get_log_root_path_value(passed_args)
        if is_log_root_path_provided:
            performance_file_root_path = log_root_path_value
        else:
            performance_file_root_path = DEFAULT_PERFORMANCE_ROOT_PATH

        if not os.access(performance_file_root_path, os.R_OK):
            performance_file_root_path = os.path.join(SCRIPT_PATH)

        performance_file_root_path = os.path.join(performance_file_root_path, self.bur_id)
        create_path(performance_file_root_path)

        self.update_per_backup_report(performance_file_root_path)
        self.update_per_volume_report(performance_file_root_path)

    def update_per_backup_report(self, performance_file_path):
        """
        Update the file related to the consolidated report per backup.

        :param performance_file_path: path to store the report file.
        """
        report_file_path = os.path.join(performance_file_path, PERFORMANCE_PER_BACKUP_FILE_NAME)

        if not os.path.exists(report_file_path):
            report_file = open(report_file_path, 'a')
            report_file.write(str(BURPerformance.get_per_backup_header()))
            report_file.close()

        with open(report_file_path, 'a') as report_file:
            report_file.write(self.__str__())

    def update_per_volume_report(self, performance_file_path):
        """
        Update the file related to the report per volume.

        :param performance_file_path: path to store the report file.
        """
        report_file_path = os.path.join(performance_file_path, "{}{}".
                                        format(self.bur_id,
                                               PERFORMANCE_PER_VOLUME_SUFFIX_FILE_NAME))

        if not os.path.exists(report_file_path):
            report_file = open(report_file_path, 'a')
            report_file.write(str(BURPerformance.get_per_volume_header()))
            report_file.close()

        for volume_name in self.backup_output_dict.keys():
            proc_time = self.backup_output_dict[volume_name][
                constants.VOLUME_OUTPUT_KEYS.processing_time.name]
            tar_time = self.backup_output_dict[volume_name][
                constants.VOLUME_OUTPUT_KEYS.tar_time.name]
            transfer_time = self.backup_output_dict[volume_name][
                constants.VOLUME_OUTPUT_KEYS.transfer_time.name]

            total_proc_time = float(proc_time) + float(tar_time)
            total_time = total_proc_time + float(transfer_time)

            # rsync_output = \
            #     self.backup_output_dict[volume_name][constants.VOLUME_OUTPUT_KEYS.rsync_output.name]

            # rsync_speedup = rsync_rate = constants.NOT_INFORMED_STR
            # if rsync_output is not None:
            #     rsync_speedup = rsync_output.speedup
            #     rsync_rate = rsync_output.rate

            rsync_speedup = "0.0"
            rsync_rate = "0.0"

            azcopy_output = self.backup_output_dict[volume_name][constants.VOLUME_OUTPUT_KEYS.rsync_output.name]

            az_copy_transfer_time = constants.NOT_INFORMED_STR
            if azcopy_output is not None:
                az_copy_transfer_time = azcopy_output.summary_dict.get("Elapsed Time (Minutes)")


            with open(report_file_path, 'a') as report_file:
                report_file.write("{}, {}, {}, {}, {}, {}, {}, {}, {}\n".format(volume_name,
                                                                            format_time(proc_time),
                                                                            format_time(tar_time),
                                                                            format_time(
                                                                                total_proc_time),
                                                                            format_time(
                                                                                transfer_time),
                                                                            format_time(total_time),
                                                                            rsync_speedup,
                                                                            rsync_rate, az_copy_transfer_time))

    @staticmethod
    def get_log_root_path_value(passed_args):
        """
        Extract the value provided with --log_root_path, if any.

        :param passed_args: the log_root_path value, if any.
        :return: true and log_root_path value, if it was provided; false and None otherwise.
        """
        for param in passed_args:
            if param == constants.LOG_ROOT_PATH_CLI:
                param_found_at_index = passed_args.index(constants.LOG_ROOT_PATH_CLI)
                if (param_found_at_index + 1) < len(passed_args):
                    if passed_args.index(passed_args[param_found_at_index + 1]) is not None:
                        log_root_path_value = passed_args[param_found_at_index + 1]
                        if str(log_root_path_value).strip() and \
                                not str(log_root_path_value).startswith("--"):
                            return True, log_root_path_value
        return False, None

    @staticmethod
    def get_per_backup_header():
        """
        Return the header of the performance report per backup.

        :return: header.
        """
        return "BUR_ID, TOTAL_TIME\n"

    @staticmethod
    def get_per_volume_header():
        """
        Return the header of the performance report per volume.

        :return: header.
        """
        return "VOLUME_NAME, COMPRESSION_ENCRYPTION_TIME, TAR_TIME, TOTAL_PROCESSING_TIME, " \
               "TRANSFER_TIME, TOTAL_TIME, SPEEDUP, RATE, AZCOPY_TRANSFER_TIME\n"
