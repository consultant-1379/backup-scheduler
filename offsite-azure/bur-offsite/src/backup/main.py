#!/usr/bin/env python

##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=too-many-arguments,too-many-locals,unused-argument

"""Module for running the upload, download and clean up of backups."""

import argparse
from enum import Enum
import os
import sys

from logger import logging

from backup import __version__
from backup.bur_input_validators import SCRIPT_OBJECTS, validate_argument_list, \
    validate_get_main_logger, validate_input_arguments, validate_onsite_offsite_locations, \
    validate_script_settings
from backup.constants import DEFAULT_NUM_PROCESSORS, DEFAULT_NUM_THREADS, \
    DEFAULT_NUM_TRANSFER_PROCS, LOG_ROOT_PATH_CLI, LOG_SUFFIX
from backup.exceptions import BurException, NotificationHandlerException
from backup.local_backup_handler import LocalBackupHandler
from backup.offsite_backup_handler import OffsiteBackupHandler
from backup.utils.datatypes import get_values_from_dict
from backup.utils.datetime import format_time, get_formatted_timestamp
from backup.utils.decorator import timeit
from backup.utils.fsys import get_home_dir
from backup.utils.script_cli import get_cli_arguments

SCRIPT_OPTION_HELP = "Select the function to be executed.\n" \
                     "    1 - Backup to cloud\n" \
                     "    2 - Download from cloud\n" \
                     "    3 - Execute retention"
NUMBER_THREADS_HELP = "Select the number of threads allowed. Defaults to 5."
NUMBER_PROCESSORS_HELP = "Select the number of processors. Defaults to 5."
NUMBER_RSYNC_INSTANCES_HELP = "Select the number of working rsync instances. Defaults to 8."
LOG_ROOT_PATH_HELP = "Provide a path to store the logs."
LOG_LEVEL_HELP = "Provide the log level. Options: [CRITICAL, ERROR, WARNING, INFO, DEBUG]."
BACKUP_TAG_HELP = "Provide the backup tag to be downloaded."
CUSTOMER_NAME_HELP = "Provide the customer name to process upload or download."
BACKUP_DESTINATION_HELP = "Provide the destination of the downloaded backup."
RSYNC_SSH_HELP = "Whether to use rsync over ssh. Defaults to False, which means it will use " \
                 "rsync daemon."
USAGE_HELP = "Display detailed help."
OFFSITE_RETENTION_HELP = "Number of how many backups will be retained."
BUR_VERSION_HELP = "Show currently installed bur version."

SCRIPT_PATH = os.path.dirname(__file__)
SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

CONF_FILE_NAME = 'config.cfg'

MAIN_LOG_FILE_NAME = "bur_{}.{}".format(SCRIPT_FILE, LOG_SUFFIX)
DEFAULT_LOG_ROOT_PATH = os.path.join(get_home_dir(), "backup")

SUCCESS_EXIT_CODE = 0

EXIT_CODES = Enum('EXIT_CODES', 'INVALID_INPUT, FAILED_UPLOAD, FAILED_DOWNLOAD, FAILED_QUERY, '
                                'FAILED_OFFSITE_CLEANUP, FAILED_VALIDATION')

SCRIPT_OPERATIONS = Enum('SCRIPT_OPERATIONS', 'BKP_UPLOAD, BKP_DOWNLOAD, RETENTION, SIZE')


