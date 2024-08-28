##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module is for any utilities for validating general inputs."""

from backup.exceptions import ExceptionCodes, UtilsException


def check_not_empty(value):
    """
    Check if the value param is empty or not.

    :param value: input to be validated.
    :return: True if not empty.
    :raise UtilsException: if value param is empty.
    """
    if not value:
        raise UtilsException(ExceptionCodes.EmptyValue)

    if isinstance(value, str):
        if not value.strip():
            raise UtilsException(ExceptionCodes.EmptyValue)

    return True
