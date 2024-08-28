##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module is for adding any utilities related to the network."""

import socket


def is_valid_ip(ip_address):
    """
    Validate if provided IP address is valid.

    :param ip_address: IP in string format to be validated.
    :return: true if ip is valid; false, otherwise.
    """
    try:
        socket.inet_aton(ip_address)
    except socket.error:
        return False
    return True
