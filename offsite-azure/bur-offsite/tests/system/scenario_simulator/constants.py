##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Constants required in yaml based filesystem scenario creation strategy."""

import os

from backup.logger import CustomLogger


BINARY_FILE_TYPE_KEY = 'binary'
TEXT_FILE_TYPE_KEY = 'text'
BINARY_FILE_RANDOM_CONTENT_VALUE = 'random'

METADATA_FILE_TYPE_KEY = "metadata"
METADATA_VOL_KEY = "volume_meta"
METADATA_VOL_VALUE = "volume_meta"
METADATA_PARENT_ID_VALUE = "null"
METADATA_DESC_VALUE = "mock_backup"
METADATA_VERSION_VALUE = "1.0.0"

METADATA_BACKUP_ID_KEY = 'backup_id'
METADATA_VOL_ID_KEY = 'volume_id'
METADATA_PARENT_ID_KEY = 'parent_id'
METADATA_VERSION_KEY = 'version'
METADATA_CREATED_AT = 'created_at'
METADATA_BACKUP_DESC_KEY = 'backup_description'
METADATA_BACKUP_NAME_KEY = 'backup_name'
METADATA_OBJECTS_KEY = 'objects'
METADATA_OBJECTS_LENGTH = 'length'
METADATA_OBJECTS_OFFSET = 'offset'
METADATA_OBJECTS_COMPRESSION = 'compression'
METADATA_OBJECTS_MD5 = 'md5'

FILE_DESCRIPTOR_FILE_NAME = 'name'
FILE_DESCRIPTOR_FILE_PATH = 'path'
FILE_DESCRIPTOR_FILE_TYPE = 'type'
FILE_DESCRIPTOR_FILE_SIZE = 'size'
FILE_DESCRIPTOR_FILE_CONTENT = 'content'
FILE_DESCRIPTOR_CUSTOMER_ID = 'customer_id'
FILE_DESCRIPTOR_BACKUP_ID = 'backup_id'
FILE_DESCRIPTOR_VOL_ID = 'volume_id'

YAML_FILE_NAME = 'name'
YAML_FILE_TYPE = 'type'
YAML_FILE_SIZE = 'size'
YAML_FILE_CONTENT = 'content'

CUSTOMER_DEPLOYMENT_FOLDER = 'customer_deployment'
BACKUP_VOL_FILE_NAME = 'volume_file'
VOLUME_FOLDER = 'volume'

SIM_PLAN_FOLDERS = 'folders'
SIM_PLAN_FILES = 'files'
SIM_PLAN_LAYOUT = 'layout'
SIM_PLAN_PROCESS = 'to_process'

SUPPORTED_PROCESSING_STEPS = ['tar', 'gpg']

FILE_BLOCK_SIZE = 4096
DIRECTORY_OWNER_ACCESS = 0o700

SCRIPT_PATH = os.path.dirname(__file__)

SYSTEM_TEST_LOGGER = CustomLogger(SCRIPT_PATH, "", "")

YML_SUFFIX = 'yml'

LAYOUT_CONF_PATH = os.path.join(SCRIPT_PATH, 'conf')
LAYOUT_DICT = {layout_file.split('.')[0]: os.path.join(LAYOUT_CONF_PATH, layout_file) for
               layout_file in os.listdir(LAYOUT_CONF_PATH) if YML_SUFFIX in layout_file}
