##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=C0103,R0912
# invalid-name (snake_case comments)
# too-many-branches

# flake8: noqa=C901
# function is too complex

"""Module for validating all the inputs to execute BUR scripts."""
from argparse import ArgumentError
from enum import Enum
import logging
import multiprocessing
import os

from backup.backup_settings import ScriptSettings
from backup.constants import DEFAULT_NUM_PROCESSORS, LOG_SUFFIX, DEFAULT_NUM_THREADS
from backup.exceptions import BackupSettingsException, ExceptionCodes, InputValidatorsException
from backup.logger import CustomLogger
from backup.utils.fsys import create_path
from backup.utils.net import is_valid_ip
from backup.utils.remote import check_remote_path_exists, create_remote_dir


SCRIPT_OBJECTS = Enum('SCRIPT_OBJECTS', 'NOTIFICATION_HANDLER, OFFSITE_CONFIG, ONSITE_CONFIG, '
                                        'GNUPG_MANAGER, CUSTOMER_CONFIG_DICT, DELAY_CONFIG, SIZE')


def validate_get_main_logger(console_input_args, main_script_file_name, bur_operation_enum):
    """
    Validate and get the main logger object, which is created based on the selected operation.

    :param console_input_args: arguments passed to the console.
    :param main_script_file_name: name of the main script.
    :param bur_operation_enum: enumerator with the valid operations supported by BUR.
    :return: custom logger object.
    """
    try:
        operation = validate_script_option_argument(console_input_args.script_option,
                                                    bur_operation_enum.SIZE.value)

        main_log_file_name = prepare_log_file_name(operation, bur_operation_enum,
                                                   console_input_args.customer_name,
                                                   console_input_args.backup_tag)

        return CustomLogger(main_script_file_name, console_input_args.log_root_path,
                            main_log_file_name, console_input_args.log_level)

    except InputValidatorsException as exception:
        logger = CustomLogger(main_script_file_name, "")

        logger.log_error_exit("Error creating the logger object. Cause: {}."
                              .format(exception.__str__()))


def prepare_log_file_name(operation, script_operations_enum, customer_name, backup_tag):
    """
    Prepare a meaningful log file name based on the provided cli arguments.

    :param operation: the script option, refer to script_option to see the possible values.
    :param script_operations_enum: enumerator with the valid operations supported by BUR.
    :param customer_name: the provided value for customer_name, if any.
    :param backup_tag: the provided value for backup_tag, if any.
    :return: a meaningful log file name based on the required operation and the passed parameters.
    :raise InputValidatorsException: if an invalid operation is passed.
    """
    if operation == int(script_operations_enum.BKP_UPLOAD.value):
        if customer_name.strip():
            main_log_file_name = "{}_upload.{}".format(customer_name, LOG_SUFFIX)
        else:
            main_log_file_name = "all_customers_upload.{}".format(LOG_SUFFIX)

    elif operation == int(script_operations_enum.BKP_DOWNLOAD.value):
        if customer_name.strip() and backup_tag is not None and backup_tag.strip():
            main_log_file_name = \
                "{}_{}_download.{}".format(customer_name, backup_tag, LOG_SUFFIX)

        elif customer_name.strip() and (backup_tag is None or not backup_tag.strip()):
            main_log_file_name = "{}_download.{}".format(customer_name, LOG_SUFFIX)

        elif not customer_name.strip() and backup_tag is not None and backup_tag.strip():
            main_log_file_name = "{}_download.{}".format(backup_tag, LOG_SUFFIX)

        else:
            main_log_file_name = "error_download.{}".format(LOG_SUFFIX)

    elif operation == int(script_operations_enum.RETENTION.value):
        if customer_name.strip():
            main_log_file_name = "{}_retention.{}".format(customer_name, LOG_SUFFIX)
        else:
            main_log_file_name = "all_customers_retention.{}".format(LOG_SUFFIX)

    else:
        raise InputValidatorsException(ExceptionCodes.OperationNotSupported, operation)

    return main_log_file_name


def validate_log_root_path(log_root_path, default_log_root_path):
    """
    Validate the informed log root path.

    :param log_root_path: log root path to be validated.
    :param default_log_root_path: default log value.
    :return: validated log root path.
    :raise InputValidatorsException: if it could not create the path.
    """
    if log_root_path is None or not log_root_path.strip():
        log_root_path = default_log_root_path

    if not create_path(log_root_path):
        raise InputValidatorsException(ExceptionCodes.CannotCreatePath, log_root_path)

    return log_root_path


