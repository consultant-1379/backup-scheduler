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

"""
Utils script for common use
"""
import ConfigParser
import datetime
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import urllib3

import requests


SCRIPT_NAME = os.path.basename(__file__)
LOG = logging.getLogger(SCRIPT_NAME)

USER_READ_ONLY = 0600


def get_time():
    """
    Return the current time.

    Returns:
        Time object
    """
    return datetime.datetime.now()


def send_mail(email_url, sender, receiver, subject, message):
    """
    Prepares and sends e-mail over configured e-mail service via EMAIL_URL
    configuration property if Deployment's health check has failed.

    Args:
        email_url: url for e-mail service
        sender: from address the email is being sent
        receiver: receiver of the email
        subject: e-mail health check subject.
        message: e-mail health check message.

    Returns:
        True if the e-mail was sent. False if it failed.

    Raises:
        Nothing
    """
    LOG.info("Sending e-mail from '%s' to '%s'.", sender, receiver)

    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except AttributeError:
        pass

    personalisations = [{"to": [{"email": receiver}], "subject": subject}]
    json_string = {"personalizations": personalisations,
                   "from": {"email": sender},
                   "content": [{"type": "text/plain", "value": message}]}

    post_data = json.dumps(json_string).encode("utf8")
    hdrs = {'cache-control': 'no-cache', 'content-type': 'application/json'}

    resp = requests.post(email_url, data=post_data, headers=hdrs, verify=False)

    try:
        resp.raise_for_status()
    except requests.exceptions.RequestException as err:
        LOG.error("Exception sending mail: %s", err)
        LOG.error("Failed to send e-mail to: '%s'", receiver)
        return False

    LOG.info("Sent e-mail to: '%s'.", receiver)
    return True


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

    print msg
    sys.exit(code)


def to_seconds(duration):
    """Converts time string to second, where string is of form,
       3h, 5m, 20s etc

    Args:
       duration: str with numeric value suffixed with h, s, or m

    Returns:
        int: Seconds represented by the duration

    Raises:
        ValueError, KeyError if the string cannot be parsed.
    """

    try:
        units = {"s": 1, "m": 60, "h": 3600}
        return int(float(duration[:-1]) * units[duration[-1]])

    except KeyError:
        raise KeyError("Unit invalid (must be 's', 'h' or 'm')")
    except (ValueError, NameError):
        raise ValueError('The value informed is in the wrong format')


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
    log_file = os.path.basename(log_file)
    log_file = log_dir + '/' + customer + '_' + log_file

    log_level = getattr(logging, cfg.get("logging.level").upper(), None)

    logging.basicConfig(level=log_level,
                        format=log_fmt,
                        datefmt=log_date,
                        filename=log_file)

    if stdout:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(log_level)
        formatter = logging.Formatter(log_fmt, log_date)
        stream_handler.setFormatter(formatter)
        log.addHandler(stream_handler)
    return log


def post_http(url, data, log):
    """Post HTTP request.

    Args:
        url (str): URL to POST
        data (str): Data to POST
        log (Logger): Instance of Logger class

    Returns:
        dict: JSON response data

    Raises:
        ValueError, RequestException
    """
    log.info('POST request: %s', url)
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}

    try:
        result = requests.post(url, data=data, headers=headers)
        result.raise_for_status()
    except (ValueError, requests.exceptions.RequestException) as err:
        log.error("Failed to post http request: %s" % err)
        return {}
    try:
        return result.json()
    except ValueError:
        return {}


def get_http_request(url, log):
    """Get HTTP request.

    Args:
        url (str): URL to GET
        log (Logger): Instance of Logger class

    Returns:
        list: of dicts representing JSON response data

    Raises:
        Nothing
    """
    log.info('GET request: %s', url)
    try:
        result = requests.get(url)
        result.raise_for_status()
    except (ValueError, requests.exceptions.RequestException) as err:
        log.error("Failed to get http request: %s" % err)
        return []

    try:
        return result.json()
    except ValueError as err:
        log.error("Could not decode response: %s" % err)
        return []


def cmd(command, is_logging=True, env=None):
    """Runs subprocess and returns exit code, stdout & stderr

    Args:
       command: Command and its arguments to run
       is_logging: if it should log or not the command
       env: environment to run command in

    Returns:
        tuple: return code (int), stdout (str), stderr (str)

    Raises: Nothing
    """
    LOG.info("Running command: " + command)

    try:
        process = subprocess.Popen(command,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=True,
                                   env=env)

        stdout, stderr = process.communicate()
        LOG.info("Return code: " + str(process.returncode))

    except (OSError, ValueError, subprocess.CalledProcessError) as err:
        LOG.error("Failed to run " + command)
        LOG.exception(err)
        return 1

    if is_logging:
        if stdout:
            LOG.info("STDOUT: %s", stdout)
        if stderr:
            LOG.info("STDERR: %s", stderr)
    return process.returncode, stdout, stderr


