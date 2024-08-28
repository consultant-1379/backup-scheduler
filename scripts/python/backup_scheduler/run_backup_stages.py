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

"""Script to be called from the command line to run backup script"""

import ConfigParser
import getopt
import logging
import os
import sys

# pylint: disable=relative-import
from backup_handlers import BackupSequencer
from backup_handlers import BackupStages
from backup_utils import send_mail, err_exit
from backup_utils import to_seconds
from backup_utils import get_logger, Cfg
# pylint: enable=relative-import

CUSTOMER = None
BACKUP_TAG = None
BACKUP_ID = None
STAGE = None
WF_URL = None
LCM = None

SEND_MAIL = True
STDOUT = False
MAIL_TO = None
MAIL_URL = None

SCRIPT_NAME = os.path.basename(__file__)
DIR = os.path.dirname(os.path.realpath(__file__))
CONF_FILE = DIR + '/' + SCRIPT_NAME.split('.')[0] + '.ini'

LOG = logging.getLogger(SCRIPT_NAME)

USAGE = """
Usage: {script} --customer=CUSTOMER --stage=STAGE\
 [--tag=TAG] [--id=ID] [--nomail] [--stdout]

Run a stage in the backup sequence for a customer.

Where:
CUSTOMER is the name of the customer (tenancy/deployment_id)

STAGE     is one of:
          KEY        - Retrieve and validate private key for tenancy
          STORAGE_WF -  Check for banned workflows on all tenancies
          ALL_WF     - Check for any workflow on 'this' tenancy
          RETENTION  - Set the retention policy for backups
          BACKUP     - Trigger Backup
          RUNNING    - Check if Backup is running (requires ID)
          CHECK      - Check state of finished backup (requires ID)
          VALIDATE   - Trigger Backup validation workflow
          METADATA   - Backup Metadata
          FLAG       - Create success flag in backup directory

          ALL        - To Run all the above stages in sequence

          WFS        - WFS runs STORAGE_WF & ALL_WF and waits
          WAIT       - This waits until backup is not running (requires ID)

TAG       is a label for the backup, needed for every stage after BACKUP.
          If TAG is not supplied for ALL and BACKUP then one will be generated.
ID        is the backup id, required for some stages

--nomail  disables the email functionality of the script
--stdout  log to standard output

The script uses the file {cfg} for configuration.
"""


def usage(err=1):
    """Display usage and exit.

    Args:
       exit_val: numerical exit code

    Returns: Exits script with exit_val

    Raises: Nothing
    """
    conf_file = os.path.basename(CONF_FILE)
    err_exit(USAGE.format(script=SCRIPT_NAME, cfg=conf_file), err)


def mailer(subject, message, add_info=False):
    """Function to send email.

    Args:
       subject: string for email subject
       message: string for message
       add_info: boolean to add backup info

    Returns: Nothing

    Raises: Nothing
    """
    if not SEND_MAIL:
        return

    if add_info:
        if LCM and BACKUP_ID:
            url = ("http://%s/index.html#workflows/"
                   "workflow/enmdeploymentworkflows.--."
                   "Backup%%20Deployment/workflowinstance/%s"
                   % (LCM, BACKUP_ID))
        else:
            url = None

        message = """%s
Customer: %s
Tag:      %s
ID:       %s
WF URL:   %s""" % (message, CUSTOMER, BACKUP_TAG, BACKUP_ID, url)

    sender = CUSTOMER + "@no-reply.ericsson.net"

    if not send_mail(MAIL_URL, sender, MAIL_TO, subject, message):
        LOG.warning("Failed to send mail to %s, %s", MAIL_TO, message)


def validate_args(customer, stage, backup_id, backup_tag):
    """Validate command line arguments.

     Args:
        customer: customer string
        stage: stage string
        backup_id: backup id string
        backup_tag: backup tag string

     Returns: Nothing

     Raises: Nothing
     """

    if not stage:
        print "--stage required"
        usage()

    if not customer:
        print "--customer required"
        usage()

    if stage in ('RUNNING', 'CHECK', 'WAIT'):
        if not backup_id:
            print "--id required for stage %s" % stage
            usage()

    # BACKUP_TAG is not needed in stages before BACKUP and can be
    # generated in ALL or BACKUP stages so is not mandatory for them
    if stage not in ('KEY', 'WFS', 'STORAGE_WF', 'ALL_WF',
                     'RETENTION', 'ALL', 'BACKUP'):
        if not backup_tag:
            print "--tag required for stage %s" % stage
            usage()


