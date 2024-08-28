##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=too-many-instance-attributes,too-many-arguments,unused-argument,too-many-locals

"""Module to manage download related functions of customer's backups."""

import multiprocessing as mp
import os
import time

import dill

from backup.constants import BUR_FILE_LIST_DESCRIPTOR_FILE_NAME, \
    BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME, SUCCESS_FLAG_FILE, TAR_SUFFIX, TIMEOUT, VOLUME_OUTPUT_KEYS
from backup.exceptions import BurException, DownloadBackupException, ExceptionCodes, AzCopyException
from backup.logger import CustomLogger
from backup.rsync_manager import RsyncManager
from backup.azcopy_manager import AzCopyManager
from backup.utils.backup_handler import check_is_processed_volume, \
    check_local_disk_space_for_download, validate_backup_per_volume
from backup.utils.compress import decompress_file, is_tar_file
from backup.utils.datatypes import find_elem_dict, get_values_from_dict
from backup.utils.decorator import collect_performance_data, timeit
from backup.utils.fsys import create_path, is_valid_path, load_pickle_file, remove_path, \
    split_folder_list
from backup.utils.remote import check_remote_path_exists, is_remote_folder_empty, \
    remove_remote_dir, run_ssh_command, sort_remote_folders_by_content
from backup.utils.validator import check_not_empty

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]


def download_volume_from_offsite(volume_name, archived_volume_name, remote_volume_path,
                                 backup_destination_path, remote_az_volume_path, rsync_ssh=True):
    """
    Call the transfer function to download volumes from the off-site.

    This function is used by the multiprocessing pool, so that the volumes are downloaded in
    parallel.

    :param volume_name: name of the volume to be downloaded.
    :param archived_volume_name: name of the archived volume file on off-site to be downloaded.
    :param remote_volume_path: remote location of the volume on off-site.
    :param backup_destination_path: local destination to store the volume data.
    :param rsync_ssh: rsync mode used (true for ssh/false for daemon).
    :param remote_az_volume_path
    :return: tuple (volume name, archived volume name, output dictionary, destination path).
    """
    volume_output = dict()
    volume_output[VOLUME_OUTPUT_KEYS.status.name] = False
    volume_output[VOLUME_OUTPUT_KEYS.rsync_output.name] = None
    volume_output[VOLUME_OUTPUT_KEYS.transfer_time.name] = 0.0

    try:
        transfer_time = []
        #rsync_output = RsyncManager.transfer_file(remote_volume_path, backup_destination_path,
        #                                          rsync_ssh, get_elapsed_time=transfer_time)

        azcopy_output = AzCopyManager.transfer_file(remote_az_volume_path, backup_destination_path)

        volume_output[VOLUME_OUTPUT_KEYS.rsync_output.name] = azcopy_output

        if transfer_time:
            volume_output[VOLUME_OUTPUT_KEYS.transfer_time.name] = transfer_time[0]

        volume_output[VOLUME_OUTPUT_KEYS.status.name] = True

    except BurException as transfer_exp:
        error_message = "Error while downloading volume. {}".format(transfer_exp.__str__())
        volume_output[VOLUME_OUTPUT_KEYS.output.name] = error_message

    return volume_name, archived_volume_name, volume_output, backup_destination_path


def unwrapper_process_volume_function(backup_handler_obj, *args):
    """
    Process_volume method to use Multiprocessing map to run class methods in a different process.

    Un-wrapper function for OffsiteBackupHandler.

    :param backup_handler_obj: OffsiteBackupHandler object.
    :param args: arguments of the unwrapped function.
    :return: same output as OffsiteBackupHandler.process_volume method.
    :raise DownloadBackupException: if the arguments are not as expected.
    """
    loaded_backup_handler_object = dill.loads(backup_handler_obj)
    if not isinstance(loaded_backup_handler_object, OffsiteBackupHandler):
        raise DownloadBackupException(ExceptionCodes.CannotUnwrapperObject, backup_handler_obj)

    return loaded_backup_handler_object.process_volume(*args)