def main(arg_list=None):
    """
    Start the backup upload/download/cleanup processes.

    Customer(s) is/are specified according to the input.

    :param arg_list: list of params to be used instead of the input cli.
    :return: exit code as defined in ExitCodes enumerator.
    """
    try:
        args = validate_argument_list(get_arg_parser, DEFAULT_LOG_ROOT_PATH, arg_list)
    except BurException as arg_parse_exp:
        show_bur_arg_error(arg_parse_exp.__str__())

    if args.usage:
        show_bur_usage()

    if args.version:
        show_bur_version()

    if arg_list:
        provided_cli_args = arg_list
    else:
        provided_cli_args = get_cli_arguments()

    logger = validate_get_main_logger(args, MAIN_LOG_FILE_NAME, SCRIPT_OPERATIONS)

    logger.log_info("Running BUR with the following arguments: {}".format(provided_cli_args))

    config_object_dict = execute_validation_input(args, logger)

    offsite_config = config_object_dict[SCRIPT_OBJECTS.OFFSITE_CONFIG.name]
    onsite_config = config_object_dict[SCRIPT_OBJECTS.ONSITE_CONFIG.name]
    customer_config_dict = config_object_dict[SCRIPT_OBJECTS.CUSTOMER_CONFIG_DICT.name]
    gpg_manager = config_object_dict[SCRIPT_OBJECTS.GNUPG_MANAGER.name]
    notification_handler = config_object_dict[SCRIPT_OBJECTS.NOTIFICATION_HANDLER.name]
    delay_config = config_object_dict[SCRIPT_OBJECTS.DELAY_CONFIG.name]

    op_time = []

    if str(args.script_option) == str(SCRIPT_OPERATIONS.BKP_UPLOAD.value):
        execute_backup_upload(customer_config_dict, offsite_config, onsite_config, gpg_manager,
                              notification_handler, logger, args, delay_config,
                              get_elapsed_time=op_time)

        # If this message needs to be changed, then please notify all team members about it.
        # Changing this message will have an impact on the genie pipeline, refer to NMAAS-2393.
        logger.log_time("Elapsed time to complete the backup", op_time[0])

    elif str(args.script_option) == str(SCRIPT_OPERATIONS.BKP_DOWNLOAD.value):
        if args.backup_tag is not None and args.backup_tag.strip():
            execute_backup_download(customer_config_dict, offsite_config, gpg_manager,
                                    notification_handler, logger, args, get_elapsed_time=op_time)

            elapsed_time_msg = "Elapsed time to finish the whole backup download process"

        else:
            execute_backup_query(customer_config_dict, offsite_config, gpg_manager,
                                 notification_handler, logger, args, get_elapsed_time=op_time)

            elapsed_time_msg = "Elapsed time to search backups"

        logger.log_time(elapsed_time_msg, op_time[0])

    elif str(args.script_option) == str(SCRIPT_OPERATIONS.RETENTION.value):
        success_list = execute_offsite_backup_cleanup(customer_config_dict, offsite_config,
                                                      gpg_manager, notification_handler, logger,
                                                      args, get_elapsed_time=op_time)

        logger.log_time("Elapsed time to finish the backup off-site cleanup operation", op_time[0])

        report_success(notification_handler, logger, SCRIPT_OPERATIONS.RETENTION, success_list)

    else:
        logger.log_error_exit("Operation {} not supported.".format(args.script_option),
                              EXIT_CODES.INVALID_INPUT.value)

    return SUCCESS_EXIT_CODE


def execute_validation_input(bur_args, logger):
    """
    Validate the configuration file and input arguments.

    Return the objects necessary to run BUR operations.

    :param bur_args: argument object.
    :param logger: logger object.
    :return: configuration object dictionary if success, exit with INVALID_INPUT error code.
    """
    script_objects = {}
    try:
        script_objects = validate_script_settings(CONF_FILE_NAME, script_objects, logger,
                                                  bur_args.customer_name)

        validate_onsite_offsite_locations(CONF_FILE_NAME, script_objects, logger)

        validate_input_arguments(bur_args, SCRIPT_OPERATIONS, logger)

    except BurException as validation_exception:
        if script_objects and SCRIPT_OBJECTS.NOTIFICATION_HANDLER.name in script_objects.keys():
            notification_handler = script_objects[SCRIPT_OBJECTS.NOTIFICATION_HANDLER.name]

            operation = "Input Validation"
            report_error(notification_handler, logger, operation, validation_exception.__str__(),
                         EXIT_CODES.FAILED_VALIDATION.value, exit_script=True)
        else:
            logger.log_error_exit(validation_exception.__str__(),
                                  EXIT_CODES.FAILED_VALIDATION.value)

    return script_objects


