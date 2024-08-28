##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=R0902,C0103,R0913,E0401,R0903
# too-many-instance-attributes
# invalid-name(snake_case comments)
# too-many-arguments
# import-error
# too-few-public-methods


"""Module for processing config.cfg file."""

from ConfigParser import ConfigParser, MissingSectionHeaderError, NoOptionError, NoSectionError, \
    ParsingError
import os

from backup.constants import DEFAULT_OFFSITE_NAME, DEFAULT_OFFSITE_RETENTION
from backup.exceptions import BackupSettingsException, ExceptionCodes
from backup.gnupg_manager import GnupgManager
from backup.logger import CustomLogger
from backup.notification_handler import NotificationHandler
from backup.utils.datetime import to_seconds
from backup.utils.fsys import get_home_dir

SCRIPT_FILE = os.path.basename(__file__).split('.')[0]

SYSTEM_CONFIG_FILE_ROOT_PATH = os.path.join(get_home_dir(), "backup", "config")
DEFAULT_CONFIG_FILE_ROOT_PATH = os.path.join(os.path.dirname(__file__), 'config')


class SupportInfo:
    """Class used to store sourced information about the support contact."""

    def __init__(self, email, server):
        """
        Initialize Support Info object.

        :param email: support email info.
        :param server: email server.
        """
        self.email = email
        self.server = server

    def __str__(self):
        """Represent Support Info object as string."""
        return "({}, {})".format(self.email, self.server)

    def __repr__(self):
        """Represent Support Info object."""
        return self.__str__()


class OffsiteConfig:
    """Class used to store sourced information about the off-site backup location."""

    def __init__(self, ip, user, path, folder, retention, storage_account, container_name, name=DEFAULT_OFFSITE_NAME):
        """
        Initialize Offsite Config object.

        :param ip: ip of the server.
        :param user: user allowed to access the server.
        :param path: path in which the backup folder will be placed.
        :param folder: backup folder's name.
        :param name: name of offsite location.
        """
        self.name = name
        self.ip = ip
        self.user = user
        self.path = path
        self.folder = folder
        self.full_path = os.path.join(path, folder)
        self.host = user + '@' + ip
        self.storage_account = storage_account
        self.container_name = container_name
        self.full_container_path = os.path.join(storage_account, container_name)
        self.retention = retention

    def __str__(self):
        """Represent Offsite Config object as string."""
        return "({}, {}, {}, {})".format(self.name, self.ip, self.user, self.full_path)

    def __repr__(self):
        """Represent Offsite Config object."""
        return self.__str__()


class OnsiteConfig:
    """Class used to store sourced information about the onsite backup location."""

    def __init__(self, temp_path):
        """
        Initialize Onsite Config object.

        :param temp_path: temporary folder to store files during the backup process.
        """
        self.temp_path = temp_path

    def __str__(self):
        """Represent Onsite Config object as string."""
        return "({})".format(self.temp_path)

    def __repr__(self):
        """Represent Onsite Config object."""
        return self.__str__()


class EnmConfig:
    """Class used to store sourced information about the backup location of a customer."""

    def __init__(self, name, path):
        """
        Initialize ENM Config object.

        :param name: deployment name from the configuration section.
        :param path: backup path.
        """
        self.name = name
        self.backup_path = path

    def __str__(self):
        """Represent EnmConfig object as string."""
        return "({}, {})".format(self.name, self.backup_path)

    def __repr__(self):
        """Represent EnmConfig object."""
        return self.__str__()


class DelayConfig:
    """Class for holding delay configurations from config file."""

    def __init__(self, max_delay):
        """
        Initialize DelayConfig object.

        :param max_delay: max seconds of how long the upload process can take.
        """
        self.max_delay = max_delay

    def __str__(self):
        """Represent DelayConfig object as string."""
        return "({})".format(self.max_delay)

    def __repr__(self):
        """Represent DelayConfig object."""
        return self.__str__()