def parse_args(argv):
    """Handle command line arguments.  Sets global vars for
       backup tag, LCM IP/host, stage, and backup id.

    Args:
       argv: list of system arguments

    Returns: Nothing

    Raises: Nothing
    """
    # pylint: disable=global-statement
    global BACKUP_TAG
    global BACKUP_ID
    global CONF_FILE
    global STAGE
    global CUSTOMER
    global SEND_MAIL
    global STDOUT
    # pylint: enable=global-statement

    long_opts = ["customer=", "cfg=", "tag=", "stage=",
                 "id=", "nomail", "stdout", "help"]

    try:
        opts, _ = getopt.getopt(argv, "h", long_opts)
    except getopt.GetoptError:
        usage()

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt == '--customer':
            CUSTOMER = arg
        elif opt == '--cfg':
            CONF_FILE = arg
        elif opt == '--tag':
            BACKUP_TAG = arg
        elif opt == '--stage':
            STAGE = arg
        elif opt == '--id':
            BACKUP_ID = arg
        elif opt == '--nomail':
            SEND_MAIL = False
        elif opt == '--stdout':
            STDOUT = True
        else:
            print "Unknown option %s" % opt
            usage()

    validate_args(CUSTOMER, STAGE, BACKUP_ID, BACKUP_TAG)


