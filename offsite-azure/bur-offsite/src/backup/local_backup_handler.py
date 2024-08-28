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

"""Module to manage upload related functions of customer's backups."""

from enum import Enum
import multiprocessing as mp
import os
import time

import dill

from backup.constants import BACKUP_META_FILE, BUR_FILE_LIST_DESCRIPTOR_FILE_NAME, \
    BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME, PROCESSED_VOLUME_ENDS_WITH, SUCCESS_FLAG_FILE, \
    VOLUME_OUTPUT_KEYS
from backup.exceptions import BurException, ExceptionCodes, UploadBackupException, UtilsException, AzCopyException
from backup.logger import CustomLogger
from backup.rsync_manager import RsyncManager
from backup.azcopy_manager import AzCopyManager
from backup.utils.backup_handler import check_local_disk_space_for_upload, \
    validate_backup_per_volume
from backup.utils.compress import compress_file
from backup.utils.decorator import collect_performance_data, timeit, timer_delay
from backup.utils.fsys import create_path, create_pickle_file, get_folder_file_lists_from_dir, \
    get_formatted_size_on_disk, remove_path
from backup.utils.remote import check_remote_path_exists, create_remote_dir, \
    get_remote_folder_content

MIN_BKP_LOCAL = 1

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

VOLUME_CALLBACK_OUTPUT_INDEX = Enum('VOLUME_CALLBACK_OUTPUT_INDEX', 'VOLUME_NAME, VOLUME_OUTPUT, '
                                                                    'REMOTE_BACKUP_PATH, REMOTE_AZ_BACKUP_PATH')


def unwrapper_local_backup_handler_function(backup_handler_obj, function_name, *args):
    """
    Reload a LocalBackupHandler object to use Multiprocessing map function.

    Supported functions: process_volume, transfer_backup_volume_to_offsite.

    :param backup_handler_obj: LocalBackupHandler object.
    :param function_name: name of the function from LocalBackupHandler class to be executed.
    :param args: arguments of the unwrapped function.
    :return: volume_name, volume_output and remote_backup_path; or output of the original function.
    :raise UploadBackupException: if the arguments are not as expected.
    """
    loaded_backup_handler_object = dill.loads(backup_handler_obj)
    if not isinstance(loaded_backup_handler_object, LocalBackupHandler):
        raise UploadBackupException(ExceptionCodes.CannotUnwrapperObject,
                                    loaded_backup_handler_object)

    if function_name not in (LocalBackupHandler.process_volume.__name__,
                             LocalBackupHandler.transfer_backup_volume_to_offsite.__name__):
        raise UploadBackupException(ExceptionCodes.OperationNotSupported, function_name)

    if function_name == LocalBackupHandler.process_volume.__name__:
        volume_path = args[0]
        volume_name = args[1]
        temp_volume_folder_path = args[2]
        remote_backup_path = args[3]
        remote_az_backup_path = args[4]

        volume_output = loaded_backup_handler_object.process_volume(volume_path,
                                                                    temp_volume_folder_path)
        return volume_name, volume_output, remote_backup_path, remote_az_backup_path

    return loaded_backup_handler_object.transfer_backup_volume_to_offsite(*args)


