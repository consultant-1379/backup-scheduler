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

import sys
import os
import subprocess
import getopt
import ConfigParser


from set_customer_retention_utils import get_logger, Cfg, err_exit

CUSTOMER = None
STDOUT = False
RETENTION_VALUE = "2"

SCRIPT_NAME = os.path.basename(__file__)
DIR = os.path.dirname(os.path.realpath(__file__))
CONF_FILE_NAME = "run_backup_stages.ini"
CONF_FILE = os.path.join(DIR, CONF_FILE_NAME)

USAGE="""
Usage: {script} --customer=CUSTOMER --retention=RETENTION_VALUE\
  [--stdout]

The script uses the file {cfg} for configuration.
"""

def usage(err=1):
    """Display usage and exit.

    Args:
       err: numerical exit code

    Returns: Exits script with exit_val

    Raises: Nothing
    """
    conf_file = os.path.basename(CONF_FILE)
    err_exit(USAGE.format(script=SCRIPT_NAME, cfg=conf_file), err)


def parse_args(argv):
    """Handle command line arguments.  Sets global vars for
       backup tag, LCM IP/host, stage, and backup id.

    Args:
       argv: list of system arguments

    Returns: Nothing

    Raises: Nothing
    """
    # pylint: disable=global-statement

    global CUSTOMER
    global RETENTION_VALUE
    global STDOUT
    # pylint: enable=global-statement

    long_opts = ["customer=", "retention=", "stdout", "help"]

    if not argv:
        usage()

    try:
        opts, _ = getopt.getopt(argv, "h", long_opts)
    except getopt.GetoptError:
        usage()

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt == '--customer':
            CUSTOMER = arg
        elif opt == '--retention':
            RETENTION_VALUE = arg
        elif opt == '--stdout':
            STDOUT = True
        else:
            print("Unknown option {}".format(opt))
            usage()


def cmd(command, log, is_logging=True, env=None):
    """Runs subprocess and returns exit code, stdout & stderr

    Args:
       command: Command and its arguments to run
       is_logging: if it should log or not the command
       env: environment to run command in

    Returns:
        tuple: return code (int), stdout (str), stderr (str)

    Raises: Nothing
    """
    log.info("Running command: " + command)

    try:
        process = subprocess.Popen(command,
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=True,
                                   env=env)

        stdout, stderr = process.communicate()
        log.info("Return code: " + str(process.returncode))

    except (OSError, ValueError, subprocess.CalledProcessError) as err:
        log.error("Failed to run " + command)
        log.exception(err)
        return 1

    if is_logging:
        if stdout:
            log.info("STDOUT: %s", stdout)
        if stderr:
            log.info("STDERR: %s", stderr)
    return process.returncode, stdout, stderr


def set_retention(lcm, retention, enm_key, log):
    """Sets backup retention
       This is a 'stage' method.

    Args: None

    Returns:
        Bool: True if workflows are running
        Str: For script output

    Raises: Nothing (hopefully!)
    """
    log.info("Stage >>> Set retention")
    path = 'enm/applications/bur/services/backup/retention_value'
    consul_cmd = 'consul kv put %s %s' % (path, retention)
    opts = ' -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
    ssh = 'ssh -i %s %s cloud-user@%s ' % (enm_key, opts, lcm)
    result, _, _ = cmd(ssh + consul_cmd, log)

    if result != 0:
        log.error("Failed to set retention")
        msg = "Failed to set consul retention value on " + lcm
        return False
    return True


def main():

    # Parse arguments
    parse_args(sys.argv[1:])

    cfg = Cfg()
    cfg.read_config(CONF_FILE)

    try:
        log = get_logger(cfg, CUSTOMER, STDOUT)
    except (AttributeError,
            ConfigParser.NoOptionError,
            ConfigParser.NoSectionError) as err:
        err_exit("Logging configuration invalid in " + CONF_FILE, 1)

    try:
        customers = cfg.get("general.customers").split(',')
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as err:
        err_exit("Could not get customer list from " + CONF_FILE, 1, log)

    if CUSTOMER not in customers:
        msg = "Customer %s not in list %s, exiting" % (CUSTOMER, customers)
        err_exit(msg, 1, log)

    try:
        lcm = cfg.get(CUSTOMER + ".lcm")
        enm_key = cfg.get(CUSTOMER + ".enm_key")
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as err:
        err_exit("Failed to read item from " + CONF_FILE + " " + err, 1, log)

    log.info("lcm: {}".format(lcm))
    log.info("retention_val: {}".format(RETENTION_VALUE))
    log.info("enm_key: {}".format(enm_key))

    result = set_retention(lcm, RETENTION_VALUE, enm_key, log)

    if result:
        return 0
    elif result is False:
        return 1

    log.error("Stage failed to retrieve info or timed out.  It can be re-ran")
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

