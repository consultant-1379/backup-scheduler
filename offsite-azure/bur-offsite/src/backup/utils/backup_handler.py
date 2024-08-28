##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=too-many-return-statements

"""Module is for backup handling utility functions."""

import glob
import json
import os

from backup.constants import BACKUP_META_FILE, BLOCK_SIZE_MB_STR, GENIE_VOL_BKPS_DEPLOYMENT, \
    META_DATA_KEYS, METADATA_FILE_SUFFIX, SUCCESS_FLAG_FILE
from backup.exceptions import ExceptionCodes, UtilsException
from backup.utils.fsys import get_free_disk_space, get_size_on_disk, is_dir, remove_path
from backup.utils.remote import get_remote_folder_size


def check_local_disk_space_for_upload(local_backup_path, temp_backup_path, logger):
    """
    Check whether the disk onsite has enough free space to process backup upload.

    :param local_backup_path: backup path to be processed.
    :param temp_backup_path: temporary backup directory.
    :param logger: logger object.
    :return: true if success.
    :raise UtilsException: if there is no free space enough available.
    """
    free_disk_space_onsite_mb = get_free_disk_space(temp_backup_path)

    bkp_size_mb = get_size_on_disk(local_backup_path)

    if free_disk_space_onsite_mb <= bkp_size_mb:
        error_params = ["Path: {}.".format(temp_backup_path),
                        "Required: {}{}.".format(bkp_size_mb, BLOCK_SIZE_MB_STR),
                        "Available: {}{}.".format(free_disk_space_onsite_mb, BLOCK_SIZE_MB_STR)]
        raise UtilsException(ExceptionCodes.NotEnoughFreeDiskSpace, error_params)

    logger.info("Required space to store temporary backup data in '{0}': {1}{2}. Available space "
                "{3}{2}."
                .format(temp_backup_path, bkp_size_mb, BLOCK_SIZE_MB_STR,
                        free_disk_space_onsite_mb))

    return True


def check_local_disk_space_for_download(backup_path_offsite, host, bkp_download_path, logger):
    """
    Check whether the disk onsite has enough free space to download the backup from offsite.

    :param backup_path_offsite: backup path to be downloaded from offsite.
    :param host: offsite machine to connect to, OFFSITE_USERNAME@OFFISTE_IP.
    :param bkp_download_path: the destination path where the downloaded backup will be stored.
    :param logger: logger object.
    :return: true if success.
    :raise UtilsException: if there is no free space enough available.
    """
    free_disk_space_onsite_mb = get_free_disk_space(bkp_download_path)

    bkp_size_offsite_mb = get_remote_folder_size(host, backup_path_offsite)

    if free_disk_space_onsite_mb <= bkp_size_offsite_mb:
        error_params = ["Path: {}.".format(bkp_download_path),
                        "Required: {}{}.".format(bkp_size_offsite_mb, BLOCK_SIZE_MB_STR),
                        "Available: {}{}.".format(free_disk_space_onsite_mb, BLOCK_SIZE_MB_STR)]
        raise UtilsException(ExceptionCodes.NotEnoughFreeDiskSpace, error_params)

    logger.info("Required space to download backup '{0}': {1}{2}. Available space {3}{2}."
                .format(backup_path_offsite, bkp_size_offsite_mb, BLOCK_SIZE_MB_STR,
                        free_disk_space_onsite_mb))

    return True


def check_is_processed_volume(volume_path, logger):
    """
    Check if the volume is valid and completely downloaded against its metadata file.

    If the volume folder exists but cannot be validated, remove it from the system.

    :param volume_path: path to the volume.
    :param logger: logger object.
    :return: true if the volume exists and was validated, false otherwise.
    """
    if not os.path.exists(volume_path):
        return False

    if not validate_volume_metadata(volume_path, logger):
        remove_path(volume_path)
        return False

    return True


def validate_backup_per_volume(deployment_label, backup_path, logger):
    """
    Validate the volumes and metadata file inside the backup_path folder.

    :param deployment_label: deployment label or customer name.
    :param backup_path: backup path.
    :param logger: logger object.
    :return: true, if the backup was correctly validated, false, otherwise.
    """
    logger.info("Validating backup '{}'.".format(backup_path))

    backup_structure = {'files': [], 'folders': []}

    for item in os.listdir(backup_path):
        if os.path.isfile(os.path.join(backup_path, item)):
            backup_structure['files'].append(item)
        else:
            backup_structure['folders'].append(item)

    report_unexpected_files_presence(backup_structure, logger)

    if deployment_label == GENIE_VOL_BKPS_DEPLOYMENT:
        validate_dispatcher = [is_backup_ok_valid]
    else:
        validate_dispatcher = [is_backup_ok_valid,
                               is_backup_volume_valid]

    for validation_function in validate_dispatcher:
        if not validation_function(backup_path, backup_structure, logger):
            return False

    logger.info("Successful validation of backup '{}' .".format(backup_path))
    return True