@timeit
def execute_backup_upload(customer_config_dict, offsite_config, onsite_config, gpg_manager,
                          notification_handler, logger, bur_args, delay_config, **kwargs):
    """
    Go over the customer's list and trigger their backup processes.

    If customer name is provided, it will perform the backup of this single enmaas deployment.

    :param customer_config_dict: dictionary with the enmaas configuration per customer.
    :param offsite_config: offsite object.
    :param onsite_config: onsite object.
    :param gpg_manager: gpg manager object.
    :param notification_handler: object to send e-mail in case of error.
    :param logger: logger object.
    :param bur_args: the CLI arguments.
    :param delay_config: configuration about timeout for backup uploads.
    :return: True if success.
    """
    operation = SCRIPT_OPERATIONS.BKP_UPLOAD
    success_message_list = []
    is_success = True

    for customer_config in customer_config_dict.values():
        try:
            if not os.path.exists(customer_config.backup_path):
                logger.error("Backup path '{}' does not exist for customer {}"
                             .format(customer_config.backup_path, customer_config.name))
                continue

            local_backup_handler = LocalBackupHandler(offsite_config,
                                                      onsite_config,
                                                      customer_config,
                                                      gpg_manager,
                                                      bur_args.number_processors,
                                                      bur_args.number_threads,
                                                      bur_args.number_transfer_processors,
                                                      logger,
                                                      bur_args.rsync_ssh)

            upload_time = []
            report_delay_args = [customer_config.name, operation, delay_config.max_delay,
                                 get_formatted_timestamp(), notification_handler, logger]

            processed_backup_tag = local_backup_handler.process_backup_list(
                bur_args.backup_tag, get_elapsed_time=upload_time, max_delay=delay_config.max_delay,
                on_timeout=report_delay, on_timeout_args=report_delay_args)

            success_message = "Upload successfully finished for customer {}.".format(
                customer_config.name)
            logger.info(success_message)
            success_message_list.append(success_message)

            backup_tag_message = "Backup tag(s): {}.".format(processed_backup_tag)
            success_message_list.append(backup_tag_message)

            if upload_time:
                elapsed_msg = "Elapsed time to finish upload"
                success_message_list.append("{}: {}.".format(elapsed_msg,
                                                             format_time(upload_time[0])))
                logger.log_time(elapsed_msg, upload_time[0])

            customer_dict = {customer_config.name: customer_config}
            # cleanup_success_list = execute_offsite_backup_cleanup(
            #     customer_dict, offsite_config, gpg_manager, notification_handler, logger, bur_args)

            # success_message_list.append(cleanup_success_list)

            report_success(notification_handler, logger, operation, success_message_list,
                           customer_config.name)

        except BurException as upload_exception:
            is_success = False
            report_error(notification_handler, logger, operation, upload_exception.__str__(),
                         EXIT_CODES.FAILED_UPLOAD.value)

    if not is_success:
        logger.log_error_exit("BUR Operation finished.", EXIT_CODES.FAILED_UPLOAD.value)

    return True


