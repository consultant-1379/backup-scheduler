##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Managing machine-specific config file for system tests."""

import ConfigParser
import errno
import os

from tests.system.config.props import CUSTOMER_PATH, CUSTOMER_PATH_VAL, \
    ITEM_BKP_DIR, ITEM_BKP_DIR_VAL, ITEM_BKP_MAX_DELAY, ITEM_BKP_MAX_DELAY_VAL, \
    ITEM_BKP_PATH, ITEM_BKP_PATH_VAL, ITEM_BKP_TEMP_FOLDER, ITEM_BKP_TEMP_FOLDER_VAL, \
    ITEM_EMAIL_TO, ITEM_EMAIL_TO_VAL, ITEM_EMAIL_URL, ITEM_EMAIL_URL_VAL, \
    ITEM_GPG_USER_EMAIL, ITEM_GPG_USER_EMAIL_VAL, ITEM_GPG_USER_NAME, ITEM_GPG_USER_NAME_VAL, \
    ITEM_IP, ITEM_IP_VAL, ITEM_RETENTION, ITEM_RETENTION_VAL, ITEM_USER, ITEM_USER_VAL, \
    SEC_CUSTOMER, SEC_DELAY, SEC_GNUPG, SEC_OFFSITE_CONN, SEC_ONSITE_PARAMS, SEC_SUPPORT_CONTACT

CONFIG_EXT = '.cfg'
BACKUP_EXT = '.bk'


def generate(conf_file, customer_count, need_backup=True):
    """
    Generate config file and create backup from original one if necessary.

    :param conf_file: Generation path of the config file.
    :param customer_count: Number of customer section in the conf file.
    :param need_backup: Create a backup from existing config file in the "conf_path".
    :raise ValueError: If the the given conf_file is not pointing to a .cfg file.
    """
    if not validate_conf_file(conf_file):
        raise ValueError('.cfg file is required but {} given.'.format(conf_file))

    create_conf_path(conf_file)

    config = ConfigParser.ConfigParser()
    config.optionxform = str

    if need_backup:
        create_backup(conf_file)
    with open(conf_file, 'w') as cfile:
        add_support_contact_section(config)
        add_gnupg_section(config)
        add_onsite_section(config)
        add_offsite_section(config)
        add_customer_section(config, customer_count)
        add_delay_section(config)
        config.write(cfile)


def create_backup(conf_file):
    """
    Create backup if request in initialize time.

    :param conf_file: Generation path of the config file.
    """
    if os.path.exists(conf_file):
        os.rename(conf_file, conf_file + BACKUP_EXT)


def add_support_contact_section(config):
    """
    Add [SUPPORT_CONTACT] section and its items inside conf file.

    :param config: Parse config instance to set property item on.
    """
    config.add_section(SEC_SUPPORT_CONTACT)
    config.set(SEC_SUPPORT_CONTACT, ITEM_EMAIL_TO, ITEM_EMAIL_TO_VAL)
    config.set(SEC_SUPPORT_CONTACT, ITEM_EMAIL_URL, ITEM_EMAIL_URL_VAL)


def add_gnupg_section(config):
    """
    Add [GNUPG] section and its items inside conf file.

    :param config: Parse config instance to set property item on.
    """
    config.add_section(SEC_GNUPG)
    config.set(SEC_GNUPG, ITEM_GPG_USER_NAME, ITEM_GPG_USER_NAME_VAL)
    config.set(SEC_GNUPG, ITEM_GPG_USER_EMAIL, ITEM_GPG_USER_EMAIL_VAL)


def add_onsite_section(config):
    """
    Add [ONSITE_PARAMS] section and its items inside conf file.

    :param config: Parse config instance to set property item on.
    """
    config.add_section(SEC_ONSITE_PARAMS)
    config.set(SEC_ONSITE_PARAMS, ITEM_BKP_TEMP_FOLDER, ITEM_BKP_TEMP_FOLDER_VAL)


def add_offsite_section(config):
    """
    Add [OFFSITE_CONN] section and its items inside conf file.

    :param config: Parse config instance to set property item on.
    """
    config.add_section(SEC_OFFSITE_CONN)
    config.set(SEC_OFFSITE_CONN, ITEM_IP, ITEM_IP_VAL)
    config.set(SEC_OFFSITE_CONN, ITEM_USER, ITEM_USER_VAL)
    config.set(SEC_OFFSITE_CONN, ITEM_BKP_PATH, ITEM_BKP_PATH_VAL)
    config.set(SEC_OFFSITE_CONN, ITEM_BKP_DIR, ITEM_BKP_DIR_VAL)
    config.set(SEC_OFFSITE_CONN, ITEM_RETENTION, ITEM_RETENTION_VAL)


def add_customer_section(config, customer_count):
    """
    Add [CUSTOMER_X] section and its items inside conf file.

    :param config: Parse config instance to set property item on.
    :param customer_count: Number of customer section in the conf file.
    """
    for customer_num in range(customer_count):
        customer_section = SEC_CUSTOMER.format(customer_num)
        config.add_section(customer_section)
        config.set(customer_section, CUSTOMER_PATH, CUSTOMER_PATH_VAL.format(customer_num))


def add_delay_section(config):
    """
    Add [DELAY] section and its items inside conf file.

    :param config: Parse config instance to set property item on.
    """
    config.add_section(SEC_DELAY)
    config.set(SEC_DELAY, ITEM_BKP_MAX_DELAY, ITEM_BKP_MAX_DELAY_VAL)


def validate_conf_file(conf_file):
    """
    Validate if the given file extension conforms to the BUR.

    :param conf_file: Given config file in absolute path
    :return: True if comply with BUR otherwise False
    """
    _, ext = os.path.splitext(conf_file)
    if ext.strip() != CONFIG_EXT:
        return False
    return True


def create_conf_path(conf_file):
    """
    Create directory structure lead to conf file.

    :param conf_file: Given config file in absolute path.
    :raise OSError: if there is issue creating directories.
    """
    if os.path.dirname(conf_file):
        try:
            os.makedirs(os.path.dirname(conf_file))
        except OSError as ex:
            if ex.errno == errno.EEXIST:
                pass
            else:
                raise OSError('Issue creating requested directories: {}'.format(str(ex)))


def replace_to_origin_conf(conf_file):
    """
    Remove config left from tests and replace origin conf back in place.

    :param conf_file: Given config file in absolute path
    """
    name, _ = os.path.splitext(conf_file)
    origin_conf_file = name + CONFIG_EXT + BACKUP_EXT
    if not os.path.exists(origin_conf_file):
        return

    if os.path.exists(conf_file):
        os.remove(conf_file)

    os.rename(origin_conf_file, conf_file)