class OffsiteBackupHandler:
    """
    Class responsible for executing the backup download and off-site cleanup features.

    It uses multi-processing to handle each volume in parallel for each backup.
    """

    def __init__(self, gpg_manager, offsite_config, customer_config_dict, thread_pool_size,
                 process_pool_size, transfer_pool_size, logger, rsync_ssh=True):
        """
        Initialize Offsite Backup Handler object.

        :param gpg_manager: gpg manager object to handle decrypt/encrypt tasks.
        :param offsite_config: information about the remote server.
        :param customer_config_dict: information list about customers.
        :param thread_pool_size: number of allowed running threads at a time.
        :param process_pool_size: number of allowed running processes at a time.
        :param transfer_pool_size: number of allowed running rsync processes at a time.
        :param logger: logger object.
        :param rsync_ssh: boolean to determine whether to use rsync over ssh or rsync daemon.
        """
        self.gpg_manager = gpg_manager
        self.offsite_config = offsite_config
        self.customer_config_dict = customer_config_dict

        self.thread_pool_size = thread_pool_size
        self.process_pool_size = process_pool_size
        self.transfer_pool_size = transfer_pool_size

        self.rsync_ssh = rsync_ssh
        self.logger = CustomLogger(SCRIPT_FILE, logger.log_root_path, logger.log_file_name,
                                   logger.log_level)

        self.remote_root_backup_path = os.path.join(self.offsite_config.path,
                                                    self.offsite_config.folder)
        self.remote_container_path = os.path.join(self.offsite_config.full_container_path)
        self.backup_output_dict = {}

        self.process_pool = None

        self.serialized_object = dill.dumps(self)

    @timeit
    def execute_download_backup_from_offsite(self, customer_name, backup_tag, backup_destination,
                                             **kwargs):
        """
        Execute the download of the backup based on the input parameters.

        Check if the desired customer exists before calling the download function.

        :param customer_name: customer name to retrieve the backup.
        :param backup_tag: backup tag to be retrieved from the off-site location.
        :param backup_destination: path where the backup will be downloaded.
        :return: true if success.
        :raise DownloadBackupException: if backup tag cannot be found.
        """
        check_not_empty(backup_tag)

        customer_config = get_values_from_dict(self.customer_config_dict, customer_name)

        customer_backup_dict = self.get_offsite_backup_dict(customer_config)

        customer_name, backup_path_to_be_retrieved = find_elem_dict(customer_backup_dict,
                                                                    backup_tag)

        if not backup_path_to_be_retrieved.strip():
            raise DownloadBackupException(ExceptionCodes.NoSuchBackupTag, backup_tag)

        az_backup_path_to_be_retrieved = os.path.join(self.remote_container_path, customer_name, os.path.basename(backup_path_to_be_retrieved))
        self.logger.info("Azure storage backup path to retrieve backup : {}".format(az_backup_path_to_be_retrieved))

        backup_destination = self.validate_backup_destination(customer_name, backup_destination)

        self.download_process_backup(customer_name, backup_tag, backup_path_to_be_retrieved,
                                     backup_destination, az_backup_path_to_be_retrieved)

        return True

    def validate_backup_destination(self, customer_name, backup_destination=""):
        """
        Validate the informed backup destination and try to create it if it does not exists.

        :param customer_name: customer name to retrieve the backup.
        :param backup_destination: backup destination folder to do the download from off-site.
        :return: validated backup destination or default value.
        :raise DownloadBackupException: if cannot create backup_destination path.
        """
        if not backup_destination.strip():
            backup_destination = self.customer_config_dict[customer_name].backup_path
            self.logger.warning("Backup destination not informed. Default location '{}' "
                                "used".format(backup_destination))
        else:
            backup_destination = os.path.join(backup_destination, customer_name)

        if not create_path(backup_destination):
            raise DownloadBackupException(ExceptionCodes.CannotCreatePath, backup_destination)

        return backup_destination

    def get_offsite_backup_dict(self, customer_query=None, timeout=TIMEOUT):
        """
        Query the off-site server looking for the list of available backups.

        If the customer_name is empty, retrieves the available backup from all customers, otherwise
        it gets just the ones from a particular customer.

        :param customer_query: specific customer object to process or None.
        :param timeout: time to wait for the process to finish.
        :return: map containing the list of available backups in the off-site by customer name.
        """
        if customer_query is None:
            customer_config_list = self.customer_config_dict.values()
        else:
            if not isinstance(customer_query, list):
                customer_config_list = [customer_query]
            else:
                customer_config_list = customer_query

        list.sort(customer_config_list)

        self.logger.info("Looking for available backups for customers: {}."
                         .format(customer_config_list))

        backup_list_by_customer_dict = dict()

        ssh_get_sorted_dir_list = ""
        for customer_config in customer_config_list:
            ssh_get_sorted_dir_list += "ls -dt {}/*/\necho END-OF-COMMAND\n" \
                .format(os.path.join(self.remote_root_backup_path, customer_config.name))
            backup_list_by_customer_dict[customer_config.name] = []

        stdout, _ = run_ssh_command(self.offsite_config.host, ssh_get_sorted_dir_list, timeout)

        folder_by_customer = stdout.split('END-OF-COMMAND')

        customer_idx = 0
        for key, _ in sorted(backup_list_by_customer_dict.items()):
            if customer_idx > len(folder_by_customer):
                break

            backup_list_by_customer_dict[key] = split_folder_list(folder_by_customer[customer_idx])
            customer_idx += 1

        return backup_list_by_customer_dict

    @collect_performance_data
    def download_process_backup(self, customer_name, backup_tag, backup_path_to_retrieve,
                                backup_destination_path, backup_az_path_to_retrieve):
        """
        Download and process the backup to the destination directory.

        Download the informed backup given by download_backup_path to the destination.

        Decompress all volumes and delete the compressed files.

        Decrypt all files inside the volumes and delete the decrypted files.

        :param customer_name: name or deployment label.
        :param backup_tag: backup tag to be retrieved.
        :param backup_path_to_retrieve: backup path on remote location to be downloaded.
        :param backup_destination_path: folder to store the downloaded backup.
        :param backup_az_path_to_retrieve
        :return: tuple with backup tag, backup output and total time.
        :raise Exception: if backup path cannot be created.
        """
        time_start = time.time()

        check_local_disk_space_for_download(backup_path_to_retrieve, self.offsite_config.host,
                                            backup_destination_path, self.logger)

        download_backup_path = os.path.join(backup_destination_path, backup_tag)

        if not create_path(download_backup_path):
            raise DownloadBackupException(ExceptionCodes.CannotCreatePath, download_backup_path)

        self.logger.info("Downloading backup {} to '{}'.".format(backup_tag, download_backup_path))

        self.check_offsite_backup_success_flag(backup_path_to_retrieve)

        source_remote_dir = "{}:{}".format(self.offsite_config.host, backup_path_to_retrieve)

        self.backup_output_dict = mp.Manager().dict()

        self.process_pool = mp.Pool(self.process_pool_size)

        volume_name_list, volume_name_to_download_list = \
            self.check_volumes_for_download(source_remote_dir, backup_az_path_to_retrieve, download_backup_path)

        if volume_name_to_download_list:
            self.logger.info("Downloading list of volumes: {}."
                             .format(volume_name_to_download_list))

            transfer_pool = mp.Pool(self.transfer_pool_size)

            for archived_volume_name in volume_name_to_download_list:
                remote_volume_path = os.path.join(source_remote_dir, archived_volume_name)
                remote_az_volume_path = os.path.join(backup_az_path_to_retrieve, archived_volume_name)

                self.logger.info("Downloading volume '{}' to '{}'.".format(remote_az_volume_path,
                                                                           download_backup_path))

                volume_name = archived_volume_name.split('.')[0]

                transfer_pool.apply_async(download_volume_from_offsite,
                                          (volume_name, archived_volume_name, remote_volume_path,
                                           download_backup_path, remote_az_volume_path, self.rsync_ssh),
                                          callback=self.on_volume_downloaded)
            transfer_pool.close()
            transfer_pool.join()

        self.process_pool.close()
        self.process_pool.join()

        self.process_backup_metadata_files(source_remote_dir, backup_az_path_to_retrieve, download_backup_path)

        time_end = time.time()

        # it is not possible collect the performance data with timeit in this case.
        total_backup_download_time = time_end - time_start

        self.check_backup_download_errors(customer_name, download_backup_path, volume_name_list)

        bur_id = "download_{}".format(backup_tag)

        return bur_id, self.backup_output_dict, total_backup_download_time

    def check_offsite_backup_success_flag(self, offsite_backup_path):
        """
        Check the off-site for the backup success flag.

        :param offsite_backup_path: backup path on off-site.
        :return: true, if the flag exists.
        :raise Exception: if backup flag could not be found.
        """
        if not check_remote_path_exists(self.offsite_config.host, os.path.join(
                offsite_backup_path, SUCCESS_FLAG_FILE)):
            raise DownloadBackupException(ExceptionCodes.MissingBackupOKFlag, offsite_backup_path)

        return True

    def check_volumes_for_download(self, source_remote_dir, az_remote_dir, download_backup_path):
        """
        Check the status of volumes of given backup.

        Get the list of volumes from descriptor file and verify if each volume is downloaded and
        processed, downloaded but pending processing or needs to be downloaded.

        :param source_remote_dir: remote directory where the backup is stored.
        :param download_backup_path: local directory where the recovered backup is stored.
        :return: tuple (list of all volumes, list of still missing volumes).
        :raise DownloadBackupException: if an empty volume list is detected in the descriptor file.
        """
        bur_volume_list_desc_file_path = os.path.join(source_remote_dir,
                                                      BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME)
        bur_volume_list_az_file_path = os.path.join(az_remote_dir, BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME)

        volume_name_list = OffsiteBackupHandler.retrieve_remote_pickle_file_content(
            bur_volume_list_desc_file_path, download_backup_path, self.rsync_ssh, bur_volume_list_az_file_path)

        if not volume_name_list:
            raise DownloadBackupException(ExceptionCodes.NoVolumeListForBackup,
                                          bur_volume_list_desc_file_path)

        self.logger.info('Volumes found on offsite : {}'.format(volume_name_list))

        missing_volume_list = []

        for volume_name in volume_name_list:
            volume_path = os.path.join(download_backup_path, volume_name)
            if check_is_processed_volume(volume_path, self.logger):
                continue

            archived_volume_name = "{}.{}".format(volume_name, TAR_SUFFIX)
            full_archived_volume_path = os.path.join(download_backup_path, archived_volume_name)

            if os.path.exists(full_archived_volume_path):
                self.logger.info("'{}' already downloaded in the system. "
                                 "Starting to process it.".format(full_archived_volume_path))

                volume_output = dict()
                volume_output[VOLUME_OUTPUT_KEYS.status.name] = True
                volume_output[VOLUME_OUTPUT_KEYS.rsync_output.name] = None
                volume_output[VOLUME_OUTPUT_KEYS.transfer_time.name] = 0.0

                self.on_volume_downloaded((volume_name, archived_volume_name, volume_output,
                                           download_backup_path))
            else:
                missing_volume_list.append(archived_volume_name)

        return volume_name_list, missing_volume_list

    def on_volume_downloaded(self, callback_tuple):
        """
        Start the processing of the downloaded volume if no error happened.

        :param callback_tuple: output of the download_volume_from_offsite function.
        :return: true, if volume was downloaded and sent to the process pool; false, otherwise.
        """
        volume_name = callback_tuple[0]
        archived_volume_name = callback_tuple[1]
        volume_output = callback_tuple[2]
        backup_destination_path = callback_tuple[3]

        if volume_output[VOLUME_OUTPUT_KEYS.status.name]:
            self.logger.info("Starting to recover volume {}.".format(volume_name))

            self.process_pool.apply_async(unwrapper_process_volume_function,
                                          (self.serialized_object, archived_volume_name,
                                           backup_destination_path, volume_output),
                                          callback=self.on_volume_processed)
            return True

        self.logger.error("An error happened while downloading volume '{}'.".format(volume_name))

        if volume_output[VOLUME_OUTPUT_KEYS.rsync_output.name]:
            self.logger.error(volume_output[VOLUME_OUTPUT_KEYS.rsync_output.name])

        self.backup_output_dict[volume_name] = volume_output

        return False

    def on_volume_processed(self, callback_tuple):
        """
        Return callback after a volume is downloaded from off-site.

        :param callback_tuple: expected tuple (volume_name, volume_output_dictionary).
        :return: volume output status.
        """
        volume_name = callback_tuple[0]
        volume_output = callback_tuple[1]

        self.backup_output_dict[volume_name] = volume_output

        return volume_output[VOLUME_OUTPUT_KEYS.status.name]

    def process_backup_metadata_files(self, source_remote_dir, az_remote_dir, backup_destination_path):
        """
        Retrieve and process backup metadata files inside backup's folder.

        :param source_remote_dir: backup remote location.
        :param backup_destination_path: actual downloaded backup folder.
        :param az_remote_dir
        :return: True if success.
        """
        self.logger.info("Processing backup metadata files.")

        file_list_metadata_path = os.path.join(source_remote_dir,
                                               BUR_FILE_LIST_DESCRIPTOR_FILE_NAME)
        file_list_metadata_az_path = os.path.join(az_remote_dir, BUR_FILE_LIST_DESCRIPTOR_FILE_NAME)

        file_name_list = OffsiteBackupHandler.retrieve_remote_pickle_file_content(
            file_list_metadata_path, backup_destination_path, self.rsync_ssh, file_list_metadata_az_path)

        self.logger.info('Available metadata files: {}'.format(file_name_list))

        for file_name in file_name_list:
            file_path = os.path.join(backup_destination_path, file_name)

            if os.path.exists(file_path):
                self.logger.info("Backup metadata file {} already downloaded.".format(file_name))
                continue

            remote_file_path = os.path.join(source_remote_dir, file_name)
            az_remote_file_path = os.path.join(az_remote_dir, file_name)

            #RsyncManager.transfer_file(remote_file_path, backup_destination_path, self.rsync_ssh)
            AzCopyManager.transfer_file(az_remote_file_path, backup_destination_path)

            if is_tar_file(file_path):
                self.logger.info("Extracting backup metadata file '{}'.".format(file_path))

                decompressed_file_path = decompress_file(file_path, backup_destination_path, True)
                self.gpg_manager.decrypt_decompress_file(decompressed_file_path)

        self.check_onsite_backup_success_flag(backup_destination_path)

        return True

    def check_onsite_backup_success_flag(self, backup_destination_path):
        """
        Check on-site, after processing metadata files, if BACKUP_OK flag was downloaded.

        :param backup_destination_path: backup download destination path on-site.
        :return: True if flag was found.
        :raise DownloadBackupException: if flag is missing.
        """
        backup_flag_path = os.path.join(backup_destination_path, SUCCESS_FLAG_FILE)

        if not os.path.exists(backup_flag_path):
            raise DownloadBackupException(ExceptionCodes.MissingBackupOKFlag)

        self.logger.info("Backup OK file recognized: '{}'.".format(backup_flag_path))

        return True

    def check_backup_download_errors(self, customer_name, backup_download_destination_path,
                                     volume_name_list):
        """
        Confirm all volumes were downloaded without errors and validate them against metadata.

        :param customer_name: customer name or deployment label.
        :param backup_download_destination_path: path where the backup was downloaded.
        :param volume_name_list: list of all volumes that should have been downloaded.
        :return: true, if no error was found.
        :raise DownloadBackupException: if a problem happens during the process.
        """
        self.logger.info("Validating all volumes were downloaded and processed successfully.")

        # Check for errors during the process
        failed_volume_error_message_list = []
        for key, _ in self.backup_output_dict.items():
            if not self.backup_output_dict[key][VOLUME_OUTPUT_KEYS.status.name]:
                error_message = \
                    self.backup_output_dict[key][VOLUME_OUTPUT_KEYS.output.name]
                failed_volume_error_message_list.append(error_message)
                self.logger.error(error_message)

        if failed_volume_error_message_list:
            raise DownloadBackupException(ExceptionCodes.DownloadProcessFailed,
                                          failed_volume_error_message_list)

        # Check the volumes exist in the system
        for volume_name in volume_name_list:
            full_local_volume_path = os.path.join(backup_download_destination_path, volume_name)

            if not os.path.exists(full_local_volume_path):
                raise DownloadBackupException(ExceptionCodes.MissingVolume,
                                              [volume_name, full_local_volume_path])

        # Check against metadata
        if not validate_backup_per_volume(customer_name, backup_download_destination_path,
                                          self.logger):
            raise DownloadBackupException(ExceptionCodes.MetadataValidationFailed,
                                          backup_download_destination_path)
        self.logger.info("Backup '{}' successfully validated."
                         .format(backup_download_destination_path))

        return True

    def process_volume(self, volume_name, volume_root_path, volume_output):
        """
        Process a volume downloaded from off-site to its original state.

        The results are stored in an output dictionary.

        :param volume_name: volume name.
        :param volume_root_path: volume root path.
        :param volume_output: output dictionary with results after processing the volume.
        :return: tuple with volume name and volume output dictionary.
        """
        volume_output[VOLUME_OUTPUT_KEYS.processing_time.name] = 0.0
        volume_output[VOLUME_OUTPUT_KEYS.tar_time.name] = 0.0
        volume_output[VOLUME_OUTPUT_KEYS.output.name] = ""
        volume_output[VOLUME_OUTPUT_KEYS.status.name] = False

        volume_full_path = os.path.join(volume_root_path, volume_name)

        try:
            self.logger.log_info("Process_id: {}, processing volume {}.".format(os.getpid(),
                                                                                volume_name))

            is_valid_path(volume_full_path)

            self.logger.info("Extracting volume {}.".format(volume_full_path))

            volume_extraction_time = []
            decompress_file(volume_full_path, volume_root_path, True,
                            get_elapsed_time=volume_extraction_time)

            if volume_extraction_time:
                self.logger.log_time("Elapsed time to extract volume '{}'".format(volume_full_path),
                                     volume_extraction_time[0])
                volume_output[VOLUME_OUTPUT_KEYS.tar_time.name] = volume_extraction_time[0]

            decompressed_volume_dir = os.path.join(volume_root_path, volume_name.split('.')[0])

            self.logger.info("Decrypting and decompressing files from volume '{}'.".format(
                decompressed_volume_dir))

            tot_volume_process_time = []
            self.gpg_manager.decrypt_decompress_file_list(decompressed_volume_dir,
                                                          self.thread_pool_size,
                                                          get_elapsed_time=tot_volume_process_time)

            if tot_volume_process_time:
                self.logger.log_time("Elapsed time to process the volume '{}'".format(
                    decompressed_volume_dir), tot_volume_process_time[0])
                volume_output[VOLUME_OUTPUT_KEYS.processing_time.name] = \
                    tot_volume_process_time[0]

            volume_output[VOLUME_OUTPUT_KEYS.status.name] = True

        except BurException as exception:
            volume_output[VOLUME_OUTPUT_KEYS.output.name] = \
                "Error while processing volume. {}.".format(exception.__str__())
        return volume_name, volume_output

    def get_backup_dir_list_to_cleanup(self, offsite_retention):
        """
        Get the list of the oldest directories to be removed for each customer from the off-site.

        Note that empty backups are not considered in the process.

        :param offsite_retention: how many backups should be kept on offside.
        :return: list with the directories to be removed or empty.
        """
        customer_config_list = get_values_from_dict(self.customer_config_dict)

        dir_list_by_customer_dict = self.get_offsite_backup_dict(customer_config_list)

        dir_to_be_removed_list = []

        for customer_key, _ in dir_list_by_customer_dict.items():

            not_empty_bkp_path_list = filter(lambda offsite_bkp_path: not is_remote_folder_empty(
                self.offsite_config.host, offsite_bkp_path), dir_list_by_customer_dict[
                    customer_key])

            offsite_backup_list_size = len(not_empty_bkp_path_list)

            log_message = "Customer {} has {} backup(s). Retention is {}." \
                .format(customer_key, offsite_backup_list_size, offsite_retention)

            if offsite_backup_list_size > offsite_retention:
                sorted_backup_list = sort_remote_folders_by_content(self.offsite_config.host,
                                                                    not_empty_bkp_path_list)

                dir_to_be_removed_list.extend(sorted_backup_list[offsite_retention:])

                self.logger.info("{} {} backups should be removed."
                                 .format(log_message, offsite_backup_list_size - offsite_retention))
                continue

            self.logger.warning("{} Nothing to do.".format(log_message))

        return dir_to_be_removed_list

    def clean_offsite_backup(self, number_retention):
        """
        Connect to the off-site server and cleans old backups for each customer.

        Keep the MAX_BKP_OFFSITE most recent backups.

        :return tuple with true, success message and list of removed directories, if no problem
        happened or tuple with false, error message, list of removed directories, otherwise.
        """
        self.logger.log_info("Performing the clean up on off-site server.")

        remove_dir_list = self.get_backup_dir_list_to_cleanup(number_retention)

        if not remove_dir_list:
            return True, "Off-site clean up finished successfully with no backup removed.", []

        try:
            not_removed_list, validated_removed_list = remove_remote_dir(self.offsite_config.host,
                                                                         remove_dir_list)
        except BurException as cleanup_exp:
            return False, cleanup_exp.__str__(), []

        if not_removed_list:
            log_message = "Following backups were not removed: {}".format(not_removed_list)
            return False, log_message, validated_removed_list

        return True, "Off-site clean up finished successfully.", validated_removed_list

    @staticmethod
    def retrieve_remote_pickle_file_content(remote_file_path, local_destination_path,
                                            rsync_ssh=True, remote_az_file_path=None):
        """
        Retrieve and load the content of a pickle file stored remotely.

        The downloaded file is removed after its content is loaded.

        :param remote_file_path: full path of the file remotely.
        :param local_destination_path: local destination path to download the file.
        :param rsync_ssh: boolean to determine whether to use rsync over ssh or rsync daemon.
        :param remote_az_file_path
        :return: true if success.
        :raise DownloadBackupException: if cannot read pickle file content or remove it after
        reading.
        """
        #RsyncManager.transfer_file(remote_file_path, local_destination_path, rsync_ssh)
        AzCopyManager.transfer_file(remote_az_file_path, local_destination_path)

        local_file_path = os.path.join(local_destination_path, os.path.basename(remote_file_path))

        list_content = load_pickle_file(local_file_path)

        if not isinstance(list_content, list):
            raise DownloadBackupException(ExceptionCodes.WrongTypeError,
                                          ["Pickle file content was supposed to be a list.",
                                           list_content])

        if not remove_path(local_file_path):
            raise DownloadBackupException(ExceptionCodes.CannotRemoveFile, local_file_path)

        return list_content
