##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=invalid-name

"""Script to create initial layout for testing."""

import os
import time

from tests.system.config import generator
from tests.system.utils import helpers
from tests.system.utils.constants import BUR_SIM_ENV_PATH, CONFIG_FILE, SIM_FOLDER

from backup.logger import CustomLogger
from backup.utils.fsys import remove_path


SCRIPT_FILE = os.path.basename(__file__).split('.')[0]
logger = CustomLogger(SCRIPT_FILE, "")


def main():
    """Create base layout in filesystem for testing purpose."""
    logger.log_info("Start Creating config file with 2 customers")
    generator.generate(CONFIG_FILE, customer_count=2)

    logger.log_info("Start Creating filesystem layout")

    remove_path(BUR_SIM_ENV_PATH)

    helpers.create_layout(SIM_FOLDER, './conf/valid_filesystem_layout.yml')


if __name__ == '__main__':
    START = time.time()
    main()
    END = time.time()
    logger.log_info("execution time {}".format(END - START))
