##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module to customize logger functions."""

import logging
from logging.handlers import RotatingFileHandler
import os
import sys

import backup.constants as constants
from backup.utils.datetime import format_time

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

DEFAULT_LOG_ROOT_PATH = os.path.dirname(__file__)
DEFAULT_LOG_FILE_NAME = "{}.{}".format(SCRIPT_FILE, constants.LOG_SUFFIX)

OUTPUT_LINE = "===================================================================================="


class CustomLogger(logging.LoggerAdapter):
    """CustomLogger is a customized logger with auxiliary functions to display log messages."""

    def __init__(self, script_reference=SCRIPT_FILE, log_root_path=DEFAULT_LOG_ROOT_PATH,
                 log_file_name=DEFAULT_LOG_FILE_NAME, log_level=logging.DEBUG):
        """
        Initialize log class.

        :param script_reference: script name using the logger.
        :param log_root_path: full root path of the log file.
        :param log_file_name: log file name.
        :param log_level: level in which log messages will be displayed.
        """
        self.log_level = log_level
        self.log_root_path = log_root_path
        self.log_file_name = log_file_name
        self.log_file_full_path = ""

        if log_root_path.strip() and log_file_name.strip() and os.path.exists(log_root_path):
            self.log_file_full_path = os.path.join(log_root_path, log_file_name)

        self.logger = logging.getLogger(script_reference)
        if not self.logger.handlers:
            self.configure_logger()

        super(CustomLogger, self).__init__(self.logger, {})

    def configure_logger(self):
        """Configure logging for this script."""
        formatter = logging.Formatter('%(asctime)s - %(processName)s - '
                                      '%(threadName)s - %(name)s - '
                                      '%(levelname)s - %(message)s')

        self.logger.setLevel(self.log_level)

        stream_handler_obj = logging.StreamHandler()
        stream_handler_obj.setLevel(self.log_level)
        stream_handler_obj.setFormatter(formatter)
        self.logger.addHandler(stream_handler_obj)

        if self.log_file_full_path.strip():
            file_handler_objs = RotatingFileHandler(self.log_file_full_path)
            file_handler_objs.setLevel(self.log_level)
            file_handler_objs.setFormatter(formatter)
            self.logger.addHandler(file_handler_objs)

    def log_info(self, log_content):
        """
        Log a message between lines to highlight the log.

        :param log_content: content of log message.
        """
        self.info(OUTPUT_LINE)
        self.info(log_content)
        self.info(OUTPUT_LINE)

    def log_error_exit(self, log_content, exit_code=0):
        """
        Log messages with error level, then exits application with provided exit code.

        :param log_content: content of log message.
        :param exit_code: exit code to exit the application with.
        """
        if not isinstance(log_content, list):
            log_content = [log_content]

        for log_error in log_content:
            self.error(log_error)

        self.error("Exiting (exit code: %s).", exit_code)

        sys.exit(exit_code)

    def log_time(self, msg, elapsed_time):
        """
        Log a message with elapsed time information.

        :param msg:          context message to describe the elapsed time.
        :param elapsed_time: elapsed time to be logged.
        """
        formatted_time = format_time(float(elapsed_time))

        self.info("%s : %s.", msg, str(formatted_time))