@timeit
def execute_backup_query(customer_config_dict, offsite_config, gpg_manager, notification_handler,
                         logger, bur_args, **kwargs):
    """
    Display the list of available backups on off-site per customer.

    :param customer_config_dict: dictionary with customer configuration data.
    :param offsite_config: off-site object.
    :param gpg_manager: gpg manager object.
    :param notification_handler: object to send e-mail in case of error.
    :param logger: logger object.
    :param bur_args: the CLI arguments.
    :return: True if success.
    """
    offsite_backup_handler = OffsiteBackupHandler(gpg_manager,
                                                  offsite_config,
                                                  customer_config_dict,
                                                  bur_args.number_threads,
                                                  bur_args.number_processors,
                                                  bur_args.number_transfer_processors,
                                                  logger,
                                                  bur_args.rsync_ssh)

    try:
        customer_query = get_values_from_dict(customer_config_dict, bur_args.customer_name)

    except BurException as customer_not_found_exception:
        error_list = [customer_not_found_exception.__str__()]

        report_error(notification_handler, logger, SCRIPT_OPERATIONS.BKP_DOWNLOAD, error_list,
                     EXIT_CODES.FAILED_QUERY.value, exit_script=True)

    customer_backup_dict = offsite_backup_handler.get_offsite_backup_dict(customer_query)

    success_message = "Retrieved list of backups per customer: {}.".format(dict(
        customer_backup_dict))

    logger.info(success_message)

    return True


@timeit
def execute_backup_download(customer_config_dict, offsite_config, gpg_manager,
                            notification_handler, logger, bur_args, **kwargs):
    """
    Find the informed backup tag on off-site and download it to the local NFS.

    Customer name is optional when providing backup tag.

    :param customer_config_dict: dictionary with customer configuration data.
    :param offsite_config: off-site object.
    :param gpg_manager: gpg manager object.
    :param notification_handler: object to send e-mail in case of error.
    :param logger: logger object.
    :param bur_args: the CLI arguments.
    :return: True if success.
    """
    offsite_backup_handler = OffsiteBackupHandler(gpg_manager,
                                                  offsite_config,
                                                  customer_config_dict,
                                                  bur_args.number_threads,
                                                  bur_args.number_processors,
                                                  bur_args.number_transfer_processors,
                                                  logger,
                                                  bur_args.rsync_ssh)

    operation = SCRIPT_OPERATIONS.BKP_DOWNLOAD

    try:
        offsite_backup_handler.execute_download_backup_from_offsite(bur_args.customer_name,
                                                                    bur_args.backup_tag,
                                                                    bur_args.backup_destination)

        success_message = "Backup '{}' downloaded successfully to destination '{}'.".format(
            bur_args.backup_tag, bur_args.backup_destination)

        logger.info(success_message)

        report_success(notification_handler, logger, operation, success_message,
                       bur_args.customer_name)

    except BurException as backup_download_exception:
        backup_tag = "Backup tag: {}.".format(bur_args.backup_tag) if bur_args.backup_tag \
            else "No tag informed."

        error_list = [backup_tag, backup_download_exception.__str__()]
        report_error(notification_handler, logger, operation, error_list,
                     EXIT_CODES.FAILED_DOWNLOAD.value, exit_script=True)

    return True


@timeit
def execute_offsite_backup_cleanup(customer_config_dict, offsite_config, gpg_manager,
                                   notification_handler, logger, bur_args, **kwargs):
    """
    Perform the backup off-site cleanup for all customers.

    If more than 3 backups are found on off-site, the oldest one will be deleted.

    :param customer_config_dict: dictionary with all enmaas configuration data.
    :param offsite_config: off-site object.
    :param gpg_manager: gpg manager object.
    :param notification_handler: object to send e-mail in case of error.
    :param logger: logger object.
    :param bur_args: the CLI arguments.
    :return: success_message_list if success; if error, exit with FAILED_OFFSITE_CLEANUP error code.
    """
    operation = SCRIPT_OPERATIONS.RETENTION
    offsite_backup_handler = OffsiteBackupHandler(gpg_manager,
                                                  offsite_config,
                                                  customer_config_dict,
                                                  bur_args.number_processors,
                                                  bur_args.number_threads,
                                                  bur_args.number_transfer_processors,
                                                  logger,
                                                  bur_args.rsync_ssh)

    if not bur_args.offsite_retention:
        bur_args.offsite_retention = offsite_config.retention

    cleanup_status, out_msg, removed_dir = \
        offsite_backup_handler.clean_offsite_backup(bur_args.offsite_retention)

    if not cleanup_status:
        report_error(notification_handler, logger, operation, out_msg,
                     EXIT_CODES.FAILED_OFFSITE_CLEANUP.value, exit_script=True)

    logger.info(out_msg)
    success_message_list = [out_msg]

    if removed_dir:
        removed_msg = "Removed directories were: {}".format(removed_dir)
        logger.info(removed_msg)
        success_message_list.append(removed_msg)

    return success_message_list