class ScriptSettings:
    """
    Class used to store and validate data from the configuration file.

    Configuration file will be checked first in $USER_HOME/backup/config/config.cfg and then at
    the directory "config" in the same level as the script.
    """

    def __init__(self, config_file_name, logger):
        """
        Initialize Script Settings object.

        :param config_file_name: name of the configuration file.
        :param logger: logger object.
        """
        self.config_file_name = config_file_name

        self.config_file_path = self._get_config_file_path()

        self.logger = CustomLogger(SCRIPT_FILE, logger.log_root_path, logger.log_file_name,
                                   logger.log_level)

        self.config = self._get_config_details()

    def _get_config_file_path(self):
        """
        Verify the path to config file.

        :return: config file pathname.
        """
        config_root_path = SYSTEM_CONFIG_FILE_ROOT_PATH
        if not os.access(config_root_path, os.R_OK):
            config_root_path = DEFAULT_CONFIG_FILE_ROOT_PATH

        return os.path.join(config_root_path, self.config_file_name)

    def _get_config_details(self):
        """
        Read the configuration file and create the main objects used by the system.

        Errors that occur during this process are appended to the validation error list.

        :return: a dictionary with the system objects.
        :raise BackupSettingsException: if the configuration file cannot be parsed.
        """
        if not os.access(self.config_file_path, os.R_OK):
            raise BackupSettingsException(ExceptionCodes.ConfigurationFileReadError,
                                          self.config_file_path)

        try:
            config = ConfigParser()
            config.readfp(open(self.config_file_path))

        except (AttributeError, MissingSectionHeaderError, ParsingError) as error:
            raise BackupSettingsException(ExceptionCodes.ConfigurationFileParsingError, error)

        except IOError as error:
            raise BackupSettingsException(ExceptionCodes.ConfigurationFileReadError, error)

        self.logger.info("Reading configuration file '%s'.", self.config_file_path)

        return config

    def get_notification_handler(self):
        """
        Read support contact section from the config file.

        :return: the notification handler with the informed data.
        :raise BackupSettingsException: if the configuration file cannot be parsed.
        """
        try:
            support_info = SupportInfo(str(self.config.get('SUPPORT_CONTACT', 'EMAIL_TO')),
                                       str(self.config.get('SUPPORT_CONTACT', 'EMAIL_URL')))
        except NoSectionError as error:
            raise BackupSettingsException(ExceptionCodes.MissingSupportContactSection, error)

        except NoOptionError as error:
            raise BackupSettingsException(ExceptionCodes.ConfigurationFileOptionError, error)

        self.logger.info("The following support information was defined: %s.", support_info)

        return NotificationHandler(support_info.email, support_info.server, self.logger)

    def get_gnupg_manager(self):
        """
        Read GPG information section from the config file.

        :return: an object with the gnupg information.
        :raise BackupSettingsException: if the configuration file cannot be parsed.
        """
        try:
            gpg_manager = GnupgManager(str(self.config.get('GNUPG', 'GPG_USER_NAME')),
                                       str(self.config.get('GNUPG', 'GPG_USER_EMAIL')),
                                       self.logger)
        except NoSectionError as error:
            raise BackupSettingsException(ExceptionCodes.MissingGnupgSection, error)

        except NoOptionError as error:
            raise BackupSettingsException(ExceptionCodes.ConfigurationFileOptionError, error)

        self.logger.info("The following gnupg information was defined: %s.", gpg_manager)

        return gpg_manager

    def get_offsite_config(self):
        """
        Read offsite connection section from config file.

        :return: an object with the offsite information.
        :raise BackupSettingsException: if the configuration file cannot be parsed.
        """
        try:
            try:
                retention = self.config.getint('OFFSITE_CONN', 'RETENTION')
            except (NoOptionError, KeyError, ValueError):
                self.logger.warning("Retention not configured. Using default value: {}."
                                    .format(DEFAULT_OFFSITE_RETENTION))
                retention = DEFAULT_OFFSITE_RETENTION

            offsite_config = OffsiteConfig(self.config.get('OFFSITE_CONN', 'IP'),
                                           self.config.get('OFFSITE_CONN', 'USER'),
                                           self.config.get('OFFSITE_CONN', 'BKP_PATH'),
                                           self.config.get('OFFSITE_CONN', 'BKP_DIR'),
                                           retention,
                                           self.config.get('OFFSITE_CONN', 'STORAGE_ACCOUNT'),
                                           self.config.get('OFFSITE_CONN', 'CONTAINER_NAME'))
        except NoSectionError as error:
            raise BackupSettingsException(ExceptionCodes.MissingOffSiteSection, error)

        except (NoOptionError, KeyError, ValueError) as error:
            raise BackupSettingsException(ExceptionCodes.ConfigurationFileOptionError, error)

        self.logger.info("The following off-site information was defined: %s.", offsite_config)

        return offsite_config

    def get_onsite_config(self):
        """
        Read onsite settings section from the config file.

        :return: an object with the onsite information.
        :raise BackupSettingsException: if the configuration file cannot be parsed.
        """
        try:
            onsite_config = OnsiteConfig(self.config.get('ONSITE_PARAMS', 'BKP_TEMP_FOLDER'))
        except NoSectionError as error:
            raise BackupSettingsException(ExceptionCodes.MissingOnSiteSection, error)

        except (NoOptionError, KeyError, ValueError) as error:
            raise BackupSettingsException(ExceptionCodes.ConfigurationFileOptionError, error)

        self.logger.info("The following onsite information was defined: %s.", onsite_config)

        return onsite_config

    def get_customer_config_dict(self, customer_name=None):
        """
        Read customer sections from the config file.

        :param customer_name: customer name, if running the script just for one customer.
        :return: dictionary with the information of all customers in the configuration file.
        :raise BackupSettingsException: if the configuration file cannot be parsed.
        """
        try:
            sections = self.config.sections()
            sections.remove('SUPPORT_CONTACT')
            sections.remove('GNUPG')
            sections.remove('OFFSITE_CONN')
            sections.remove('ONSITE_PARAMS')
            sections.remove('DELAY')

            self.logger.info("The following deployments were defined: %s.", sections)

            customer_config_dict = {}

            if customer_name and customer_name.strip():
                self.logger.info("Configuration loaded only for: {}.".format(customer_name))
                path = self.config.get(customer_name, "CUSTOMER_PATH")

                return {customer_name: EnmConfig(customer_name, path)}

            for section in sections:
                path = self.config.get(section, "CUSTOMER_PATH")

                customer_config_dict[section] = EnmConfig(section, path)

        except NoSectionError as error:
            raise BackupSettingsException(ExceptionCodes.MissingCustomerSection, error)

        except NoOptionError as error:
            raise BackupSettingsException(ExceptionCodes.ConfigurationFileOptionError, error)

        return customer_config_dict

    def get_delay_config(self):
        """
        Read delay details from config file.

        :return: a DelayConfig object.
        :raise BackupSettingsException: if the configuration file cannot be parsed.
        """
        try:
            max_delay = to_seconds(self.config.get("DELAY", "BKP_MAX_DELAY"))

            self.logger.log_info("Max running time for a backup upload is defined up to {} seconds."
                                 .format(max_delay))

            return DelayConfig(max_delay)

        except NoSectionError as error:
            raise BackupSettingsException(ExceptionCodes.MissingBackupDelaySection, error)

        except NoOptionError as error:
            raise BackupSettingsException(ExceptionCodes.ConfigurationFileOptionError, error)
