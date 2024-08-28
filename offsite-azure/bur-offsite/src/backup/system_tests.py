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

# pylint: disable-all
# flake8: noqa

import os
import sys
import time
import argparse
from subprocess import Popen
from logger import CustomLogger
from backup.utils.fsys import create_path, get_home_dir
from backup.utils.datetime import format_time

OPERATION_UPLOAD = "1"
OPERATION_DOWNLOAD = "2"

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

OUTPUT_ROOT_PATH = os.path.join(get_home_dir(), "backup")

DEFAULT_DOWNLOAD_PATH = "/data1/rpcbackups/staging04/bur-test/download_test"
# DEFAULT_LOGS_PATH = "/data1/rpcbackups/staging04/bur-test/bur-logs"
DEFAULT_LOGS_PATH = OUTPUT_ROOT_PATH

global download_folder
download_folder = ""

global log_folder
log_folder = ""

global logger
logger = CustomLogger(SCRIPT_FILE, "")

global num_processes
num_processes = 5

global num_threads
num_threads = 5

global rsync_ssh
rsync_ssh = False


def run_popen(command_list, shell=False):
    if not command_list:
        return None

    if not shell:
        command_list += ["--number_processors", num_processes, "--number_threads", num_threads,
                         "--rsync_ssh", rsync_ssh]

        logger.info("Running command list: {}.".format(command_list))

        with open(os.devnull, "w") as devnull:
            return Popen(command_list, stdout=devnull, stderr=devnull)

    command = ""
    for cmd_item in command_list:
        command += cmd_item + " "

    command += " --number_processors {} --number_threads {} --rsync_ssh {}"\
        .format(num_processes, num_threads, rsync_ssh)

    logger.info("Running command: {}.".format(command))

    return Popen(command, shell=True)


def run_bur_process(param_list=[], verbose=False):
    full_cmd = ["bur"] + param_list + ["--do_cleanup", "0"]

    return run_popen(full_cmd, verbose)


def get_bur_upload_single_instance_process(customer_name="", verbose=False):
    cmd_par = []
    if customer_name.strip():
        cmd_par = ["--script_option", OPERATION_UPLOAD, "--customer_name", customer_name,
                   "--log_root_path", os.path.join(log_folder, customer_name)]

    return run_bur_process(cmd_par, verbose)


def get_bur_download_single_instance_process(backup_tag="", verbose=False):
    if not backup_tag.strip():
        return None

    cmd_par = ["--script_option", OPERATION_DOWNLOAD, "--backup_destination", download_folder,
               "--backup_tag", backup_tag, "--log_root_path", os.path.join(log_folder, backup_tag)]

    return run_bur_process(cmd_par, verbose)


def execute_bur_upload_single_instance(customer_name="", verbose=False):
    p = get_bur_upload_single_instance_process(customer_name, verbose)
    if p is not None:
        p.wait()


def execute_bur_download_single_instance(backup_tag="", verbose=False):
    p = get_bur_download_single_instance_process(backup_tag, verbose)
    if p is not None:
        p.wait()


def execute_bur_multiple_instances(operation="", input_list=[], verbose=False):
    if not operation.strip():
        logger.error("Empty operation.")
        return

    if operation == OPERATION_DOWNLOAD:
        execute_bur_function = get_bur_download_single_instance_process
    elif operation == OPERATION_UPLOAD:
        execute_bur_function = get_bur_upload_single_instance_process
    else:
        logger.error("Invalid operation: {}.".format(operation))
        return

    instance_dic = {}
    for input_value in input_list:
        input_value = input_value.strip()
        if input_value in instance_dic.keys():
            logger.warning("Ignoring repeated value: {}.".format(input_value))
            continue

        instance_dic[input_value] = execute_bur_function(input_value, verbose)

    if len(instance_dic.keys()) > 0:
        check_alive_process(instance_dic)


