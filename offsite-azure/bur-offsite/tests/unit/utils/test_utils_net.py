##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""The purpose of this module is to provide unit testing for utils.metadata.py script."""

import unittest

from backup.utils.net import is_valid_ip

INVALID_HOST = "2.3.4."
VALID_HOST = '127.0.0.1'


class UtilsNetTestCase(unittest.TestCase):
    """Test Cases for net utility methods located in utils."""

    def test_is_valid_ip(self):
        """Test if ip is valid."""
        self.assertTrue(is_valid_ip(VALID_HOST))

    def test_is_valid_ip_invalid_ip(self):
        """Test invalid ip."""
        self.assertFalse(is_valid_ip(INVALID_HOST))