def validate_log_level(log_level):
    """
    Validate the informed log level. Sets to INFO when the informed value is invalid.

    :param log_level: log level.
    :return: validated log level.
    """
    if log_level in (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG):
        return log_level

    log_level = str(log_level)

    if str(log_level).lower() == "critical":
        log_level = logging.CRITICAL
    elif str(log_level).lower() == "error":
        log_level = logging.ERROR
    elif str(log_level).lower() == "warning":
        log_level = logging.WARNING
    elif str(log_level).lower() == "info":
        log_level = logging.INFO
    elif str(log_level).lower() == "debug":
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    return log_level


def validate_boolean_input(bool_arg):
    """
    Convert an input value into boolean.

    :param bool_arg: value to be converted into boolean.
    :return: converted value into boolean.
    """
    if isinstance(bool_arg, str):
        return bool_arg.lower() in ("yes", "true", "t", "1")

    return bool_arg


def validate_script_settings(config_file_name, script_objects, logger, customer_name=None):
    """
    Validate the config_file parsing and the objects created from it.

    :param config_file_name: BUR configuration file name.
    :param logger: logger object.
    :param script_objects: ScriptSetting objects.
    :param customer_name: customer name, if running the script just for one customer.
    :return: validated ScriptSetting object.
    :raise InputValidatorsException: if cannot validate any of script settings.
    """
    script_settings = ScriptSettings(config_file_name, logger)

    try:
        script_objects[SCRIPT_OBJECTS.NOTIFICATION_HANDLER.name] = \
            script_settings.get_notification_handler()

        script_objects[SCRIPT_OBJECTS.GNUPG_MANAGER.name] = \
            script_settings.get_gnupg_manager()

        script_objects[SCRIPT_OBJECTS.OFFSITE_CONFIG.name] = \
            script_settings.get_offsite_config()

        script_objects[SCRIPT_OBJECTS.ONSITE_CONFIG.name] = \
            script_settings.get_onsite_config()

        script_objects[SCRIPT_OBJECTS.DELAY_CONFIG.name] = \
            script_settings.get_delay_config()

        script_objects[SCRIPT_OBJECTS.CUSTOMER_CONFIG_DICT.name] = \
            script_settings.get_customer_config_dict(customer_name)

    except BackupSettingsException as exception:
        raise InputValidatorsException(parameters=exception.__str__())

    return script_objects


def validate_onsite_offsite_locations(config_file_name, script_objects, logger):
    """
    Validate if on-site and off-site location/server paths.

    :param config_file_name: BUR configuration file name.
    :param script_objects: dictionary of validated ScriptSettings objects.
    :param logger: logger object.
    :return: true if the validation succeeds.
    :raise InputValidatorsException: if validation failed for some parameter.
    """
    customer_config_dic = script_objects[SCRIPT_OBJECTS.CUSTOMER_CONFIG_DICT.name]
    offsite_config = script_objects[SCRIPT_OBJECTS.OFFSITE_CONFIG.name]

    validation_error_list = []

    validate_onsite_backup_locations(customer_config_dic, config_file_name, validation_error_list)
    validate_offsite_backup_server(offsite_config, config_file_name, logger, validation_error_list)

    if validation_error_list:
        raise InputValidatorsException(ExceptionCodes.InvalidSiteLocations, validation_error_list)

    return True


def validate_input_arguments(console_input_args, bur_operations_enum, logger):
    """
    Validate the input arguments.

    :param console_input_args: informed argument object.
    :param bur_operations_enum: BUR operations enumerator.
    :param logger: logger object.
    :raise InputValidatorsException: if validation failed for some argument.
    """
    validation_error_list = []
    validate_bur_operation_arguments(console_input_args, bur_operations_enum, validation_error_list)

    if validation_error_list:
        raise InputValidatorsException(parameters=validation_error_list)

    console_input_args.number_threads = validate_number_of_threads(
        console_input_args.number_threads, logger)

    console_input_args.number_processors = validate_number_of_processors(
        console_input_args.number_processors, logger)

    console_input_args.number_transfer_processors = validate_number_of_processors(
        console_input_args.number_transfer_processors, logger)