def get_keystone_env(keystone_file):
    """Open keystone file and create environment dictionary from it

    Args:
        keystone_file: Filename of keystone rc file

    Returns:
        dict: Built from keystone rc file

    Raises: Nothing
    """
    keystone_env = {}
    try:
        with open(keystone_file, 'r') as keystone:
            keystone_lines = keystone.readlines()
    except (IOError, ValueError) as err:
        LOG.error("Failed to read %s", keystone_file)
        LOG.exception(err)
        return keystone_env

    for line in keystone_lines:
        if '#' in line or 'export' not in line:
            continue

        line = line.replace('export ', '').translate(None, '\n\'" ')
        entry = dict([line.split("=", 1)])

        keystone_env.update(entry)

    return keystone_env


def ping(host, retries=3, wait=5):
    """ping host

    Args:
        host: Hostname or IP address to ping
        retries: number of retry attempts
        wait: seconds to wait between retries

    Returns:
        bool: True/False on success or failure

    Raises: Nothing
    """

    for i in xrange(retries):
        ret, _, _ = cmd('ping -c 1 ' + host, is_logging=False)
        if ret == 0:
            return True
        LOG.warning("Ping attempt %s failed", i)
        time.sleep(wait)

    LOG.error("Ping failed for host %s", host)
    return False


def check_private_key(user, key_file, host):
    """Validate a private key by ssh-ing to host

    Args:
        user: Login user for ssh
        key_file: Path to private key
        host: Host/IP to ssh to

    Returns:
        bool: True/False on success or failure

    Raises: Nothing
    """
    opts = '-o BatchMode=Yes'
    opts = '-o StrictHostKeyChecking=no ' + opts
    opts = '-o UserKnownHostsFile=/dev/null ' + opts
    ssh_cmd = 'ssh -i %s %s %s@%s hostname' % (key_file, opts, user, host)

    if not os.path.isfile(key_file):
        LOG.warning("Key file %s does not exist", key_file)
        return False

    ret, _, err = cmd(ssh_cmd, is_logging=False)
    if ret == 0:
        return True

    LOG.warning("ssh to %s failed using key %s: %s", host, key_file, err)
    return False


def openstack(command, env):
    """Run an OpenStack command using the OpenStack CLI.

    Args:
        command: The command to be ran
        env: Dict of environment variables for command

    Returns:
        tuple: return code (int), stdout (str), stderr (str)

    Raises: Nothing
    """

    os_cmd = "openstack --insecure %s" % command
    return cmd(os_cmd, env=env, is_logging=False)


def get_key_names_from_stack(env):
    """Retrieve OpenStack keypair stacks.

    Args:
        env: Dict of environment variables for command

    Returns:
        list: list of names of keypair stacks

    Raises: Nothing
    """
    stack_list = "stack list -c 'Stack Name' -f value"
    ret, out, err = openstack(stack_list, env)

    if ret != 0:
        LOG.error("OpenStack stack list failed: %s", err)
        return []

    stacks = out.split('\n')
    candidates = [s for s in stacks if 'cu_key' in s]
    if not candidates:
        LOG.error("No keys found in stack listing")
    return candidates


def get_private_key(key_name, env):
    """Return the private key from an OpenStack keypair stack.

    Args:
        key_name: Name of keypair stack
        env: Dict of environment variables for command

    Returns:
        string: containing private key
        None: on failure

    Raises: Nothing
    """
    show_key = "stack show %s -f json" % key_name
    ret, out, err = openstack(show_key, env)

    if ret != 0:
        LOG.error("OpenStack stack show failed: %s", err)
        return None

    try:
        os_json = json.loads(out)
    except (TypeError, ValueError):
        LOG.error("Failed to load JSON from OpenStack")
        return None

    if 'outputs' not in os_json:
        LOG.error("JSON is not in expected format")
        return None

    private_key = None
    for item in os_json['outputs']:
        try:
            output_key = item['output_key']
            if output_key == 'cloud_user_private_key':
                private_key = item['output_value']
        except (KeyError, TypeError, ValueError):
            pass

    if not private_key:
        LOG.error("Failed to get private key from OpenStack output")
    return private_key


def create_temp_key_file(key):
    """Creates a temporary private key file

    Args:
        key: Private key contents

    Returns:
        file: File object representing the temp file

    Raises: Nothing
    """
    try:
        temp_file = tempfile.NamedTemporaryFile(mode='w+t')
        temp_file.write(key)
        temp_file.flush()
        os.chmod(temp_file.name, USER_READ_ONLY)
    except (OSError, IOError):
        LOG.error("Failed to set up temp key file")
        return None

    return temp_file


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
