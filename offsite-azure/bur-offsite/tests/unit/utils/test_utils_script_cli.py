##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""The purpose of this module is to provide unit testing for script_cli.py utility script."""

import sys
import unittest

import mock

from backup.utils import script_cli

MOCK_BASE_PACKAGE = 'backup.utils.script'


class UtilsScriptTestCase(unittest.TestCase):
    """Test Cases for methods in script_cli.py utility script."""

    def test_get_cli_arguments(self):
        """Assert if the elements ending in .py are removed from the final list."""
        test_args = ['/home/bur/some_script.py', '--script_option', '1', '--do_cleanup', '1']
        expected_result = ['--script_option', '1', '--do_cleanup', '1']

        with mock.patch.object(sys, 'argv', test_args):
            result = script_cli.get_cli_arguments()

        self.assertEqual(expected_result, result)