def is_backup_volume_valid(customer_backup_path, backup_structure, logger):
    """
    Validate volumes inside a customer tag folder.

    :param customer_backup_path: Path to a customer tag.
    :param backup_structure: A dict contains files and folders list.
    :param logger: Logger instance to use for logging.
    :return: True if success; False otherwise.
    """
    if not is_customer_backup_path_exist(customer_backup_path, logger):
        return False

    if not backup_structure['folders']:
        logger.warning('No volume found inside the backup: {}.'.format(customer_backup_path))
        return False

    logger.info('Volumes to be validated are: {}'.format(backup_structure['folders']))

    for volume_folder in backup_structure['folders']:
        volume_path = os.path.join(customer_backup_path, volume_folder)

        if not validate_volume_metadata(volume_path, logger):
            logger.error("Backup '{}' could not be validated.".format(customer_backup_path))
            return False
    return True


def is_customer_backup_path_exist(customer_backup_path, logger):
    """
    Validate customer tag path.

    :param customer_backup_path: Path to a customer tag
    :param logger: Logger instance to use for logging.
    :return: True if success; False otherwise.
    """
    if not os.path.exists(customer_backup_path):
        logger.warning("Backup path '{}' does not exist.".format(customer_backup_path))
        return False
    return True


def is_backup_ok_valid(customer_backup_path, backup_structure, logger):
    """
    Validate BACKUP_OK file in the given path.

    :param customer_backup_path: the path to examine BACKUP_OK validity.
    :param backup_structure: A dict contains files and folders list.
    :param logger:
    :return: True if valid otherwise False.
    """
    if SUCCESS_FLAG_FILE not in backup_structure['files']:
        logger.warning("Backup '{}' does not have a success flag.".format(customer_backup_path))
        return False
    return True


def report_unexpected_files_presence(backup_structure, logger):
    """
    Report unexpected files inside customer tag folder.

    :param backup_structure: A dict contains files and folders list.
    :param logger: Logger instance to use for logging.
    """
    unexpected_files = filter(lambda item: item not in (SUCCESS_FLAG_FILE, BACKUP_META_FILE),
                              backup_structure['files'])

    if unexpected_files:
        logger.warning('Unexpected files found: {}'.format(unexpected_files))


def get_volume_metadata_file(volume_path, logger):
    """
    Find metadata file inside a volume.

    :param volume_path: Volume path of a backup folder.
    :param logger: Logger instance to use for logging.
    :return: Metadata file inside a volume directory.
    """
    metadata_file = glob.glob(os.path.join(
        volume_path, str('*' + METADATA_FILE_SUFFIX)))

    if len(metadata_file) == 1:
        metadata_file_name = metadata_file[0]
        return metadata_file_name

    logger.error("Cannot recognize metadata file in volume: '{}'".format(volume_path))
    return None


def get_metadata_file_json(volume_path, logger):
    """
    Read metadata file in json format and return the result.

    :param volume_path: Volume path of a backup folder.
    :param logger: Logger instance to use for logging.
    :return: Metadata file content in json.
    """
    metadata_file_name = get_volume_metadata_file(volume_path, logger)

    if not metadata_file_name:
        return None

    try:
        with open(metadata_file_name) as metadata_file:
            return json.load(metadata_file)

    except (ValueError, TypeError) as json_load_exp:
        logger.error("Metadata error: Could not parse metadata file '{}'. Cause: {}."
                     .format(metadata_file_name, json_load_exp))
        return None


def validate_metadata_content(volume_path, metadata_json, logger):
    """
    Validate metadata content with the physical volume.

    :param metadata_json: Metadata file content in json.
    :param volume_path: Volume path of a backup folder.
    :param logger: Logger instance to use for logging.
    :return: True if valid otherwise False.
    """
    volume_list = os.listdir(volume_path)
    metadata_file_list = metadata_json[META_DATA_KEYS.objects.name]

    for item in metadata_file_list:
        item_key = item.keys()
        if len(item_key) != 1:
            logger.error("Metadata error: File entry is malformed.")
            return False

        vol_file = ''.join(item_key)
        if vol_file not in volume_list:
            logger.error('Metadata item {} not found inside volume {}'
                         .format(item, repr(volume_list)))
            return False

        if META_DATA_KEYS.md5.name not in item[vol_file].keys():
            logger.error("Metadata error: Missing key {} for file {}."
                         .format(META_DATA_KEYS.md5.name, metadata_file_list))
            return False
    return True


def validate_volume_metadata(volume_path, logger):
    """
    Validate the metadata file from a specific volume against the system.

    :param volume_path: Volume path of a backup folder.
    :param logger: Logger object.
    :return: True, if all files in the metadata have the same md5 code; False otherwise.
    """
    logger.info("Validating metadata from volume '{}'.".format(volume_path))

    if not is_dir(volume_path):
        logger.info("Volume path should be a directory: '{}'.".format(volume_path))
        return False

    if not os.listdir(volume_path):
        logger.warning("Volume path '{}' is empty.".format(volume_path))
        return False

    metadata_json = get_metadata_file_json(volume_path, logger)

    if not metadata_json:
        return False

    if not validate_metadata_content(volume_path, metadata_json, logger):
        return False

    logger.info("Successful metadata validation for volume: '{}'.".format(volume_path))
    return True
