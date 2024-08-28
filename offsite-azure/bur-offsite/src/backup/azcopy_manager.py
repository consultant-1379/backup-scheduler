##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################
from subprocess import Popen, PIPE
import os

from backup.exceptions import AzCopyException, ExceptionCodes

import re

NUMBER_TRIES = 3

AZCOPY_CMD = "azcopy"
azcopy_func_args = "copy"
azcopy_output_type_args = "--output-type"
SEP = " "
azcopy_output_type = "text"

sastoken_default = "?sv=2019-02-02&ss=b&srt=sco&sp=rwdlac&se=2021-06-04T23:07:53Z&st=2019-11-18T16:07:53Z&spr=https&sig=NkvWBH3PnrUgEugjWZeUfPKnm8LR1oD9tk728q81w%2FY%3D"
sastoken = os.environ.get('SAS_TOKEN', sastoken_default)

class AzCopyOutput:
    """Class used to store relevant output information of rsync commands."""

    def __init__(self, summary_dict, error_msg=None):
        """
        Initialize Rsync Output class.

        :param summary_dict: dictionary with data parsed from the rsync output.
        """
        self.summary_dict = summary_dict
        self.error_msg = error_msg

    def __str__(self):
        """Representation of stored data in object as string."""
        return "AzCopy Output:\n" \
               "{}".format(str(self.summary_dict))


class AzCopyManager:
    """
    Class used to encapsulate AzCopy commands to transfer processed files over to Azure Storage
    """
    def __init__(self, source_path, destination_path, retry=NUMBER_TRIES):
        """
        Initialize Rsync Manager class.

        :param source_path: path of the source file to be transferred.
        :param destination_path: destination location to send the file.
        :param retry: number of tries in case of failure.
        """
        self.source_path = str(source_path)
        self.destination_path = str(destination_path)
        self.retry = retry

    @staticmethod
    def check_if_url(path):
        try:
            re.search("(?P<url>https?://[^\s]+)", path).group("url")
            return True
        except AttributeError:
            return False

    def parse_azcopy_output(self, output):
        az_op_dict = {"Elapsed Time (Minutes)" : None,
                      "Total Number Of Transfers" : None,
                      "Number of Transfers Completed" : None,
                      "Number of Transfers Failed" : None,
                      "Number of Transfers Skipped" : None,
                      "TotalBytesTransferred" : None,
                      "Final Job Status" : None}
        lines = str(output).split('\n')

        for line in lines:
            if "failed to" in line:
                return AzCopyOutput(az_op_dict, error_msg=line.strip())
            for item in az_op_dict:
                if item in line and ":" in line:
                    az_op_dict[item] = line.split(":")[1].strip()

        return AzCopyOutput(az_op_dict)

    def transfer(self):
        try:
            command = [AZCOPY_CMD, azcopy_func_args, self.source_path, self.destination_path, azcopy_output_type_args,
                       azcopy_output_type]
            process = Popen(command, shell=False, stdout=PIPE, stderr=PIPE)
            output, std_error = process.communicate()
            azcopy_output = self.parse_azcopy_output(output)

            if azcopy_output.summary_dict["Final Job Status"] != "Completed":
                if azcopy_output.error_msg:
                    raise AzCopyException(ExceptionCodes.AzCopyExecutionFailed, azcopy_output.error_msg)

            return azcopy_output
        except (TypeError, ValueError) as error:
            raise AzCopyException(parameters=error.__str__())



    @staticmethod
    def transfer_file(source_path, destination_path):
        target_file_name = os.path.basename(source_path)
        destination_file_path = os.path.join(destination_path, target_file_name)

        if AzCopyManager.check_if_url(destination_path):
            target_source_path = source_path
            target_destination_path = destination_file_path + sastoken
        elif AzCopyManager.check_if_url(source_path):
            target_source_path = source_path + sastoken
            target_destination_path = destination_file_path
        else:
            raise AzCopyException(parameters="Source and destination path not Azure URL")

        azcopy_output = AzCopyManager(target_source_path, target_destination_path, NUMBER_TRIES).transfer()

        return azcopy_output
