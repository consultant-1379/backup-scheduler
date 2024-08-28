##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=too-few-public-methods

"""Reading the YAML file to provide a list files and folder required in Testing Scenario."""

import datetime
import os

import tests.system.scenario_simulator.constants as constants
import yaml


class Layout:
    """Holds structure configuration nodes."""

    def __init__(self, conf_path):
        with open(conf_path, 'r') as stream:
            data = yaml.load(stream)
            self.nodes = data[constants.SIM_PLAN_LAYOUT]
        self.depth_limit = 5

        self.current_customer = -1
        self.current_vol = -1
        self.current_backup_id = -1

    def get_paths(self):
        """Get the node paths as a list."""
        output = {constants.SIM_PLAN_FILES: [], constants.SIM_PLAN_FOLDERS: [],
                  constants.SIM_PLAN_PROCESS: []}
        self.__get_paths(output, self.nodes, 0, os.path.sep)
        return output

    def __get_paths(self, output, nodes, depth, parent):
        """
        Extract file and information detail from the loaded yaml file.

        :param output: a dictionary data structure to hold extracted details
        :param nodes: loaded data from yaml scenario file
        :param depth: folder level in the structure
        :param parent: folder above the current processing file or folder
        """
        if isinstance(nodes, dict):
            for key, value in nodes.items():
                self.__update_counters(key)
                if not isinstance(value, (dict, list, str)):
                    return

                if key != 'file':
                    path = Layout.__create_path_string(parent, key)
                    output[constants.SIM_PLAN_FOLDERS].append(path)

                    if self.__has_valid_process_suffix(str(key)):
                        output[constants.SIM_PLAN_PROCESS].append(path)

                    self.__get_paths(output, value, depth + 1, path)
                else:
                    output[constants.SIM_PLAN_FILES].append(
                        {
                            constants.FILE_DESCRIPTOR_BACKUP_ID: self.current_backup_id,
                            constants.FILE_DESCRIPTOR_VOL_ID: self.current_vol,
                            constants.FILE_DESCRIPTOR_CUSTOMER_ID: self.current_customer,
                            constants.FILE_DESCRIPTOR_FILE_PATH: parent,
                            constants.FILE_DESCRIPTOR_FILE_NAME:
                                nodes[key].get(constants.YAML_FILE_NAME),
                            constants.FILE_DESCRIPTOR_FILE_SIZE:
                                nodes[key].get(constants.YAML_FILE_SIZE, None),
                            constants.FILE_DESCRIPTOR_FILE_CONTENT:
                                nodes[key].get(constants.YAML_FILE_CONTENT, ''),
                            constants.FILE_DESCRIPTOR_FILE_TYPE:
                                nodes[key].get(constants.YAML_FILE_TYPE,
                                               constants.TEXT_FILE_TYPE_KEY)
                        })

        elif isinstance(nodes, list):
            for item in nodes:
                if isinstance(item, (dict, list)):
                    self.__get_paths(output, item, depth + 1, parent)

    def __update_counters(self, key):
        """
        Collect class counters related to the creation of metadata file.

        :param key: file or folder name
        """
        if isinstance(key, datetime.date):
            self.current_vol = -1
            self.current_backup_id += 1

        if isinstance(key, str):
            if not key.find(constants.VOLUME_FOLDER):
                self.current_vol += 1
            elif not key.find(constants.CUSTOMER_DEPLOYMENT_FOLDER):
                self.current_customer += 1
                self.current_backup_id = -1
                self.current_vol = -1

    @staticmethod
    def __create_path_string(parent, child):
        """
        Construct a path by joining with os filesystem separator.

        :param parent: folder above the current processing file or folder
        :param child: child folder name

        :return: complete path from joining parent and child file or folder
        """
        parent = str(parent)
        child = str(child)

        if not parent or parent == os.path.sep:
            path = child

        else:
            path = os.path.join(str(parent), str(child))

        return path

    @staticmethod
    def __has_valid_process_suffix(node):
        """
        Check the suffix of the node name for supported processing tags.

        :param node: folder name in the layout plan.
        :return: True if the node has a valid suffix list; False otherwise.
        """
        if not node.strip():
            return False

        suffix_list = os.path.basename(node).split('.')[1:]

        if not suffix_list:
            return False

        for suffix in suffix_list:
            if suffix not in constants.SUPPORTED_PROCESSING_STEPS:
                print("Unsupported operation was detected in the layout '{}'. Ignoring "
                      "it.".format(node))

                return False

        return True
