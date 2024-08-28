##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module is for functions related with dates and times."""

import time

from backup.exceptions import ExceptionCodes, UtilsException


def truncate_microseconds_from_timestamp(time_stamp_value):
    """
    Remove the microseconds part from the timestamp value.

    :param time_stamp_value: time represented in seconds and microseconds.
    :return: time represented in seconds only.
    :raise UtilsException: if the time_stamp_value is negative or other invalid value.
    """
    if time_stamp_value < 0:
        raise UtilsException(ExceptionCodes.InvalidValue, time_stamp_value)

    try:
        time_stamp_value = float(int(time_stamp_value))
    except (ValueError, TypeError):
        raise UtilsException(ExceptionCodes.InvalidValue, time_stamp_value)

    return time_stamp_value


def get_formatted_timestamp():
    """
    Get formatted local date and time, based on seconds since the epoch(1st Jan 1970).

    :return: formatted local date and time, in the format YY-MM-DD HH:MM:SS.
    """
    return format_time(truncate_microseconds_from_timestamp(time.time()), '%Y-%m-%d %H:%M:%S')


def format_time(elapsed_time, time_format="%H:%M:%S"):
    """
    Display a float time according to the format string.

    :param elapsed_time: float time representation.
    :param time_format: format string.
    :return: formatted time.
    """
    return time.strftime(time_format, time.gmtime(elapsed_time))


def to_seconds(duration):
    """
    Convert time string to second, where string is of form 3h, 5m, 20s etc.

    :param duration: str with numeric value suffixed with h, s, or m.
    :return: seconds represented by the duration as int type.
    :raise UtilsException: if the string cannot be parsed.
    """
    try:
        units = {"s": 1, "m": 60, "h": 3600}
        return int(float(duration[:-1]) * units[duration[-1]])

    except KeyError:
        raise UtilsException(ExceptionCodes.InvalidTimeUnit, duration)
    except (ValueError, NameError):
        raise UtilsException(ExceptionCodes.InvalidTimeFormat, duration)