# pylint: disable=too-many-statements,too-many-branches,too-many-locals
def main():
    """Check for any workflows running on 'this' tenancy

    Args: None

    Returns:
        Bool: True if workflows are running

    Raises: Nothing (hopefully!)
    """
    # pylint: disable=global-statement
    global MAIL_URL
    global MAIL_TO
    global LCM
    global BACKUP_TAG
    global BACKUP_ID

    # Parse arguments
    parse_args(sys.argv[1:])

    # Read configuration file
    cfg = Cfg()
    cfg.read_config(CONF_FILE)

    # Set up logging
    try:
        log = get_logger(cfg, CUSTOMER, STDOUT)
    except (AttributeError,
            ConfigParser.NoOptionError,
            ConfigParser.NoSectionError) as err:
        err_exit("Logging configuration invalid in " + CONF_FILE, 1)

    # Run the backup stage
    log.info(">>> %s Started, running stage %s with tag %s  ",
             SCRIPT_NAME,
             STAGE,
             str(BACKUP_TAG))

    try:
        customers = cfg.get("general.customers").split(',')
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as err:
        err_exit("Could not get customer list from " + CONF_FILE, 1, log)

    if CUSTOMER not in customers:
        msg = "Customer %s not in list %s, exiting" % (CUSTOMER, customers)
        err_exit(msg, 1, log)

    try:
        bkup_script = cfg.get("general.backup_script")
        metadata_script = cfg.get("general.metadata_script")
        skip_all_check = cfg.get_bool("general.skip_check_all")
        fail_long_backup = cfg.get_bool("general.fail_long_backup")
        retention = cfg.get_int("general.retention")
        max_delay = to_seconds(cfg.get("timers.max_start_delay"))
        max_time = to_seconds(cfg.get("timers.max_duration"))
        max_validation_time = to_seconds(cfg.get("timers.max_validation_time"))

        nfs = cfg.get("nfs.ip")
        nfs_user = cfg.get("nfs.user")
        nfs_key = cfg.get("nfs.key")
        nfs_path = cfg.get("nfs.path")
        lcm = cfg.get(CUSTOMER + ".lcm")
        LCM = lcm
        enm_key = cfg.get(CUSTOMER + ".enm_key")
        keystone = cfg.get(CUSTOMER + ".keystone_rc")
        cust_dir = cfg.get(CUSTOMER + ".deployment_id")
        nfs_path = nfs_path + '/' + cust_dir

        MAIL_URL = cfg.get("mail.url")
        MAIL_TO = cfg.get("mail.dest")

        blocking_wfs = cfg.get("general.blocking_wfs")

    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as err:
        err_exit("Failed to read item from " + CONF_FILE + " " + err, 1, log)

    try:
        tenancies = {}
        for customer in customers:
            tenancies[customer] = cfg.get(customer + ".lcm")
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError) as err:
        msg = "Failed to read customer info from " + CONF_FILE + " " + err
        err_exit(msg, 1, log)

    if STAGE in ('ALL', 'WFS', 'WAIT'):
        backup_class = BackupSequencer
    else:
        backup_class = BackupStages

    backup = backup_class()

    backup.lcm = lcm
    backup.max_delay = max_delay
    backup.max_time = max_time
    backup.max_validation_time = max_validation_time
    backup.bkup_script = bkup_script
    backup.metadata_script = metadata_script
    backup.tenancies = tenancies
    backup.deployment_id = CUSTOMER
    backup.tag = BACKUP_TAG
    backup.enm_key = enm_key
    backup.keystone = keystone
    backup.nfs = nfs
    backup.nfs_user = nfs_user
    backup.nfs_key = nfs_key
    backup.nfs_path = nfs_path
    backup.skip_all_check = skip_all_check
    backup.fail_long_backup = fail_long_backup
    backup.retention = retention
    backup.log = log
    backup.mail_fn = mailer
    backup.backup_id = BACKUP_ID
    backup.blocking_wfs = blocking_wfs

    output = None
    try:
        if STAGE == 'KEY':
            result = backup.setup_private_key()
        elif STAGE == 'STORAGE_WF':
            result = backup.no_banned_wfs()
        elif STAGE == 'ALL_WF':
            result = backup.no_wfs()
        elif STAGE == 'RETENTION':
            result = backup.set_retention()
        elif STAGE == 'BACKUP':
            result, output = backup.start_backup()
        elif STAGE == 'RUNNING':
            result = backup.is_backup_running()
        elif STAGE == 'CHECK':
            result = backup.backup_completed_ok()
        elif STAGE == 'VALIDATE':
            result = backup.verify_backup_state()
        elif STAGE == 'METADATA':
            result = backup.backup_metadata()
        elif STAGE == 'FLAG':
            result = backup.label_ok()
        elif STAGE == 'ALL':
            result = backup.run()
        elif STAGE == 'WFS':
            result = backup.check_for_wfs()
        elif STAGE == 'WAIT':
            result = backup.wait_for_backup()
        else:
            log.error("Invalid stage %s ", STAGE)
            usage()

    except Exception as err:  # pylint: disable=broad-except
        # External orchestrator can retry this
        log.error("Unknown error occured: %s ", err)
        result = False
        output = "Stage Failed to Run"
        mailer("Backup issue: " + CUSTOMER,
               "Backup script failed, backup might be running. Stage " + STAGE,
               add_info=True)

    if output:
        print output

    if backup.backup_id:
        BACKUP_ID = backup.backup_id

    if backup.tag:
        BACKUP_TAG = backup.tag

    if STAGE == 'ALL':
        if result:
            log.info("Backup Completed Successfully")
            mailer("Backup Successful for " + CUSTOMER,
                   'Backup successful', add_info=True)
        else:
            log.error("Backup Failed")
    else:
        if result:
            log.info("Stage %s Completed Successfully", STAGE)
        else:
            log.error("Stage %s Failed", STAGE)
            if STAGE == 'WAIT':
                mailer("Backup failure: " + CUSTOMER,
                       "Timed out waiting for backup to finish", add_info=True)
            else:
                mailer("Backup failure: " + CUSTOMER,
                       "Backup failed at stage " + STAGE, add_info=True)

    if result:
        return 0
    elif result is False:
        return 1

    log.error("Stage failed to retrieve info or timed out.  It can be re-ran")
    return 2
# pylint: enable=too-many-statements,too-many-branches,too-many-locals

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
