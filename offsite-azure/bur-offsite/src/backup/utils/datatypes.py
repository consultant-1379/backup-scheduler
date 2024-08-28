##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module is for working with data types in python."""

from backup.exceptions import ExceptionCodes, UtilsException


def get_elem_dict(dic, key):
    """
    Find and get element from dictionary.

    :param dic: dictionary.
    :param key: key to the value.
    :return: value referred by the key, if exists, None otherwise.
    """
    if not isinstance(dic, dict):
        return None

    if key in dic.keys():
        return dic[key]

    return None


def find_elem_dict(dic, query):
    """
    Find element in a map of arrays.

    :param dic: map object.
    :param query: query string.
    :return: tuple (key, item) that was found, tuple ("", "") otherwise.
    """
    if not str(query).strip():
        return "", ""

    for key, _ in dic.items():
        for item in dic[key]:
            if query in str(item):
                return key, item
    return "", ""


def get_values_from_dict(dictionary, key=""):
    """
    Get values from dictionary based on the passed key.

    If no key is specified, get all values from the dictionary regardless the key.

    :param dictionary: dictionary with key value pairs.
    :param key: dictionary's key.
    :return: list with the result of the search.
    :raise UtilsException: if there is no element found in the dict param related to the key param.
    """
    if key is None or not key.strip():
        return dictionary.values()

    element = get_elem_dict(dictionary, key)
    if element is None:
        raise UtilsException(ExceptionCodes.ElementNotFound, [dictionary, key])

    return [element]