def validate_script_option_argument(str_script_option, script_option_enum_size):
    """
    Validate the provided value for script_option, if any.

    Raise an exception in case of an invalid operation.

    :param str_script_option: the value provided with script_option, if any.
    :param script_option_enum_size: operation enumerator size.
    :return: validated integer script operation.
    :raise InputValidatorsException: if str_script_option parameter cannot be parsed or is
    invalid operation.
    """
    try:
        operation = int(str_script_option)

        if operation <= 0 or operation >= script_option_enum_size:
            raise InputValidatorsException(ExceptionCodes.OperationNotSupported, operation)

        return operation

    except (ValueError, TypeError):
        raise InputValidatorsException(ExceptionCodes.OperationNotSupported, str_script_option)


def validate_bur_operation_arguments(console_input_args, bur_operations_enum,
                                     validation_error_list=None):
    """
    Validate script operation argument and its dependent parameters.

    If BKP_DOWNLOAD option is selected, validate the customer name and backup tag arguments.

    In case of validation error, exits with error code: INVALID_INPUT.

    :param console_input_args: input arguments to be validated.
    :param bur_operations_enum: BUR operations enumerator.
    :param validation_error_list: validation error list.
    """
    try:
        operation = validate_script_option_argument(console_input_args.script_option,
                                                    bur_operations_enum.SIZE.value)

        is_backup_tag_empty = console_input_args.backup_tag is None or not \
            console_input_args.backup_tag.strip()

        is_customer_name_empty = console_input_args.customer_name is None or not \
            console_input_args.customer_name.strip()

        if operation == int(bur_operations_enum.BKP_DOWNLOAD.value):
            if console_input_args.backup_destination is None:
                console_input_args.backup_destination = ""

        elif operation == int(bur_operations_enum.BKP_UPLOAD.value):
            if not is_backup_tag_empty and is_customer_name_empty:
                raise InputValidatorsException(ExceptionCodes.MissingCustomerNameForUpload)

    except InputValidatorsException as exception:
        if validation_error_list is None:
            validation_error_list = []

        validation_error_list.append(exception.__str__())


def validate_onsite_backup_locations(customer_config_dict, config_file_name,
                                     validation_error_list=None):
    """
    Check if the on-site paths informed in the configuration file are valid for each customer.

    In case of validation error, the message is appended to a list.

    :param customer_config_dict: dictionary with data for each customer in the configuration file.
    :param config_file_name: BUR configuration file name.
    :param validation_error_list: validation error list.
    """
    if validation_error_list is None:
        validation_error_list = []

    if not customer_config_dict.keys():
        validation_error_list.append("No customer defined in the configuration file '{}'. "
                                     "Nothing to do.".format(config_file_name))

    for customer_key in customer_config_dict.keys():
        customer_config = customer_config_dict[customer_key]
        if not os.path.exists(customer_config.backup_path):
            validation_error_list.append("Informed path for customer {} does not exist: '{}'."
                                         .format(customer_key, customer_config.backup_path))


def validate_offsite_backup_server(offsite_config, config_file_name, logger,
                                   validation_error_list=None):
    """
    Check if the off-site server is up and validate the specified path on that server.

    In case of validation error, the message is appended to a list.

    :param offsite_config: off-site config object.
    :param config_file_name: BUR configuration file name.
    :param logger: logger object.
    :param validation_error_list: validation error list.
    :return: true if off-site object is validated; false otherwise.
    """
    if validation_error_list is None:
        validation_error_list = []

    if not offsite_config:
        validation_error_list.append("Off-site parameters not defined in the configuration file "
                                     "'{}'. Nothing to do.".format(config_file_name))
        return False

    if not offsite_config.user.strip():
        validation_error_list.append("Off-site field 'user' is empty.")

    if not offsite_config.path.strip():
        validation_error_list.append("Off-site field 'path' is empty.")

    if not offsite_config.folder.strip():
        validation_error_list.append("Off-site field 'folder' is empty.")

    if not offsite_config.ip.strip():
        validation_error_list.append("Off-site field 'ip' is empty.")

    if offsite_config.retention < 0:
        validation_error_list.append("Off-site field 'retention' is invalid.")

    if not is_valid_ip(offsite_config.ip):
        validation_error_list.append("Informed off-site IP '{}' is not valid."
                                     .format(offsite_config.ip))
        return False

    if not check_remote_path_exists(offsite_config.host, offsite_config.path):
        validation_error_list.append("Informed root backup path does not exist on off-site: '{}'."
                                     .format(offsite_config.path))
        return False

    if not check_remote_path_exists(offsite_config.host, offsite_config.full_path):
        logger.warning("Remote backup path '{}' does not exist yet. Trying to create it."
                       .format(offsite_config.full_path))

        if not create_remote_dir(offsite_config.host, offsite_config.full_path):
            validation_error_list.append("Remote directory could not be created '{}'"
                                         .format(offsite_config.full_path))
        else:
            logger.info("New remote path '{}' created successfully."
                        .format(offsite_config.full_path))
    else:
        logger.info("Remote directory '{}' already exists".format(offsite_config.full_path))

    return True