class LocalBackupHandler:
    """
    Class responsible for executing the backup upload feature for a customer.

    It uses multi-processing to handle the volumes in parallel for each backup.
    """

    def __init__(self, offsite_config, onsite_config, customer_conf, gpg_manager, process_pool_size,
                 thread_pool_size, transfer_pool_size, logger, rsync_ssh=True):
        """
        Initialize Local Backup Handler object.

        :param offsite_config: details of the off-site server.
        :param customer_conf: details of the local customer server.
        :param gpg_manager: gpg manager object to handle encryption and decryption.
        :param process_pool_size: maximum number of running process at a time.
        :param thread_pool_size: maximum number of running threads at a time.
        :param transfer_pool_size: number of running rsync processes.
        :param logger: logger object.
        :param rsync_ssh: boolean to determine whether to use rsync over ssh or rsync daemon.
        """
        self.customer_conf = customer_conf
        self.offsite_config = offsite_config
        self.onsite_config = onsite_config

        self.remote_root_path = os.path.join(self.offsite_config.full_path, self.customer_conf.name)
        self.remote_root_container_path = os.path.join(self.offsite_config.full_container_path, self.customer_conf.name)
        self.temp_customer_root_path = os.path.join(self.onsite_config.temp_path,
                                                    self.customer_conf.name)

        logger_script_reference = "{}_{}".format(SCRIPT_FILE, customer_conf.name)
        self.logger = CustomLogger(logger_script_reference, logger.log_root_path,
                                   logger.log_file_name, logger.log_level)

        self.gpg_manager = gpg_manager
        self.process_pool_size = process_pool_size
        self.thread_pool_size = thread_pool_size
        self.transfer_pool_size = transfer_pool_size
        self.rsync_ssh = rsync_ssh
        self.backup_output_dict = None
        self.transfer_pool = None
        self.serialized_object = dill.dumps(self)

    @timer_delay
    @timeit
    def process_backup_list(self, backup_tag=None, **kwargs):
        """
        Process a list of valid backups for the customer or just the one identified by backup_tag.

        Processing includes compression, encryption and uploading tasks.

        :param backup_tag: backup id.
        :param kwargs: for process timing purposes
        :return: list of processed backup(s).
        :raise UploadBackupException: if an error occurs before processing the backups.
        """
        local_backup_list = self.get_and_validate_onsite_backups_list(backup_tag)

        self.validate_create_offsite_onsite_base_paths()

        self.logger.log_info("Doing backup of: {}, directories: {}"
                             .format(self.customer_conf.name, local_backup_list))

        backup_error_list = []
        for current_backup_folder_name in local_backup_list:
            remote_current_backup_path = os.path.join(self.remote_root_path,
                                                      current_backup_folder_name)
            remote_current_backup_az_path = os.path.join(self.remote_root_container_path,
                                                         current_backup_folder_name)

            temp_current_backup_path = os.path.join(self.temp_customer_root_path,
                                                    current_backup_folder_name)

            try:
                if not create_path(temp_current_backup_path):
                    raise UploadBackupException(ExceptionCodes.CannotCreatePath,
                                                temp_current_backup_path)

                if not create_remote_dir(self.offsite_config.host, remote_current_backup_path):
                    raise UploadBackupException(ExceptionCodes.CannotCreatePath,
                                                remote_current_backup_path)

                self.process_backup(current_backup_folder_name, temp_current_backup_path,
                                    remote_current_backup_path, remote_current_backup_az_path)

                if not remove_path(temp_current_backup_path):
                    self.logger.error("Error while removing temporary backup folder '{}'."
                                      .format(temp_current_backup_path))

            except UploadBackupException as backup_exception:
                backup_error_list.append(backup_exception.__str__())

        if backup_error_list:
            raise UploadBackupException(ExceptionCodes.ProcessBackupListErrors,
                                        [backup_error_list, "Backup tag(s): {}".format(
                                            local_backup_list)])

        return local_backup_list

    def get_and_validate_onsite_backups_list(self, backup_tag=None):
        """
        Prepare the list of valid onsite backups to be processed and uploaded to off-site.

        In case of trying to upload a certain backup tag then validate that tag, and treat it as
        a list of one element.

        :param backup_tag: a certain backup tag, to upload a certain backup of the user's choice.
        :return: list of valid onsite backups to be processed and uploaded to off-site.
        :raise UploadBackupException: if there was no backups available onsite.
        """
        valid_onsite_backups_list = self.get_local_backup_list()
        if not valid_onsite_backups_list:
            raise UploadBackupException(ExceptionCodes.NoBackupsToProcess, self.customer_conf.name)

        if backup_tag:
            if backup_tag in valid_onsite_backups_list:
                valid_onsite_backups_list = [backup_tag]
            else:
                raise UploadBackupException(ExceptionCodes.NoSuchBackupTag,
                                            [backup_tag, self.customer_conf.name])

        return valid_onsite_backups_list

    def validate_create_offsite_onsite_base_paths(self):
        """
        Validate if the customer paths exist on off-site and create temporary paths onsite.

        :return: true, if success.
        :raise UploadBackupException: if any path cannot be validated.
        """
        if not create_remote_dir(self.offsite_config.host, self.remote_root_path):
            raise UploadBackupException(ExceptionCodes.CannotCreatePath,
                                        [self.remote_root_path, self.customer_conf.name])

        if not create_path(self.onsite_config.temp_path):
            raise UploadBackupException(ExceptionCodes.CannotCreatePath,
                                        self.onsite_config.temp_path)

        if not create_path(self.temp_customer_root_path):
            raise UploadBackupException(ExceptionCodes.CannotCreatePath,
                                        self.temp_customer_root_path)

        return True

    def get_list_processed_vols_names_offsite(self, remote_backup_path):
        """
        Get the list of processed volumes names for a given backup on off-site.

        :param remote_backup_path: path of the backup on off-site.
        :return: list of processed volume names, if any or empty otherwise.
        :raise UploadBackupException: if there was a problem getting the list of volumes.
        """
        try:
            filtering_criteria = "*{}".format(PROCESSED_VOLUME_ENDS_WITH)

            offsite_volume_list = get_remote_folder_content(self.offsite_config.host,
                                                            remote_backup_path,
                                                            filtering_criteria)

            if offsite_volume_list:
                return [os.path.splitext(volume_path)[0] for volume_path in offsite_volume_list]

            self.logger.warning("Off-site backup {} doesn't have any fully processed volumes."
                                .format(remote_backup_path))

        except UtilsException as exception:
            raise UploadBackupException(ExceptionCodes.FailedToGetProcessedVolsNamesOffsite,
                                        [remote_backup_path, exception])

        return []

    @collect_performance_data
    def process_backup(self, backup_folder_name, temp_backup_path, remote_backup_path, remote_az_backup_path):
        """
        Compress, encrypt and transfer volumes of the current backup to the off-site server.

        :param backup_folder_name: backup directory name.
        :param temp_backup_path: backup temporary directory path.
        :param remote_backup_path: remote backup path.
        :param remote_az_backup_path: Remote Azure storage path for backup.
        :return: tuple with backup id, backup output dictionary and total processing time.
        """
        time_start = time.time()

        local_backup_path = os.path.join(self.customer_conf.backup_path, backup_folder_name)

        check_local_disk_space_for_upload(local_backup_path, temp_backup_path, self.logger)

        self.backup_output_dict = mp.Manager().dict()

        self.transfer_pool = mp.Pool(self.transfer_pool_size)

        file_path_list, volume_path_list, volume_path_to_process_list = \
            self.validate_already_processed_volumes(local_backup_path, temp_backup_path,
                                                    remote_backup_path, remote_az_backup_path)

        if volume_path_to_process_list:
            self.logger.info("Processing list of volumes: {}.".format(volume_path_to_process_list))

        process_pool = mp.Pool(self.process_pool_size)

        for volume_path in volume_path_to_process_list:
            volume_name = os.path.basename(volume_path)

            temp_volume_folder_path = os.path.join(temp_backup_path, volume_name)

            process_pool.apply_async(unwrapper_local_backup_handler_function,
                                     (self.serialized_object,
                                      LocalBackupHandler.process_volume.__name__, volume_path,
                                      volume_name, temp_volume_folder_path, remote_backup_path, remote_az_backup_path),
                                     callback=self.on_volume_ready)
        process_pool.close()
        process_pool.join()

        self.transfer_pool.close()
        self.transfer_pool.join()

        self.check_backup_output_errors()

        file_name_list = self.process_backup_metadata_files(file_path_list, temp_backup_path,
                                                            remote_backup_path, remote_az_backup_path)

        self.process_bur_descriptors(BUR_FILE_LIST_DESCRIPTOR_FILE_NAME, file_name_list,
                                     temp_backup_path, remote_backup_path, remote_az_backup_path)

        volume_name_list = [os.path.basename(file_path) for file_path in volume_path_list]

        self.process_bur_descriptors(BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME, volume_name_list,
                                     temp_backup_path, remote_backup_path, remote_az_backup_path)

        time_end = time.time()

        # it is not possible collect the performance data with timeit in this case.
        total_backup_processing_time = time_end - time_start

        bur_id = "{}_{}".format(self.customer_conf.name, backup_folder_name)

        return bur_id, self.backup_output_dict, total_backup_processing_time

    def validate_already_processed_volumes(self, local_backup_path, temp_backup_path,
                                           remote_backup_path, remote_az_backup_path=None):
        """
        Retrieve the list of files and volumes to be processed still.

        Check the system for already processed volumes for this backup and send them to off-site
        using the transfer pool.

        :param local_backup_path: path of the backup in the system.
        :param temp_backup_path: path of the temporary location of volumes before transferring.
        :param remote_backup_path: backup location on off-site.
        :param remote_az_backup_path: backup folder location in Azure storage
        :return: tuple with list of files, list of all volumes and list of volumes to be processed.
        :raise UploadBackupException: if cannot get volume list or metadata information.
        """
        volume_path_list, file_path_list = get_folder_file_lists_from_dir(local_backup_path)

        if not volume_path_list:
            raise UploadBackupException(ExceptionCodes.NoVolumeListForBackup, local_backup_path)

        if not file_path_list:
            raise UploadBackupException(ExceptionCodes.NoMetadataForBackup, local_backup_path)

        uploaded_volume_name_list = self.get_list_processed_vols_names_offsite(remote_backup_path)

        volume_path_list_to_process = []
        for volume_path in volume_path_list:
            volume_name = os.path.basename(volume_path)

            if volume_name in uploaded_volume_name_list:
                self.logger.info("Found already uploaded volume '{}'. Skipping it.".format(
                    volume_name))
                continue

            tar_volume_name = "{}{}".format(volume_name, PROCESSED_VOLUME_ENDS_WITH)
            proc_tar_volume_path = os.path.join(temp_backup_path, tar_volume_name)

            if os.path.exists(proc_tar_volume_path):
                self.logger.info("Found already processed volume in the system '{}'. "
                                 "Sending it to off-site.".format(proc_tar_volume_path))

                volume_output = LocalBackupHandler.get_empty_volume_output(proc_tar_volume_path,
                                                                           True)

                self.on_volume_ready((volume_name, volume_output, remote_backup_path, remote_az_backup_path))

                continue

            temp_unfinished_volume_path = os.path.join(temp_backup_path, volume_name)

            if os.path.exists(temp_unfinished_volume_path):
                self.logger.info("Cleaning up unfinished volume '{}'.".format(
                    temp_unfinished_volume_path))

                remove_path(temp_unfinished_volume_path)

            volume_path_list_to_process.append(volume_path)

        return file_path_list, volume_path_list, volume_path_list_to_process

    def process_bur_descriptors(self, descriptor_name, content_list, temp_backup_path,
                                remote_backup_path, remote_az_backup_path):
        """
        Create and transfer BUR descriptor files with the list of file and volume names to off-site.

        :param descriptor_name: name of the descriptor to be processed.
        :param content_list: content of the descriptor in list format.
        :param temp_backup_path: temporary backup processing directory.
        :param remote_backup_path: remote backup location.
        :param remote_az_backup_path: remote azure storage location
        :return: true, if success.
        """
        descriptor_path_offsite = os.path.join(remote_backup_path, descriptor_name)

        if not check_remote_path_exists(self.offsite_config.host, descriptor_path_offsite):
            self.logger.info("Creating and sending BUR file descriptor file '{}' to off-site."
                             .format(descriptor_name))

            target_dir = "{}:{}".format(self.offsite_config.host, remote_backup_path)

            LocalBackupHandler.create_transfer_pickle_file(
                os.path.join(temp_backup_path, descriptor_name), content_list, target_dir, remote_az_backup_path,
                self.rsync_ssh)

        self.logger.warning("Backup descriptor {} was already uploaded to off-site.".format(
            descriptor_name))

        return True

    def process_backup_metadata_files(self, file_list, temp_backup_path, remote_backup_path, remote_az_backup_path):
        """
        Process backup metadata files inside backup's folder.

        Metadata files are compressed, encrypted and stored in the temporary folder.

        After processing they are archived and sent to off-site.

        :param file_list: list of file paths inside the backup folder.
        :param temp_backup_path: temporary folder to process the backup.
        :param remote_backup_path: location on the off-site to send the backup.
        :param remote_az_backup_path
        :return: list of processed file names.
        :raise UploadBackupException: if processed file cannot be removed.
        """
        self.logger.info("Processing backup standalone files after volumes.")

        target_dir = "{}:{}".format(self.offsite_config.host, remote_backup_path)

        processed_file_name_list = []

        for file_path in file_list:
            file_name = os.path.basename(file_path)

            file_path_offsite = os.path.join(remote_backup_path, file_name)
            if check_remote_path_exists(self.offsite_config.host, file_path_offsite):
                self.logger.warning("Backup metadata {} was already uploaded to "
                                    "off-site.".format(file_name))
                continue

            if SUCCESS_FLAG_FILE == file_name:
                file_to_transfer = file_path
            elif BACKUP_META_FILE == file_name:
                processed_file_path = self.gpg_manager.compress_encrypt_file(file_path,
                                                                             temp_backup_path)

                self.logger.info("Archiving backup metadata file '{}'.".format(processed_file_path))

                archived_file_path = compress_file(processed_file_path, None, "w")

                if not remove_path(processed_file_path):
                    raise UploadBackupException(ExceptionCodes.CannotRemoveFile,
                                                processed_file_path)

                file_to_transfer = archived_file_path
            else:
                self.logger.warning("Unexpected file '{}' will be ignored.".format(file_path))
                continue

            self.logger.info("Transferring backup metadata file '{}' to '{}'."
                             .format(file_to_transfer, remote_az_backup_path))

            #RsyncManager.transfer_file(file_to_transfer, target_dir, self.rsync_ssh)
            AzCopyManager.transfer_file(file_to_transfer, remote_az_backup_path)

            processed_file_name_list.append(os.path.basename(file_to_transfer))

        return processed_file_name_list

    def on_volume_ready(self, on_volume_ready_tuple):
        """
        Return a callback after a volume is processed.

        If the volume is ready, add a new job to the transfer pool, so that it starts uploading
        the volume to off-site.

        Populate the backup dictionary with details of the volume's processing.

        :param on_volume_ready_tuple: volume_name, volume_output_dictionary, remote_backup_path.
        :return: true, if volume was processed and sent to the transfer pool; false, otherwise.
        """
        volume_name = on_volume_ready_tuple[
            VOLUME_CALLBACK_OUTPUT_INDEX.VOLUME_NAME.value - 1]
        volume_output = on_volume_ready_tuple[
            VOLUME_CALLBACK_OUTPUT_INDEX.VOLUME_OUTPUT.value - 1]
        remote_backup_path = on_volume_ready_tuple[
            VOLUME_CALLBACK_OUTPUT_INDEX.REMOTE_BACKUP_PATH.value - 1]
        remote_az_backup_path = on_volume_ready_tuple[
            VOLUME_CALLBACK_OUTPUT_INDEX.REMOTE_AZ_BACKUP_PATH.value -1]

        if volume_output[VOLUME_OUTPUT_KEYS.status.name]:
            processed_volume_path = volume_output[VOLUME_OUTPUT_KEYS.volume_path.name]

            volume_size_string = get_formatted_size_on_disk(processed_volume_path)

            self.logger.info("Volume '{}' processed successfully. Size: {}. Starting to send it."
                             .format(processed_volume_path, volume_size_string))

            transfer_func_name = LocalBackupHandler.transfer_backup_volume_to_offsite.__name__

            self.transfer_pool.apply_async(unwrapper_local_backup_handler_function,
                                           (self.serialized_object, transfer_func_name,
                                            volume_name, volume_output, processed_volume_path,
                                            remote_backup_path, remote_az_backup_path),
                                           callback=self.on_volume_transferred)
            return True

        self.logger.error("An error happened while processing volume '{}'.".format(volume_name))

        self.backup_output_dict[volume_name] = volume_output

        return False

    def on_volume_transferred(self, on_volume_transferred_tuple):
        """
        Return a callback after a volume is transferred.

        :param on_volume_transferred_tuple: tuple with volume_name and volume_output_dictionary.
        :return: volume output status.
        """
        volume_name = on_volume_transferred_tuple[
            VOLUME_CALLBACK_OUTPUT_INDEX.VOLUME_NAME.value - 1]
        volume_output = on_volume_transferred_tuple[
            VOLUME_CALLBACK_OUTPUT_INDEX.VOLUME_OUTPUT.value - 1]

        self.backup_output_dict[volume_name] = volume_output

        return volume_output[VOLUME_OUTPUT_KEYS.status.name]

    def check_backup_output_errors(self):
        """
        Check the output dictionary of a backup download for errors.

        :return: true, if no error was found.
        :raise UploadBackupException: if errors during the process were detected.
        """
        failed_volume_error_message_list = []

        for key, _ in self.backup_output_dict.items():
            if not self.backup_output_dict[key][VOLUME_OUTPUT_KEYS.status.name]:
                error_message = self.backup_output_dict[key][
                    VOLUME_OUTPUT_KEYS.output.name]
                failed_volume_error_message_list.append(error_message)
                self.logger.error(error_message)

        if failed_volume_error_message_list:
            raise UploadBackupException(parameters=failed_volume_error_message_list)

        return True

    def process_volume(self, volume_path, tmp_volume_path):
        """
        Process a single volume folder by encrypting the files and compressing the folder.

        :param volume_path: path of the volume.
        :param tmp_volume_path: local temporary path to store auxiliary files.
        :return: dictionary with the output of the processed volume.
        :raise UploadBackupException: if an error happens during the process.
        """
        self.logger.log_info("Process_id: {}, processing volume: {}, for: {}"
                             .format(os.getpid(), volume_path, self.customer_conf.name))

        volume_output_dict = LocalBackupHandler.get_empty_volume_output()

        try:
            if not create_path(tmp_volume_path):
                raise UploadBackupException(ExceptionCodes.CannotCreatePath, tmp_volume_path)

            self.logger.info("Compressing and encrypting files from volume '{}'."
                             .format(volume_path))

            total_volume_process_time = []
            self.gpg_manager.compress_encrypt_file_list(volume_path, tmp_volume_path,
                                                        self.thread_pool_size,
                                                        get_elapsed_time=total_volume_process_time)

            if total_volume_process_time:
                self.logger.log_time("Elapsed time to process the volume '{}'"
                                     .format(volume_path), total_volume_process_time[0])
                volume_output_dict[VOLUME_OUTPUT_KEYS.processing_time.name] = \
                    total_volume_process_time[0]

            self.logger.info("Archiving volume directory '{}' for customer {}."
                             .format(tmp_volume_path, self.customer_conf.name))

            volume_tar_time = []
            compressed_volume_path = compress_file(tmp_volume_path, None, "w",
                                                   get_elapsed_time=volume_tar_time)

            if volume_tar_time:
                self.logger.log_time("Elapsed time to archive the volume '{}'"
                                     .format(tmp_volume_path), volume_tar_time[0])
                volume_output_dict[VOLUME_OUTPUT_KEYS.tar_time.name] = volume_tar_time[0]

            if not remove_path(tmp_volume_path):
                raise UploadBackupException(ExceptionCodes.CannotRemovePath, tmp_volume_path)

            volume_output_dict[VOLUME_OUTPUT_KEYS.volume_path.name] = \
                compressed_volume_path
            volume_output_dict[VOLUME_OUTPUT_KEYS.status.name] = True

        except BurException as processing_exception:
            volume_output_dict[VOLUME_OUTPUT_KEYS.output.name] = \
                "Error while processing volume. {}".format(processing_exception.__str__())

        return volume_output_dict

    def transfer_backup_volume_to_offsite(self, volume_name, volume_output,
                                          tmp_customer_volume_path, remote_dir, remote_az_dir):
        """
        Transfer a backup already compressed and encrypted to the off-site.

        Results from the processing are stored in the output dictionary.

        :param volume_name: name of the volume to be transferred.
        :param volume_output: output dictionary with results after processing the volume.
        :param tmp_customer_volume_path: temporary folder where the backup volumes are stored.
        :param remote_dir: remote location to send the backup.
        :return: volume name and volume_output with updated data about the transferring process.
        """
        volume_output[VOLUME_OUTPUT_KEYS.rsync_output.name] = None
        volume_output[VOLUME_OUTPUT_KEYS.transfer_time.name] = 0.0

        try:
            target_dir = "{}:{}".format(self.offsite_config.host, remote_dir)

            self.logger.log_info("Process_id: {}, transferring volume '{}' to '{}'".format(
                os.getpid(), tmp_customer_volume_path, remote_az_dir))

            transfer_time = []
            # rsync_output = RsyncManager.transfer_file(tmp_customer_volume_path, target_dir,
            #                                           self.rsync_ssh,
            #                                           get_elapsed_time=transfer_time)

            azcopy_output = AzCopyManager.transfer_file(tmp_customer_volume_path, remote_az_dir)

            if transfer_time:
                self.logger.log_time("Elapsed time to transfer volume '{}'"
                                     .format(tmp_customer_volume_path), transfer_time[0])
                volume_output[VOLUME_OUTPUT_KEYS.transfer_time.name] = transfer_time[0]

            volume_output[VOLUME_OUTPUT_KEYS.rsync_output.name] = azcopy_output

            self.logger.info("Volume '{}' was successfully transferred to off-site for customer {}."
                             .format(tmp_customer_volume_path, self.customer_conf.name))

            if not remove_path(tmp_customer_volume_path):
                self.logger.error("Error to delete temporary path '{}' from customer {}.".format(
                    tmp_customer_volume_path, self.customer_conf.name))
                raise UploadBackupException(ExceptionCodes.CannotRemovePath,
                                            tmp_customer_volume_path)

            volume_output[VOLUME_OUTPUT_KEYS.status.name] = True
            volume_output[VOLUME_OUTPUT_KEYS.output.name] = ""

        except BurException as transfer_exception:
            error_message = "Error while transferring volume. {}" \
                .format(transfer_exception.__str__())

            volume_output[VOLUME_OUTPUT_KEYS.status.name] = False
            volume_output[VOLUME_OUTPUT_KEYS.output.name] = error_message

        except AzCopyException as transfer_exception:
            error_message = "Error while transferring volume. {}" \
                .format(transfer_exception.__str__())

            volume_output[VOLUME_OUTPUT_KEYS.status.name] = False
            volume_output[VOLUME_OUTPUT_KEYS.output.name] = error_message

        return volume_name, volume_output

    def clean_local_backup(self, customer_backup_path):
        """
        Clean the local customer's folder, keeping at least MAX_BKP_NFS stored.

        :param customer_backup_path: path to the customer's backup folder in NFS.
        :return: tuple with true or false and output message.
        """
        self.logger.log_info("Performing the clean up on NFS path '{}'."
                             .format(self.customer_conf.backup_path))

        number_backup_dir = 0
        for backup_dir in os.listdir(self.customer_conf.backup_path):
            if os.path.isfile(os.path.join(self.customer_conf.backup_path, backup_dir)):
                continue

            number_backup_dir += 1

        self.logger.info("There are currently {} backup(s) in the folder '{}'."
                         .format(number_backup_dir, self.customer_conf.backup_path))

        if number_backup_dir > MIN_BKP_LOCAL:
            self.logger.info("Removing backup '{}' from NFS server.".format(customer_backup_path))

            if not remove_path(customer_backup_path):
                return False, "Error while deleting folder '{}' from NFS server." \
                    .format(customer_backup_path)
        else:
            return False, "Backup '{}' NOT removed. Just {} backup found." \
                .format(customer_backup_path, MIN_BKP_LOCAL)

        return True, "Backup '{}' removed successfully.".format(customer_backup_path)

    def get_local_backup_list(self):
        """
        Get list of valid backups for the current customer sorted by date (from oldest to newest).

        :return: list of valid backup folders or None when an error happens.
        """
        source_dir = self.customer_conf.backup_path

        if not os.path.exists(source_dir):
            self.logger.error("Invalid backup source path '{}'.".format(source_dir))
            return None

        self.logger.info("Getting the list of valid backups from '{}'.".format(source_dir))

        valid_dir_list = []
        customer_tags = os.listdir(source_dir)

        self.logger.info('Available backups for customer {} are: [ {} ]'
                         .format(os.path.basename(source_dir), customer_tags))

        for backup_folder in customer_tags:
            backup_path = os.path.join(source_dir, backup_folder)

            if os.path.isfile(backup_path):
                self.logger.warning("Found a file '{}' inside backup folder.".format(backup_path))
                continue

            if not validate_backup_per_volume(self.customer_conf.name, backup_path, self.logger):
                self.logger.warning("Backup '{}' is not valid.".format(backup_path))
                continue

            self.logger.info("Backup '{}' successfully validated.".format(backup_path))

            valid_dir_list.append(backup_folder)

        valid_dir_list.sort(key=lambda s: os.path.getmtime(os.path.join(source_dir, s)))

        return valid_dir_list

    @staticmethod
    def create_transfer_pickle_file(file_path, pickle_content, target_dir, remote_az_backup_path, rsync_ssh=True):
        """
        Create and transfer a pickle file to the informed target.

        If an error occurs, an Exception is raised with the details of the problem.

        :param file_path: pickle file path to be created.
        :param pickle_content: content to be stored in the pickle file.
        :param target_dir: remote location to send the pickle file.
        :param remote_az_backup_path: remote az storage location
        :param rsync_ssh: boolean to determine whether to use rsync over ssh or rsync daemon.
        :return: true if success.
        :raise UploadBackupException: if an error happened to remove the pickle file.
        """
        create_pickle_file(pickle_content, file_path)

        #RsyncManager.transfer_file(file_path, target_dir, rsync_ssh)
        AzCopyManager.transfer_file(file_path, remote_az_backup_path)

        if not remove_path(file_path):
            raise UploadBackupException(ExceptionCodes.CannotRemoveFile, file_path)

        return True

    @staticmethod
    def get_empty_volume_output(volume_path="", status=False):
        """
        Get a volume output dictionary with initialized data.

        :param volume_path: volume path if it already exists.
        :param status: processing status.
        :return: volume output dictionary with the informed settings.
        """
        volume_output_dict = dict()

        volume_output_dict[VOLUME_OUTPUT_KEYS.volume_path.name] = volume_path
        volume_output_dict[VOLUME_OUTPUT_KEYS.processing_time.name] = 0.0
        volume_output_dict[VOLUME_OUTPUT_KEYS.tar_time.name] = 0.0
        volume_output_dict[VOLUME_OUTPUT_KEYS.output.name] = ""
        volume_output_dict[VOLUME_OUTPUT_KEYS.status.name] = status

        return volume_output_dict
