##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""This script automatically perform setUpClass and TearDown methods as declared in a base class."""

import os
import shutil
import unittest

from tests.system.utils.constants import BUR_SIM_ENV_PATH


class SystemTestBaseClass(unittest.TestCase):
    """On inherited classes, run setUp and TearDown methods."""

    @classmethod
    def setUpClass(cls):
        """Remove existing bur testing environment and log files."""
        if os.path.exists(BUR_SIM_ENV_PATH):
            shutil.rmtree(BUR_SIM_ENV_PATH)

    def tearDown(self):
        """Remove left over layout files and log from test execution."""
        shutil.rmtree(BUR_SIM_ENV_PATH)