def report_error(notification_handler, logger, operation, error_list, error_code,
                 exit_script=False, tag=None):
    """
    Log the informed error, send a notification e-mail and exit, if error during backup operation.

    :param notification_handler: object that process the e-mail sending.
    :param logger: logger object.
    :param operation: operation that raised the error.
    :param error_list: raised error message.
    :param error_code: error code.
    :param exit_script: if the report should finish the script and exit the execution.
    :param tag: backup tag or customer name for e-mail title.
    :return: true if success.
    """
    try:
        operation = get_readable_operation_name(operation)
        subject = "Error executing BUR {} Operation".format(operation)

        if tag and tag.strip():
            subject = "{} for {}".format(subject, tag)

        notification_handler.send_error_email(subject, error_list, error_code)

    except NotificationHandlerException as notification_exp:
        logger.error(notification_exp.__str__())

    if exit_script:
        logger.log_error_exit("BUR Operation finished.", error_code)

    return True


def report_success(notification_handler, logger, operation, success_list, tag=None):
    """
    Send a notification e-mail when finishing any BUR operation successfully.

    :param notification_handler: object that process the e-mail sending.
    :param logger: logger object.
    :param operation: operation that triggered success e-mail.
    :param success_list: list of success messages.
    :param tag: backup tag or customer name for e-mail title.
    :return: true if success.
    """
    try:
        operation = get_readable_operation_name(operation)
        report_title = "BUR Operation {} finished".format(operation)

        if tag and tag.strip():
            report_title = "{} for {}".format(report_title, tag)

        notification_handler.send_success_email(report_title, success_list)

    except NotificationHandlerException as notification_exp:
        logger.error(notification_exp.__str__())

    return True


def report_delay(customer_name, operation, max_delay, start_time, notification_handler, logger):
    """
    In case of delay during backup operation, send a notification e-mail.

    :param customer_name: customer that the operation was triggered for.
    :param operation: operation that triggered success e-mail.
    :param max_delay: max running time for the process.
    :param start_time: time when the operation started.
    :param notification_handler: object that process the e-mail sending.
    :param logger: logger object.
    """
    operation = get_readable_operation_name(operation)

    subject = "Delay on BUR {} Operation".format(operation)
    logger.info(subject)

    message_list = list()
    message_list.append("{} for {} is taking longer than expected."
                        .format(operation, customer_name))
    message_list.append("{} started at {} and is still running.".format(operation, start_time))
    message_list.append("Max delay time defined ({}s) was reached.".format(max_delay))

    try:
        notification_handler.send_warning_email(subject, message_list)
    except NotificationHandlerException as notification_exception:
        logger.error(notification_exception.__str__())


def get_readable_operation_name(operation):
    """
    Format Enum values to readable string.

    :param operation: name value from ScriptOperations.
    :return: formatted string.
    """
    if operation == SCRIPT_OPERATIONS.BKP_UPLOAD:
        return "Backup Upload"
    if operation == SCRIPT_OPERATIONS.BKP_DOWNLOAD:
        return "Backup Download"
    if operation == SCRIPT_OPERATIONS.RETENTION:
        return "Cleanup"
    return operation


