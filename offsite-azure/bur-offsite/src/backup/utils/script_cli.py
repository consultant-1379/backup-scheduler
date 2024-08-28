##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module is for adding any utilities related to the general command line purpose."""

import sys


def get_cli_arguments():
    """
    Return passed BUR arguments through CLI in a list, after filtering arguments ending with '.py'.

    :return a filtered list of CLI arguments, or an empty list if there was no CLI arguments passed.
    """
    provided_args = []

    if sys.argv:
        provided_args = list(sys.argv)

        for cli_argument in provided_args:

            if cli_argument.endswith(".py"):
                provided_args.remove(cli_argument)

    return provided_args
