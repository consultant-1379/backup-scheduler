##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""This module if for unit testing the utils.validator.py script."""

import unittest

from backup.exceptions import UtilsException
import backup.utils.validator as validator

EXPECTED_ERROR_MESSAGE = "Value not informed."


class ValidatorCheckNotEmptyTestCase(unittest.TestCase):
    """Test cases for check_not_empty function."""

    def test_check_not_empty(self):
        """Assert if returns True when checking a valid value."""
        result = validator.check_not_empty("test")
        self.assertTrue(result)

    def test_check_not_empty_spaces_string_value(self):
        """Assert if raises an exception when checking spaces string as parameter."""
        with self.assertRaises(UtilsException) as raised:
            validator.check_not_empty("         ")

        self.assertEqual(EXPECTED_ERROR_MESSAGE, raised.exception.message)

    def test_check_not_empty_new_line_value(self):
        """Assert if raises an exception when checking a new line character as parameter."""
        with self.assertRaises(UtilsException) as raised:
            validator.check_not_empty("\n")

        self.assertEqual(EXPECTED_ERROR_MESSAGE, raised.exception.message)

    def test_check_not_empty_tab_value(self):
        """Assert if raises an exception when checking a tab character as parameter."""
        with self.assertRaises(UtilsException) as raised:
            validator.check_not_empty("\t")

        self.assertEqual(EXPECTED_ERROR_MESSAGE, raised.exception.message)

    def test_check_not_empty_empty_string_value(self):
        """Assert if raises an exception when checking empty string as parameter."""
        with self.assertRaises(UtilsException) as raised:
            validator.check_not_empty("")

        self.assertEqual(EXPECTED_ERROR_MESSAGE, raised.exception.message)

    def test_check_not_empty_empty_dict_value(self):
        """Assert if raises an exception when checking empty dictionary as parameter."""
        with self.assertRaises(UtilsException) as raised:
            validator.check_not_empty({})

        self.assertEqual(EXPECTED_ERROR_MESSAGE, raised.exception.message)

    def test_check_not_empty_empty_list_value(self):
        """Assert if raises an exception when checking empty list as parameter."""
        with self.assertRaises(UtilsException) as raised:
            validator.check_not_empty([])

        self.assertEqual(EXPECTED_ERROR_MESSAGE, raised.exception.message)

    def test_check_not_empty_none_value(self):
        """Assert if raises an exception when checking None as parameter."""
        with self.assertRaises(UtilsException) as raised:
            validator.check_not_empty(None)

        self.assertEqual(EXPECTED_ERROR_MESSAGE, raised.exception.message)
