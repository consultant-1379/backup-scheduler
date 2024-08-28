##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""This script holds required common helpful functionality to be used in System tests."""

import glob
import os
import shutil

from tests.system.config import generator
from tests.system.scenario_simulator import layout_builder, layout_parser
from tests.system.scenario_simulator.constants import SIM_PLAN_FILES, SIM_PLAN_FOLDERS, \
    SIM_PLAN_PROCESS
from tests.system.utils.constants import CONFIG_FILE, SIM_FOLDER, SYS_TEST_LOG_PATH

from backup.main import main


def find_file(path, filename):
    """
    Find a filename inside given path.

    :param path: Path to look for the file.
    :param filename: Name of the file to look for.

    :return: Found file otherwise None.
    """
    found = [f for f in glob.iglob(os.path.join(path, filename))]
    if found:
        return found[0]
    return None


def frame(name, style_character='*'):
    """
    Frame the name with the style_character.

    :param name: Given text to be framed.
    :param style_character: Given characters to make frame.

    :return: A framed text using the required character.
    """
    line = style_character * (len(name) + 4)
    print(line)
    print('{0} {1} {0}'.format(style_character, name))
    print(line)


def create_layout(root_path, layout_file):
    """
    Create and prepare filesystem layout required for testing.

    :param root_path: filesystem context for layout creating
    :param layout_file: layout yaml file to prepare filesystem accordingly

    :return: A plan containing files and folders in the layout
    """
    valid_layout = layout_parser.Layout(layout_file)
    plan = valid_layout.get_paths()
    layout_builder.mk_dirs(root_path, plan[SIM_PLAN_FOLDERS])
    layout_builder.mk_files(root_path, plan[SIM_PLAN_FILES])
    layout_builder.process_path_list(root_path, plan[SIM_PLAN_PROCESS])

    return plan


def default_upload_operation(customer_id):
    """
    No customer version of the upload operation execution command.

    :param customer_id: Uploading the given customer id backups.

    :return: Execution code of the operation.
    """
    argument_options = [
        '--script_option', '1',
        '--customer_name', 'CUSTOMER_{}'.format(customer_id),
        '--rsync_ssh', 'True',
        '--log_root_path', SYS_TEST_LOG_PATH]

    return main(argument_options)


def upload_operation_no_customer():
    """
    No customer version of the upload operation execution command.

    :return: execution code of the operation.
    """
    argument_options = [
        '--script_option', '1',
        '--rsync_ssh', 'True',
        '--log_root_path', SYS_TEST_LOG_PATH]

    return main(argument_options)


def retention_operation():
    """
    Execute the retention operation only for all customers.

    :return: Execution code of the operation.
    """
    argument_options = [
        '--script_option', '3',
        '--rsync_ssh', 'True',
        '--log_root_path', SYS_TEST_LOG_PATH]

    return main(argument_options)


def download_operation(customer_id, backup_tag, restore_path):
    """
    Execute default download operation command.

    :param customer_id: Download the given customer id backups.
    :param backup_tag: Requesting tag to be downloaded.
    :param restore_path: Download operation output location.

    :return: Execution code of the operation.
    """
    customer_name = 'CUSTOMER_{}'.format(customer_id)

    if not customer_id.strip():
        customer_name = ""

    download_argument_options = [
        '--script_option', '2',
        '--customer_name', customer_name,
        '--rsync_ssh', 'True',
        '--backup_tag', backup_tag,
        '--backup_destination', restore_path,
        '--log_root_path', SYS_TEST_LOG_PATH]

    return main(download_argument_options)


def start_up_test_module(name):
    """Create custom BUR system log path once the process started."""
    frame('module %s started' % name)
    if not os.path.exists(SYS_TEST_LOG_PATH):
        os.makedirs(SYS_TEST_LOG_PATH)
    generator.generate(CONFIG_FILE, customer_count=2)


def finish_test_module(name):
    """Remove custom BUR system log path when finishing the process."""
    frame('module %s finished' % name)
    if os.path.exists(SYS_TEST_LOG_PATH):
        shutil.rmtree(SYS_TEST_LOG_PATH)
    generator.replace_to_origin_conf(CONFIG_FILE)


def create_bur_env_layout(test_method_name, scenario_layout):
    """Create bur environment layout."""
    frame(test_method_name)
    scenario_file = os.path.join(os.path.dirname(__file__), os.pardir, scenario_layout)
    return create_layout(SIM_FOLDER, scenario_file)