def validate_number_of_threads(num_threads_to_use, logger):
    """
    Check the provided number of threads to be used if valid.

    :param num_threads_to_use: the number of threads to be checked from the input
    :param logger: logger object.
    :return: the correct number of threads to be used.
    """
    try:
        num_threads_to_use = int(num_threads_to_use)

    except (ValueError, TypeError):
        logger.warning("Invalid number of threads: {}. Changed to: {}."
                       .format(num_threads_to_use, DEFAULT_NUM_THREADS))
        return DEFAULT_NUM_THREADS

    if num_threads_to_use < 1:
        logger.warning("Invalid number of threads: {}. Changed to: {}."
                       .format(num_threads_to_use, DEFAULT_NUM_THREADS))
        return DEFAULT_NUM_THREADS

    logger.info("Valid number of threads: {}.".format(num_threads_to_use))

    return num_threads_to_use


def validate_number_of_processors(num_processors_to_use, logger):
    """
    Check the provided number of processors to be used if valid.

    If num_processors_to_use <= 0 or num_processors_to_use is bigger than available_cores,
    then the num_processors_to_use will be replaced to available_cores.

    If num_processors_to_use is invalid, it will be replaced to DEFAULT_NUM_PROCESSORS.

    :param num_processors_to_use: the number of processors to be checked from the input args.
    :param logger: logger object.
    :return: the correct number of processors to be used.
    """
    available_cores = multiprocessing.cpu_count()

    if available_cores <= 1:
        logger.warning("Low number of available processors: {}".format(available_cores))

    try:
        num_processors_to_use = int(num_processors_to_use)

    except (ValueError, TypeError):
        logger.warning("Invalid number of processors: {}. Changed to {}."
                       .format(num_processors_to_use, DEFAULT_NUM_PROCESSORS))
        num_processors_to_use = DEFAULT_NUM_PROCESSORS

    if num_processors_to_use <= 0 or num_processors_to_use > available_cores:

        logger.warning("Invalid number of processors: {0}. Changed to {1}. Available cores: {1}."
                       .format(num_processors_to_use, available_cores))
        num_processors_to_use = available_cores

    else:
        logger.info("Number of processors: {} is valid. Available cores: {}"
                    .format(num_processors_to_use, available_cores))

    return num_processors_to_use


def validate_offsite_retention_argument(offsite_retention):
    """
    Validate the retention value.

    :param offsite_retention: how many backups should be kept at off-side.
    :return: if a positive integer, then return it. None otherwise.
    """
    try:
        retention = int(offsite_retention)

        if retention < 0:
            return None

        return retention

    except (ValueError, TypeError):
        return None


def validate_argument_list(get_arg_parser, log_root_path, arg_list=None):
    """
    Validate arguments provided to the system.

    The arguments are taken from command line or from the argument list parameter if it is not
    empty.

    :param get_arg_parser: argument parser function.
    :param log_root_path: log file path.
    :param arg_list: argument list to override the cli entered arguments.
    :return: validated argument object.
    :raise InputValidatorsException: if cannot parse the values from arg_list.
    """
    try:
        if arg_list is None:
            args = get_arg_parser().parse_args()
        else:
            args = get_arg_parser().parse_args(arg_list)
    except ArgumentError as error:
        raise InputValidatorsException(ExceptionCodes.CannotParseValue, [arg_list, error.__str__()])

    args.log_root_path = validate_log_root_path(args.log_root_path, log_root_path)
    args.offsite_retention = validate_offsite_retention_argument(args.offsite_retention)
    args.log_level = validate_log_level(args.log_level)
    args.rsync_ssh = validate_boolean_input(args.rsync_ssh)

    return args
