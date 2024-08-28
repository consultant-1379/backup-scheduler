##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""The purpose of this module is to provide unit testing for utils.datatypes.py script."""

import unittest

import backup.utils.datatypes as dtypes


class UtilsDataTypesTestCase(unittest.TestCase):
    """Test Cases for find_elem_dic function in utils.datatypes.py script."""

    def setUp(self):
        """Create testing scenario."""
        self.backup_tag = "2018-08-24"
        self.customer_backup_dic = \
            {
                'CUSTOMER_0':
                    [
                        '/home/username/Documents/mock/rpc_bkps/CUSTOMER_0/2018-08-25',
                        '/home/username/Documents/mock/rpc_bkps/CUSTOMER_0/2018-08-24',
                        '/home/username/Documents/mock/rpc_bkps/CUSTOMER_0/2018-08-23'
                    ]
            }
        self.item = 'CUSTOMER_0', '/home/username/Documents/mock/rpc_bkps/CUSTOMER_0/2018-08-24'

    def test_find_elem_dic_existent_element(self):
        """Test find existent element in dictionary."""
        key, item = dtypes.find_elem_dict(self.customer_backup_dic, self.backup_tag)
        self.assertTupleEqual((key, item), self.item)

    def test_find_elem_dic_non_existent_element(self):
        """Test find non-existent element in dictionary."""
        non_existent_backup_tag = "2019-08-26"
        key, item = dtypes.find_elem_dict(self.customer_backup_dic, non_existent_backup_tag)
        self.assertTupleEqual((key, item), ('', ''))

    def test_find_elem_dic_empty_query(self):
        """Test find element in dictionary with empty query."""
        empty_query = ""
        key, item = dtypes.find_elem_dict(self.customer_backup_dic, empty_query)
        self.assertTupleEqual((key, item), ('', ''))

    def test_find_elem_dic_empty_dictionary(self):
        """Test find element in empty dictionary."""
        empty_dictionary = ""
        with self.assertRaises(AttributeError):
            dtypes.find_elem_dict(empty_dictionary, self.backup_tag)
