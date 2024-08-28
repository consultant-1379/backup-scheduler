##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# pylint: disable=too-many-locals,deprecated-method

"""The purpose of this module is to provide unit testing for datetime.py script."""

import time
import unittest

from backup.exceptions import UtilsException
from backup.utils import datetime


def assert_proper_date_time_formatting(assertion, result_date_time):
    """Proper date time formatting should be tested."""
    formatted_date_and_time_contain_two_parts = 2
    date_time_split = result_date_time.split(' ')
    assertion.assertEqual(formatted_date_and_time_contain_two_parts, len(date_time_split))

    date_part = date_time_split[0]
    time_part = date_time_split[1]

    year_month_day_part = date_part.split('-')

    date_should_contain_three_parts = 3
    assertion.assertEqual(date_should_contain_three_parts, len(year_month_day_part))

    year = year_month_day_part[0]
    month = year_month_day_part[1]
    day = year_month_day_part[2]
    assertion.assertRegexpMatches(year, r'^\d{4}$')
    assertion.assertRegexpMatches(month, r'^\d{2}')
    assertion.assertRegexpMatches(day, r'^\d{2}')

    hour_min_sec_part = time_part.split(':')

    time_should_contain_three_parts = 3
    assertion.assertEqual(time_should_contain_three_parts, len(hour_min_sec_part))

    hour = hour_min_sec_part[0]
    minute = hour_min_sec_part[1]
    second = hour_min_sec_part[2]
    assertion.assertRegexpMatches(hour, r'^\d{2}$')
    assertion.assertRegexpMatches(minute, r'^\d{2}')
    assertion.assertRegexpMatches(second, r'^\d{2}')


class TruncateMicrosecondsFromTimestampTestCase(unittest.TestCase):
    """Test Cases for truncate_microseconds_from_timestamp function in datetime.py utils."""

    def test_truncate_microseconds_from_timestamp_value(self):
        """Assert if microseconds is truncated from timestamp."""
        sample_timestamp = 1537999522.94
        result = datetime.truncate_microseconds_from_timestamp(sample_timestamp)
        self.assertEqual(1537999522.0, result)

    def test_truncate_microseconds_from_timestamp_should_return_float(self):
        """Assert if the truncated value result is float type."""
        sample_timestamp = int(1537999522)
        result = datetime.truncate_microseconds_from_timestamp(sample_timestamp)
        self.assertEqual(float(1537999522), result)

    def test_truncate_microseconds_from_timestamp_invalid_input(self):
        """Assert if the function is dealing with abnormal inputs."""
        expected_error_msg = "Invalid value. Check value type or range."

        with self.assertRaises(UtilsException) as raised:
            datetime.truncate_microseconds_from_timestamp('aabb')
        self.assertIn(expected_error_msg, raised.exception.message)

        with self.assertRaises(UtilsException) as raised:
            datetime.truncate_microseconds_from_timestamp(None)
        self.assertIn(expected_error_msg, raised.exception.message)

        with self.assertRaises(UtilsException) as raised:
            datetime.truncate_microseconds_from_timestamp(-123.5435)
        self.assertIn(expected_error_msg, raised.exception.message)


class GetFormattedTimestampTestCase(unittest.TestCase):
    """Test Cases for get_formatted_timestamp function in datetime.py utils."""

    def test_get_formatted_timestamp(self):
        """Assert if the result contains date and time."""
        result = datetime.get_formatted_timestamp()
        assert_proper_date_time_formatting(self, result)


class FormatTimeTestCase(unittest.TestCase):
    """Test Cases for format_time function in datetime.py utils."""

    def test_format_time_should_present_proper_formatting(self):
        """Assert if the method returns expected format presented to it."""
        sample_time = time.time()
        result = datetime.format_time(sample_time, time_format='%Y-%m-%d %H:%M:%S')
        assert_proper_date_time_formatting(self, result)

    def test_formatting_time_should_have_default_formatting(self):
        """Assert if the method only returns appropriate time formatting presented as default."""
        sample_time = time.time()
        result = datetime.format_time(sample_time)
        hour_min_sec_part = result.split(':')

        time_should_contain_three_part = 3
        self.assertEqual(time_should_contain_three_part, len(hour_min_sec_part))

        hour = hour_min_sec_part[0]
        minute = hour_min_sec_part[1]
        second = hour_min_sec_part[2]
        self.assertRegexpMatches(hour, r'^\d{2}$')
        self.assertRegexpMatches(minute, r'^\d{2}')
        self.assertRegexpMatches(second, r'^\d{2}')


class ToSecondsTestCase(unittest.TestCase):
    """Test cases for to_seconds function from datetime.py script."""

    def test_to_seconds_with_hours(self):
        """Assert if 1 hour return 3600 seconds."""
        expected_result = 3600
        self.assertEqual(expected_result, datetime.to_seconds('1h'))

    def test_to_seconds_with_minutes(self):
        """Assert if 1 minute return 60 seconds."""
        expected_result = 60
        self.assertEqual(expected_result, datetime.to_seconds('1m'))

    def test_to_seconds_invalid_format(self):
        """Assert if raises an exception when informing hours and minutes together."""
        with self.assertRaises(UtilsException):
            datetime.to_seconds('2h30m')

    def test_to_seconds_invalid_unit(self):
        """Assert if raises an exception when informing an invalid time unit."""
        expected_error_msg = "Invalid time unit (must be 's' or 'h' or 'm')."

        with self.assertRaises(UtilsException) as err:
            datetime.to_seconds('2v')

        self.assertIn(expected_error_msg, err.exception.message)

    def test_to_seconds_invalid_argument_no_unit(self):
        """Assert if raises an exception when not informing time unit."""
        expected_error_msg = "Wrong format. It must be number + time unit (i.e. 3s or 4m or 5h)."

        with self.assertRaises(UtilsException) as err:
            datetime.to_seconds('4')

        self.assertIn(expected_error_msg, err.exception.message)
