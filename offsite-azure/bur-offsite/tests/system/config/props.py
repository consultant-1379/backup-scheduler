##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Define name of sections and items in the config file."""

from getpass import getuser
from os.path import join

from backup.utils.fsys import get_path_to_docs

BUR_ENV_PATH = join(get_path_to_docs(), 'bur_env')

SEC_SUPPORT_CONTACT = 'SUPPORT_CONTACT'
ITEM_EMAIL_TO = 'EMAIL_TO'
ITEM_EMAIL_TO_VAL = 'ericsson@ericsson.com'
ITEM_EMAIL_URL = 'EMAIL_URL'
ITEM_EMAIL_URL_VAL = 'http://127.0.0.1'

SEC_GNUPG = 'GNUPG'
ITEM_GPG_USER_NAME = 'GPG_USER_NAME'
ITEM_GPG_USER_NAME_VAL = 'backup'
ITEM_GPG_USER_EMAIL = 'GPG_USER_EMAIL'
ITEM_GPG_USER_EMAIL_VAL = 'backup@root.com'

SEC_ONSITE_PARAMS = 'ONSITE_PARAMS'
ITEM_BKP_TEMP_FOLDER = 'BKP_TEMP_FOLDER'
ITEM_BKP_TEMP_FOLDER_VAL = join(BUR_ENV_PATH, 'backup_tmp')

SEC_OFFSITE_CONN = 'OFFSITE_CONN'
ITEM_IP = 'IP'
ITEM_IP_VAL = '127.0.0.1'
ITEM_USER = 'USER'
ITEM_USER_VAL = getuser()
ITEM_BKP_PATH = 'BKP_PATH'
ITEM_BKP_PATH_VAL = join(BUR_ENV_PATH, 'mock')
ITEM_BKP_DIR = 'BKP_DIR'
ITEM_BKP_DIR_VAL = 'rpc_bkps'
ITEM_RETENTION = 'RETENTION'
ITEM_RETENTION_VAL = 4

SEC_CUSTOMER = 'CUSTOMER_{}'
CUSTOMER_PATH = 'CUSTOMER_PATH'
CUSTOMER_PATH_VAL = join(BUR_ENV_PATH, ITEM_BKP_DIR_VAL, 'customer_deployment_{}')

SEC_DELAY = 'DELAY'
ITEM_BKP_MAX_DELAY = 'BKP_MAX_DELAY'
ITEM_BKP_MAX_DELAY_VAL = '10s'