def check_alive_process(process_dic):
    while True:
        alive_process_dic = {}
        for key in process_dic.keys():
            if process_dic[key] is None:
                continue

            if process_dic[key].poll() is None:
                alive_process_dic[key] = process_dic[key]
            else:
                logger.info("Process has finished: {}.".format(key))

        if len(alive_process_dic.keys()) == 0:
            break

        process_dic = alive_process_dic


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--test_option", default=1,
                        help="Execute single (1) or multiple instance (2) test.")
    parser.add_argument("--num_thrds", default=5)
    parser.add_argument("--num_proc", default=5)
    parser.add_argument("--customer_list",
                        help="List of customer names to execute the test (e.g. c1, c2, c3).")
    parser.add_argument("--backup_tag_list",
                        help="List of backup tags to execute the test (e.g. c1, c2, c3).")
    parser.add_argument("--download_destination", nargs='?', default=DEFAULT_DOWNLOAD_PATH)
    parser.add_argument("--log_root_path", default=DEFAULT_LOGS_PATH,
                        help="Specify a valid path to store the logs.")
    parser.add_argument("--rsync_ssh", default=False, help="use rsync over ssh or daemon.")
    parser.add_argument("--verbose", default=False, help="Shows BUR logs.")
    parser.add_argument("--usage", action="store_true", help="Display detailed help.")

    args = parser.parse_args()

    if args.usage:
        logger.log_info("Example of usage:\n\n"
                        "(1) Running sequential upload for CUSTOMER_0 and CUSTOMER_1, "
                        "followed by a sequential download of backup tags 2018 and 2019:\n\n"
                        "    python system_tests.py --customer_list \"CUSTOMER_0, CUSTOMER_1\" "
                        "--backup_tag_list \"2018, 2019\" --test_option 1 --log_root_path "
                        "\"path_to_logs\" --download_destination \"path_to_download\" ""\n\n"
                        "(2) To run parallel upload followed by parallel download, "
                        "just use --test_option 2.\n\n"
                        "(3) To see the stdout from BUR use --verbose True.\n")
        sys.exit(1)

    backup_tag_list = []

    try:
        test_option = int(args.test_option)

        if not args.log_root_path.strip():
            raise Exception("--log_root_path should not be empty.")

        if not create_path(args.log_root_path):
            raise Exception("--log_root_path '{}' could not be created.".format(args.log_root_path))

        log_folder = args.log_root_path

        if args.customer_list is None:
            raise Exception("--customer_list should not be empty.")

        customer_list = str(args.customer_list).split(",")

        if test_option != 3:  # if the option is not "upload without download chain".

            if args.backup_tag_list is None:
                raise Exception("--backup_tag_list should not be empty.")

            backup_tag_list = str(args.backup_tag_list).split(",")

            if args.download_destination is not None:
                download_folder = str(args.download_destination)
                if not download_folder.strip():
                    raise Exception("--download_destination, can't be empty ")
            else:
                raise Exception("--download_destination is null.")

            starts_with_dot = str(download_folder)[0] == '.'
            absolute_path = os.path.isabs(download_folder)
            if not starts_with_dot and not absolute_path:
                raise Exception("--download_destination, is a path, it should start with '.' '/'")

        verbose = False
        if str(args.verbose).lower() in ("yes", "true", "t", "1"):
            verbose = True

        num_processes = int(args.num_proc)
        num_threads = int(args.num_thrds)

        rsync_ssh = False
        if str(args.rsync_ssh).lower() in ("yes", "true", "t", "1"):
            rsync_ssh = True

        if test_option == 3:
            logger.log_info("Performing system tests with the following data: Customer list: {}"
                            .format(customer_list))
        else:
            logger.log_info("Performing system tests with the following data: Customer list: {}, "
                            "Backup tag list: {}.".format(customer_list, backup_tag_list))

    except Exception as e:
        logger.log_error_exit("Invalid input value due to: {}".format(e), -1)

    ts = time.time()

    if int(args.test_option) == 1:
        logger.log_info("Run backup upload single instance.")

        for customer in customer_list:
            customer = customer.strip()
            logger.log_info("Running backup upload for customer {}.".format(customer))
            execute_bur_upload_single_instance(customer, verbose)

        logger.log_info("The whole upload procedure finished.")

        logger.log_info("Run backup download single instance.")
        for backup_tag in backup_tag_list:
            backup_tag = backup_tag.strip()
            logger.log_info("Running backup download for tag {}.".format(backup_tag))
            execute_bur_download_single_instance(backup_tag, verbose)

    elif int(args.test_option) == 2:
        logger.log_info("Run backup upload parallel.")
        execute_bur_multiple_instances(OPERATION_UPLOAD, customer_list, verbose)

        logger.log_info("The whole upload procedure finished.")

        logger.info("Run backup download parallel.")
        execute_bur_multiple_instances(OPERATION_DOWNLOAD, backup_tag_list, verbose)

    elif int(args.test_option) == 3:
        logger.log_info("Run backup upload single instance(without upload-download chain).")

        for customer in customer_list:
            customer = customer.strip()
            logger.log_info("Running backup upload for customer {}.".format(customer))
            execute_bur_upload_single_instance(customer, verbose)

    elif int(args.test_option) == 4:  # useful for large_full backups test cases.
        logger.log_info("Run backup download single instance(without upload-download chain).")
        for backup_tag in backup_tag_list:
            backup_tag = backup_tag.strip()
            logger.log_info("Running backup download for tag {}.".format(backup_tag))
            execute_bur_download_single_instance(backup_tag, verbose)

    te = time.time()
    sys_test_time = te - ts
    logger.info("Total time to complete the system test: {}".format(format_time(sys_test_time)))
    logger.info("System test finished!!!")
