##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""The purpose of this module is to provide unit testing for utils.decorator.py script."""

import time
import unittest

import mock

from backup.utils.decorator import timeit, timer_delay

MOCK_PACKAGE = 'backup.utils.decorator.'

TIME_SLEEP = 1


@timer_delay
@timeit
def dummy_method(good_input=True, **kwargs):
    """Fake the use of decorators."""
    if good_input:
        time.sleep(TIME_SLEEP)
        return True

    raise Exception("Dummy Exception!")


class UtilsTimeitDecoratorTestCase(unittest.TestCase):
    """Test Cases for timeit decorator located in decorator.py."""

    def setUp(self):
        """Set up test constants."""
        self.elapsed_time_array = []
        self.elapsed_time = 1

    def test_timeit_time_decorated_method_accordingly(self):
        """Test if decorated method is timed accordingly."""
        dummy_method(get_elapsed_time=self.elapsed_time_array)

        self.assertNotEqual(self.elapsed_time_array, [])

        self.assertGreaterEqual(self.elapsed_time_array[0], TIME_SLEEP)

    def test_timeit_measurement_done_twice(self):
        """Test if time measurement is done twice in decorated method."""
        with mock.patch(MOCK_PACKAGE + 'time.time') as mock_time:
            dummy_method(get_elapsed_time=self.elapsed_time_array)

        self.assertEqual(2, mock_time.call_count)

    def test_timeit_output_of_decorated_method_is_the_one_expected(self):
        """Test if output of decorated method is the one expected."""
        self.assertTrue(dummy_method(get_elapsed_time=self.elapsed_time_array))

    def test_timeit_when_get_elapsed_time_is_not_a_list(self):
        """Test if timeit acts when get_elapsed_time variable is not a list."""
        dummy_method(get_elapsed_time=self.elapsed_time)
        self.assertEqual(1, self.elapsed_time)

    def test_timeit_even_when_exception_is_raised_on_decorated_method(self):
        """Test measurement is done even when exception is raised on decorated method."""
        with self.assertRaises(Exception) as exception:
            dummy_method(good_input=False, get_elapsed_time=self.elapsed_time_array)
            self.assertGreater(self.elapsed_time_array[0], 0)
            self.assertNotEqual(self.elapsed_time_array, [])
            self.assertEqual("Dummy Exception!", exception.exception.message)


class UtilsTimerDelayDecoratorTestCase(unittest.TestCase):
    """Test Cases for timer_delay decorator located in decorator.py."""

    def test_timer_delay_is_starting_timer(self):
        """Testing when all keys are provided and the timer should start."""
        with mock.patch(MOCK_PACKAGE + 'Timer') as mock_timer:
            dummy_method(max_delay=1, on_timeout=mock.Mock(), on_timeout_args=[])
            self.assertEqual(1, mock_timer.return_value.start.call_count)

    def test_timer_delay_is_starting_timer_no_func_arg_provided(self):
        """Testing when just the function argument list is missing, the timer should start."""
        with mock.patch(MOCK_PACKAGE + 'Timer') as mock_timer:
            dummy_method(max_delay=1, on_timeout=mock.Mock())
            self.assertEqual(1, mock_timer.return_value.start.call_count)

    def test_timer_delay_is_not_starting_timer_no_function_provided(self):
        """Testing when no timeout function is provided, the timer should not start."""
        with mock.patch(MOCK_PACKAGE + 'Timer') as mock_timer:
            dummy_method(max_delay=1)
            self.assertEqual(0, mock_timer.return_value.start.call_count)

    def test_timer_delay_is_not_starting_timer_no_delay_provided(self):
        """Testing when no delay value is provided, the timer should not start."""
        with mock.patch(MOCK_PACKAGE + 'Timer') as mock_timer:
            dummy_method(on_timeout=mock.Mock())
            self.assertEqual(0, mock_timer.return_value.start.call_count)

    def test_timer_delay_is_not_starting_timer_no_key_provided(self):
        """Testing when no key is provided, the timer should not start."""
        with mock.patch(MOCK_PACKAGE + 'Timer') as mock_timer:
            dummy_method()
            self.assertEqual(0, mock_timer.return_value.start.call_count)
