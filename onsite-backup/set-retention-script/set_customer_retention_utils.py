#!/usr/bin/env python
##############################################################################
# COPYRIGHT Ericsson AB 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import logging
import os
import sys
import ConfigParser

SCRIPT_NAME = os.path.basename(__file__)


class Cfg(object):
    """ Class to handle config file parameter reading
    """

    def __init__(self):
        self.conf = ConfigParser.SafeConfigParser()

    def read_config(self, config_file):
        """
        Create an object with configurations passed by within 'config_file'
        :param config_file: An .ini file providing script parameters
        :return: self with the configuration items
        """
        self.conf.read(config_file)

    def get(self, key, raw=False):
        """
        Get a value from the items
        :param raw: True if is to be brought without any format
        :param key: 'key' is in format 'section.option' param for ConfigParser.
        :return: a boolean value from the configuration file
        """
        section, option = key.split('.', 1)
        return self.conf.get(section, option, raw)

    def get_int(self, key):
        """
        Get a int value from the items
        :param key: 'key' is in format 'section.option' param for ConfigParser.
        :return: a boolean value from the configuration file
        """
        section, option = key.split('.', 1)
        return self.conf.getint(section, option)

    def get_bool(self, key):
        """
        Get a boolean value from the items
        :param key: 'key' is in format 'section.option' param for ConfigParser.
        :return: a boolean value from the configuration file
        """
        section, option = key.split('.', 1)
        return self.conf.getboolean(section, option)


def get_logger(cfg, customer, stdout=False):
    """Configures and returns a logger object

    Args:
       cfg: Object holding ini file configuration, including logging config
       customer: Name of customer to prepend log file name with
       stdout: Boolean to control logging to standard out

    Returns:
        log: Log object

    Raises: AttributeError, ConfigParser.NoOptionError,
            ConfigParser.NoSectionError
    """
    log = logging.getLogger(SCRIPT_NAME)

    log_fmt = cfg.get("logging.format", raw=True)
    log_date = cfg.get("logging.datefmt", raw=True)
    log_file = cfg.get("logging.log_file")
    log_dir = os.path.dirname(log_file)
    log_name_field = "set_customer_retention.log"
    customer_log_name_field = customer + '_' + log_name_field
    log_name = os.path.join(log_dir, customer_log_name_field)

    log_level = getattr(logging, cfg.get("logging.level").upper(), None)

    logging.basicConfig(level=log_level,
                        format=log_fmt,
                        datefmt=log_date,
                        filename=log_name)

    if stdout:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(log_level)
        formatter = logging.Formatter(log_fmt, log_date)
        stream_handler.setFormatter(formatter)
        log.addHandler(stream_handler)
    return log


def err_exit(msg, code=1, log=None):
    """Print and optionally log an error message then exit

    Args:
       msg:  str error message
       code: int exit code, default 1
       log:  logger object, default None

    Returns:
        Nothing.  System exit.

    Raises:
        Nothing.
    """
    if log:
        log.error(msg)

    print(msg)
    sys.exit(code)
