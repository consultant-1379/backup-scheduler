##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""This script holds required constants necessary to be used in System tests."""

import os

from backup.utils.fsys import get_home_dir, get_path_to_docs

MOCK_BASE_PACKAGE = 'backup.logger'

CUSTOMER_FOLDER_PREFIX_NFS = 'customer_deployment_'
CUSTOMER_FOLDER_PREFIX = 'CUSTOMER_'
VOL_FOLDER_PREFIX = 'volume'

NFS_FOLDER_NAME = 'rpc_bkps'
RESTORE_FOLDER_NAME = 'restore'
BUR_SIM_ENV_FOLDER = 'bur_env'
BUR_BKP_TMP_FOLDER = 'backup_tmp'

MOCK_OFFSITE_RELATIVE_PATH = os.path.join('mock', NFS_FOLDER_NAME)
SIM_FOLDER = get_path_to_docs()
BUR_SIM_ENV_PATH = os.path.join(SIM_FOLDER, BUR_SIM_ENV_FOLDER)
BACKUP_TEMP_PATH = os.path.join(BUR_SIM_ENV_PATH, BUR_BKP_TMP_FOLDER)
SYS_TEST_LOG_PATH = os.path.join(BUR_SIM_ENV_PATH, 'logs')
BUR_UPLOAD_LOG_PATH = os.path.join(SYS_TEST_LOG_PATH, 'CUSTOMER_{}_upload.log')
BUR_ALL_UPLOAD_LOG_PATH = os.path.join(SYS_TEST_LOG_PATH, 'all_customers_upload.log')
BUR_DOWNLOAD_LOG_PATH = os.path.join(SYS_TEST_LOG_PATH, 'CUSTOMER_{}_{}_download.log')

CONFIG_FILE = os.path.join(get_home_dir(), 'backup/config/config.cfg')
