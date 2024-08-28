##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""This script holds required constants necessary to be used across the project."""

from enum import Enum
from sys import platform

LOG_SUFFIX = "log"
TAR_SUFFIX = "tar"
GZ_SUFFIX = "gz"
GPG_SUFFIX = "gpg"
DESCRIPTOR_SUFFIX = "dat"
METADATA_FILE_SUFFIX = "_metadata"
PROCESSED_VOLUME_ENDS_WITH = '.' + TAR_SUFFIX
DESCRIPTOR_ENDS_WITH = '.' + DESCRIPTOR_SUFFIX

SUCCESS_FLAG_FILE = "BACKUP_OK"
BACKUP_META_FILE = "backup.metadata"

BUR_FILE_LIST_DESCRIPTOR_FILE_NAME = "bur_file_list_descriptor{}".format(DESCRIPTOR_ENDS_WITH)
BUR_VOLUME_LIST_DESCRIPTOR_FILE_NAME = "bur_volume_list_descriptor{}".format(DESCRIPTOR_ENDS_WITH)

LOG_ROOT_PATH_CLI = "--log_root_path"

TIMEOUT = 120
LOG_LEVEL = "LogLevel=ERROR"

BLOCK_SIZE_MB_STR = "MB"
BLOCK_SIZE_GB_STR = "GB"

BLOCK_SIZE_MB = 1000
BLOCK_SIZE_GB = 1024

DEFAULT_NUM_THREADS = 5
DEFAULT_NUM_PROCESSORS = 5
DEFAULT_NUM_TRANSFER_PROCS = 8

PLATFORM_NAME = str(platform).lower()

DF_COMMAND_AVAILABLE_SPACE_INDEX = 3
DF_COMMAND_MOUNTED_ON_INDEX = 5

TAR_CMD = "gtar" if 'sun' in PLATFORM_NAME else "tar"

META_DATA_KEYS = Enum('META_DATA_KEYS', 'objects, md5')


VOLUME_OUTPUT_KEYS = Enum('VOLUME_OUTPUT_KEYS', 'volume_path, processing_time, tar_time, output, '
                                                'status, rsync_output, transfer_time')

NOT_INFORMED_STR = "Not informed"

GENIE_VOL_BKPS_DEPLOYMENT = "genie_vol_bkp"

DEFAULT_OFFSITE_RETENTION = 4
DEFAULT_OFFSITE_NAME = "AZURE"
