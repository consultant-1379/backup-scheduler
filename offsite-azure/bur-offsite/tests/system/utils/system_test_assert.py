##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""BUR custom assertion for system-wide operation testing."""

import os
import re
import tarfile

from tests.system.scenario_simulator import layout_builder
from tests.system.scenario_simulator.constants import FILE_DESCRIPTOR_BACKUP_ID, \
    FILE_DESCRIPTOR_CUSTOMER_ID, FILE_DESCRIPTOR_FILE_NAME, FILE_DESCRIPTOR_FILE_PATH
from tests.system.utils import helpers
from tests.system.utils.constants import BACKUP_TEMP_PATH, BUR_SIM_ENV_PATH, \
    CUSTOMER_FOLDER_PREFIX, MOCK_OFFSITE_RELATIVE_PATH, VOL_FOLDER_PREFIX

from backup.constants import BUR_FILE_LIST_DESCRIPTOR_FILE_NAME, \
    BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME, DEFAULT_OFFSITE_RETENTION, GPG_SUFFIX, GZ_SUFFIX, \
    SUCCESS_FLAG_FILE, TAR_SUFFIX
from backup.utils.fsys import load_pickle_file


class SystemTestAssertions:
    """Custom defined assertion for readability of system test."""

    @staticmethod
    def assert_backup_temp_is_empty(customer_id):
        """
        Verify if backup temp folder is empty.

        :param customer_id: Files related to the given customer id.
        :raise: AssertionError in case left over temp files not removed.
        """
        if os.listdir(os.path.join(BACKUP_TEMP_PATH, CUSTOMER_FOLDER_PREFIX + customer_id)):
            raise AssertionError('Backup Temp folder not empty')

    def assert_files_on_azure_are_valid(self, test_folder, upload_file_spec, customer_id):
        """
        Check files in the uploaded files as follow.

        1- matching volume compressed file with corresponding folder on NFS.
        2- check vol descriptor file content if it included with volume folder names.
        3- check backup_of file on azure and it's descriptor content.
        4- reading compressed vol files and included filenames with.
        those inside corresponding volume folder in NFS.

        :param test_folder: bur-env path as mock azure location.
        :param upload_file_spec: uploaded files specifications dict.
        :param customer_id: required customer id in testing.
        """
        customer_spec = [f for f in upload_file_spec
                         if f[FILE_DESCRIPTOR_CUSTOMER_ID] == customer_id]
        last_backup_id = customer_spec[-1][FILE_DESCRIPTOR_BACKUP_ID]
        last_backup_id_spec = {
            item[FILE_DESCRIPTOR_FILE_PATH]
            for item in customer_spec
            if item[FILE_DESCRIPTOR_BACKUP_ID] == last_backup_id and 'volume_file' in item['name']
        }

        vols = self.__get_vols_from_descriptor(test_folder, customer_id)
        self.__check_compressed_vol_files_on_azure(customer_id, last_backup_id_spec,
                                                   test_folder, vols)
        self.__check_backup_file_on_azure(test_folder, customer_id)
        self.__check_bur_descriptor_on_azure(test_folder, customer_id)
        self.__check_volume_content_is_compressed(test_folder, customer_id,
                                                  customer_spec)

    @staticmethod
    def assert_downloaded_backup_is_valid(backup_path, download_path, tag, customer_id):
        """
        Match downloaded and backup with with each other.

        :param backup_path: Backup files location in the filesystem.
        :param download_path: Location of files after downloading backups.
        :param tag: backup tag label.
        :param customer_id: Customer id to check retention against.

        :return: True if expected processes number match with the fact in log.
        """
        for root, _, filenames in os.walk(backup_path):
            for filename in filenames:
                download_file = os.path.join(download_path,
                                             CUSTOMER_FOLDER_PREFIX + customer_id,
                                             tag, os.path.basename(root)
                                             if VOL_FOLDER_PREFIX in root else '',
                                             filename)
                if not os.path.exists(download_file):
                    raise AssertionError('file {} not found in restoration location {} '
                                         .format(filenames, download_path))

                backup_file = os.path.join(root, filename)
                if not SystemTestAssertions.__is_files_equal(backup_file, download_file):
                    raise AssertionError('backup file {} not matched with restored version {}'
                                         .format(backup_file, download_file))

    @staticmethod
    def assert_retention_is_valid(customer_id, retention=DEFAULT_OFFSITE_RETENTION):
        """
        Check the validity of retention on offsite.

        Ignore empty backup folders if any.

        :param customer_id: customer id to check retention against.
        :param retention: valid number of backups on offsite.
        """
        customer_offsite_path = os.path.join(BUR_SIM_ENV_PATH, MOCK_OFFSITE_RELATIVE_PATH,
                                             CUSTOMER_FOLDER_PREFIX + customer_id)

        bkp_dir_list = [os.path.join(customer_offsite_path, bkp_dir) for bkp_dir in os.listdir(
            customer_offsite_path)]

        bkp_dir_list = filter(lambda bkp_path: len(os.listdir(bkp_path)) > 0, bkp_dir_list)

        backup_count = len(bkp_dir_list)

        if backup_count != retention:
            raise AssertionError('Invalid retention. current backup count: {} vs expected: {}'
                                 .format(backup_count, retention))

    @staticmethod
    def assert_backups_exist(customer_id, bkp_name_list):
        """
        Check if the list of backup tags exists on offsite.

        :param customer_id: customer id to check.
        :param bkp_name_list: list og backup tags to be checked.
        """
        customer_offsite_path = os.path.join(BUR_SIM_ENV_PATH, MOCK_OFFSITE_RELATIVE_PATH,
                                             CUSTOMER_FOLDER_PREFIX + customer_id)

        for bkp_name in bkp_name_list:
            bkp_list = os.listdir(customer_offsite_path)
            if bkp_name not in bkp_list:
                raise AssertionError(
                    'Backup \'{}\' was expected to be found on off-site. List of backups found : {}'
                    .format(bkp_name, bkp_list))

    @staticmethod
    def __is_files_equal(file1, file2):
        """Check given files equality by comparing their md5 value."""
        file1_md5_val = layout_builder.get_file_md5(file1)
        file2_md5_val = layout_builder.get_file_md5(file2)
        return file1_md5_val == file2_md5_val

    @staticmethod
    def __is_vol_in_descriptor(filename, vols):
        """
        Check if vol descriptor list content matches with a folder name in filename.

        :param filename: A volume folder path including files to backup.
        :param vols: List of volume name in vol descriptor file.

        :return: True if found one otherwise False.
        """
        return any(ext in filename for ext in vols)

    def __get_vols_from_descriptor(self, test_folder, customer_id):
        """
        Get a list of volume names from it's descriptor file.

        :param test_folder: Bur-env path as mock azure location.
        :param customer_id: Required customer id in testing.

        :return: A list includeing volume names inside vol descriptor.
        """
        vol_descriptor_file = self.__get_vol_descriptor_on_azure(test_folder, customer_id)
        out = load_pickle_file(vol_descriptor_file)
        return out

    @staticmethod
    def __check_bur_descriptor_on_azure(test_folder, customer_id):
        """
        Find bur file descriptor offsite.

        :param test_folder: Testing context location.
        :param customer_id: Given customer id to look for.
        """
        vol_desc_path = os.path.join(test_folder, MOCK_OFFSITE_RELATIVE_PATH,
                                     CUSTOMER_FOLDER_PREFIX + str(customer_id), '**')
        expected_bur_desc_content = [SUCCESS_FLAG_FILE]
        bur_descriptor_file = helpers.find_file(vol_desc_path, BUR_FILE_LIST_DESCRIPTOR_FILE_NAME)
        if not bur_descriptor_file:
            raise AssertionError('{} descriptor file not found for customer {}'
                                 .format(BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME, customer_id))
        content = load_pickle_file(bur_descriptor_file)

        if len(content) != 1 and content != expected_bur_desc_content:
            raise AssertionError('Invalid content in descriptor file {}'.format(
                bur_descriptor_file))

    @staticmethod
    def __get_vol_descriptor_on_azure(test_folder, customer_id):
        """
        Find vol descriptor file offsite.

        :param test_folder: Testing context location.
        :param customer_id: Given customer id to look for.
        """
        vol_desc_path = os.path.join(test_folder, MOCK_OFFSITE_RELATIVE_PATH,
                                     CUSTOMER_FOLDER_PREFIX + str(customer_id), '**')
        filename = helpers.find_file(vol_desc_path, BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME)

        if filename:
            return filename

        raise AssertionError('Vol descriptor file {} not found for customer {}'.format(
            BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME, customer_id))

    def __check_compressed_vol_files_on_azure(self,
                                              customer_id, last_backup_id_spec, test_folder, vols):
        """
        Check  volume folder onsite with offsite.

        :param customer_id: Customer id for which vol file validation is done.
        :param last_backup_id_spec: Last backup id on NFS.
        :param test_folder:  Bur-env path as mock azure location.
        :param vols: Vols name list loaded from descriptor file.
        """
        for file_spec in last_backup_id_spec:
            match = re.search(r'\d{4}-\d{2}-\d{2}.*', file_spec)
            backup_tag_vol_path = match.group()
            upload_path = os.path.join(test_folder,
                                       MOCK_OFFSITE_RELATIVE_PATH,
                                       CUSTOMER_FOLDER_PREFIX + str(customer_id),
                                       backup_tag_vol_path + '.' + TAR_SUFFIX)

            self.__is_vol_in_descriptor(upload_path, vols)

            if not os.path.exists(upload_path):
                raise AssertionError('Volume file {} missing.'.format(
                    os.path.basename(upload_path)))

    @staticmethod
    def __check_backup_file_on_azure(test_folder, customer_id):
        """
        Check the BACKUP_OK and bur descriptor file.

        :param test_folder: Bur-env path as mock azure location.
        :param customer_id: Required customer id in testing.
        """
        backup_path = os.path.join(test_folder, MOCK_OFFSITE_RELATIVE_PATH,
                                   CUSTOMER_FOLDER_PREFIX + str(customer_id), '**')
        filename = helpers.find_file(backup_path, SUCCESS_FLAG_FILE)
        if not filename:
            raise AssertionError("{} file not found in azure mock"
                                 .format(SUCCESS_FLAG_FILE))

    @staticmethod
    def __check_volume_content_is_compressed(test_folder, customer_id, spec):
        """
        Validate volume compressed file content to have all the corresponding files on NFS.

        :param test_folder: Bur-env path as mock azure location.
        :param customer_id: Required customer id in testing.
        :param spec: List of dict with details of each files on NFS.
        """
        last_backup_id = spec[-1][FILE_DESCRIPTOR_BACKUP_ID]
        azure_mock_path_to_customer_folder = os.path.join(test_folder,
                                                          MOCK_OFFSITE_RELATIVE_PATH,
                                                          CUSTOMER_FOLDER_PREFIX +
                                                          str(customer_id))
        backup_tag_date = re.search(r'\d{4}-\d{2}-\d{2}',
                                    spec[-1][FILE_DESCRIPTOR_FILE_PATH]).group()

        spec_for_vol = {
            os.path.join(os.path.basename(
                f[FILE_DESCRIPTOR_FILE_PATH]), f[FILE_DESCRIPTOR_FILE_NAME])
            for f in spec
            if f[FILE_DESCRIPTOR_BACKUP_ID] == last_backup_id and 'volume' in f[
                FILE_DESCRIPTOR_FILE_PATH]
        }

        for backup_file in spec_for_vol:
            tar_file = os.path.join(azure_mock_path_to_customer_folder,
                                    backup_tag_date,
                                    os.path.dirname(backup_file) + '.' + TAR_SUFFIX)
            tar = tarfile.open(tar_file)
            looking_file = backup_file + '.'.join(['', GZ_SUFFIX, GPG_SUFFIX])

            if looking_file not in tar.getnames():
                raise AssertionError('file {} not found in the compressed file {}'
                                     .format(looking_file, tar_file))