def get_arg_parser():
    """
    Parse input arguments.

    :return: parsed arguments object.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--script_option", default=1, help=SCRIPT_OPTION_HELP)
    parser.add_argument("--number_threads",
                        default=DEFAULT_NUM_THREADS,
                        help=NUMBER_THREADS_HELP)
    parser.add_argument("--number_processors", default=DEFAULT_NUM_PROCESSORS,
                        help=NUMBER_PROCESSORS_HELP)
    parser.add_argument("--number_transfer_processors",
                        default=DEFAULT_NUM_TRANSFER_PROCS,
                        help=NUMBER_RSYNC_INSTANCES_HELP)
    parser.add_argument(LOG_ROOT_PATH_CLI, nargs='?', default=DEFAULT_LOG_ROOT_PATH,
                        help=LOG_ROOT_PATH_HELP)
    parser.add_argument("--log_level", nargs='?', default=logging.INFO, help=LOG_LEVEL_HELP)
    parser.add_argument("--backup_tag", help=BACKUP_TAG_HELP)
    parser.add_argument("--customer_name", default="", help=CUSTOMER_NAME_HELP)
    parser.add_argument("--backup_destination", nargs='?', help=BACKUP_DESTINATION_HELP)
    parser.add_argument("--rsync_ssh", default=False, help=RSYNC_SSH_HELP)
    parser.add_argument("--usage", action="store_true", help=USAGE_HELP)
    parser.add_argument("--offsite_retention", help=OFFSITE_RETENTION_HELP)
    parser.add_argument("--version", action="store_true", help=BUR_VERSION_HELP)

    return parser


def show_bur_usage():
    """Display this usage help message whenever the script is run with '--usage' argument."""
    print("""

        Usage of: '{0}'

        This message is displayed when script is run with '--usage' argument.
        ============================================================================================
                                            Overview:
        ============================================================================================
        This script aims at automating the process for off-site upload and download of
        the ENMaaS backup sets, according to the requirements from the Jira issue NMAAS-516
        (https://jira-nam.lmera.ericsson.se/browse/NMAAS-516).

        It basically does the following for each option:

        1. Upload

        1.1 Read the parameters from a configuration file to retrieve customer deployment settings.
        1.2 Validate the input arguments and the current settings.
        1.3 If a customer is not specified in the input arguments, run the upload for all
        customers defined in the configuration file. Otherwise, process just the specified customer.
        1.4 For each valid backup, encrypt the data using gpg tool and compress before uploading.

        2. Download

        2.1 Accepts the customer name, backup tag or both as input as well as the destination
        directory.
        2.2 Lists the available backup sets for a customer if no backup tag is defined.
        2.3 If a backup tag is specified, download, extract and decrypt the backup content to the
        specified location.

        3. Retention

        3.1 Delete any backup sets, other than last 3, from the offsite. Retention value can be
        set on configuration file or provided through CLI argument. CLI argument always override
        configuration file setup.

        ============================================================================================
                                    Script Flow and Exit Codes:
        ============================================================================================

        This script works as follows:

        1. Validate input from CLI and configuration file.

        2. Generate the objects needed to execute BUR.

        3. For the upload feature, do the following:
            3.1 If no customer is specified, the script will process all customers from the
            configuration file sequentially, otherwise just the informed customer will be affected.
            If a customer and a backup tag is informed, just that backup will be processed.

            3.2 The backup task is done in parallel, so that the volumes are processed and
            transferred to offsite independently. The number of process and threads used can be
            specified by CLI.

            3.3 Each process is responsible for the following task:
                - Create a thread pool to compress (gzip) and encrypt (gpg) all files inside a
                volume.
                - Archive the volume using tar.
            3.4 The already processed volumes without errors are uploaded to the offsite (rsync).

            3.5 Remove the older backups from each customer directory, according to the off-site
            retention value.

        4. For the download feature, do the following:
            4.1 If the user informs just the customer name, the system queries the offsite for
                the list of available backups.
            4.2 If the user informs just the backup tag, the actual backup path is searched and the
                system tries to download it.
            4.3 If the user informs both backup tag and customer, the system tries to download the
                actual backup folder from the off-site.
            4.4 After a successful download, the system decompress and decrypts the volumes in
                parallel.
            4.5 The downloaded backup is stored in the destination location passed by CLI.

        Regarding the upload feature, if at any point a problem happens, the process of the
        current backup stops and the error is reported via CLI. If there are other backups to be
        uploaded, BUR will try to execute them before ending the script.

        ============================================================================================
                                    E-mail notifications:
        ============================================================================================

        The notification e-mail is sent to the support team specified in the configuration file in
        the following cases:

        1. In case of success.

        SUCCESS (1): Script executed without errors.

        2. Error during the execution of BUR.

        The following error codes can be raised in case of other failures during the process:

        INVALID_INPUT (2): Error while validating input arguments or configuration file.
        FAILED_UPLOAD (3): Error while executing the upload function.
        FAILED_DOWNLOAD (4): Error while executing the download function.
        FAILED_OFFSITE_CLEANUP (5): Error while executing the cleanup function.

        3. If the upload is taking too long to execute.

        ============================================================================================
                                        Configuration File ({1}):
        ============================================================================================

        The script depends on a configuration file '{1}' for both operations Upload and Download.

        --------------------------------------------------------------------------------------------
        It must contain the following email variables:

        [SUPPORT_CONTACT]
        EMAIL_TO       Email address to send failure notifications.
        EMAIL_URL      URL of the email service.

        [GNUPG]
        GPG_USER_NAME  User name used by gpg to create a encryption key.
        GPG_USER_EMAIL Use email for gpg usage.

        [OFFSITE_CONN]
        IP              remote ip address.
        USER            server user.
        BKP_PATH        remote root path where the backups will be placed.
        BKP_DIR         remote folder name where the backups will be stored. This folder will be
                        created in the BKP_PATH if it does not exist.
        RETENTION       max value for retention of backups.

        [ONSITE_PARAMS]
        BKP_TEMP_FOLDER local temporary folder to store files during the upload process.

        [DELAY]
        BKP_MAX_DELAY maximum amount of time to wait until the support is notified.

        For example:

        [SUPPORT_CONTACT]
        EMAIL_TO=fo-enmaas@ericsson.com
        EMAIL_URL=https://172.31.2.5/v1/emailservice/send

        [GNUPG]
        GPG_USER_NAME="backup"
        GPG_USER_EMAIL="backup@root.com"

        [OFFSITE_CONN]
        IP=159.107.167.73
        USER=user_name
        BKP_PATH=/root/path/to/backup/dir
        BKP_DIR=backup_dir_name
        RETENTION=3

        [ONSITE_PARAMS]
        BKP_TEMP_FOLDER=/path/to/local/temp/folder

        [DELAY]
        BKP_MAX_DELAY=10s

        Note: Path variables should not contain quotes.
        --------------------------------------------------------------------------------------------

        --------------------------------------------------------------------------------------------
        Each customer should have a new entry in this configuration file as below:

        [CUSTOMER_NAME]
        CUSTOMER_PATH   path to the customer's volumes.

        For example:
        [CUSTOMER_0]
        CUSTOMER_PATH=/path/to/customer/backup/folder
        --------------------------------------------------------------------------------------------
        """.format(SCRIPT_FILE, CONF_FILE_NAME))

    sys.exit(SUCCESS_EXIT_CODE)


def show_bur_version():
    """Display currently installed bur version whenever the script is run with '--version'."""
    print("BUR version: {}".format(__version__))

    sys.exit(SUCCESS_EXIT_CODE)


def show_bur_arg_error(error_message=""):
    """Display an error message when the argument list provided cannot be validated."""
    print("Provided argument list is invalid due to: {}\n\nRun --usage option for help.".format(
        error_message))

    sys.exit(EXIT_CODES.INVALID_INPUT.value)


if __name__ == '__main__':
    sys.exit(main())
