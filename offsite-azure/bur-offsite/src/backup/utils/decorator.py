##############################################################################
# COPYRIGHT Ericsson 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson Inc. The programs may be used and/or copied only with written
# permission from Ericsson Inc. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

"""Module is for adding any custom decorators."""

from enum import Enum
import new
from threading import Timer
import time

from backup.performance import BURPerformance

DECORATOR_KEYS = Enum('DECORATOR_KEYS', 'get_elapsed_time, max_delay, on_timeout, on_timeout_args')


def timeit(method):
    """
    Calculate the elapsed time to execute a function. Decorator function.

    :param method: annotated method.
    """
    def wrapper(*args, **kw):
        """Calculate the elapsed time to execute the method."""
        time_start = time.time()
        result = method(*args, **kw)
        time_end = time.time()

        if DECORATOR_KEYS.get_elapsed_time.name in kw:
            if isinstance(kw[DECORATOR_KEYS.get_elapsed_time.name], list):
                kw[DECORATOR_KEYS.get_elapsed_time.name].append(time_end - time_start)
        return result

    wrapper.__wrapped__ = method
    return wrapper


def collect_performance_data(method):
    """
    Collect performance data after executing a backup operation. Decorator function.

    :param method: decorated method.
    :return: tuple (bur_id, backup_output, total_time time).
    """
    def wrapper(*args, **kw):
        """Get the return of the method and generate performance reports."""
        bur_id, backup_output_dic, total_time = method(*args, **kw)

        BURPerformance(bur_id, backup_output_dic, total_time).update_csv_reports()

        return bur_id, backup_output_dic, total_time

    wrapper.__wrapped__ = method

    return wrapper


def timer_delay(method):
    """
    Execute a function after the specified timeout. Decorator function.

    :param method: decorated method.
    """
    def wrapper(*args, **kw):
        """Execute a function after timeout."""
        max_delay = None
        if DECORATOR_KEYS.max_delay.name in kw:
            max_delay = kw[DECORATOR_KEYS.max_delay.name]

        on_timeout_function = None
        if DECORATOR_KEYS.on_timeout.name in kw and callable(kw[DECORATOR_KEYS.on_timeout.name]):
            on_timeout_function = kw[DECORATOR_KEYS.on_timeout.name]

        on_timeout_function_args = []
        if DECORATOR_KEYS.on_timeout_args.name in kw and \
                isinstance(kw[DECORATOR_KEYS.on_timeout_args.name], list):
            on_timeout_function_args = kw[DECORATOR_KEYS.on_timeout_args.name]

        if on_timeout_function is None or max_delay is None:
            return method(*args, **kw)

        try:
            timer = Timer(float(max_delay), on_timeout_function, on_timeout_function_args)
            timer.start()

            return method(*args, **kw)

        finally:
            if timer.is_alive():
                timer.cancel()

    wrapper.__wrapped__ = method

    return wrapper


def get_undecorated_class_method(decorated_function, original_instance=None):
    """
    Retrieve original function from a decorated function.

    :param decorated_function: decorated function.
    :param original_instance: original instance to which the function was attached.
    :return: original function after stripping the decorator or None in case of invalid input.
    """
    if not decorated_function or not callable(decorated_function):
        return None

    attached_class_name = None
    if original_instance:
        attached_class_name = original_instance.__class__.__name__

    # new module is deprecated in Python 3.0. For upgrading, use the equivalent types.MethodType.
    instance_method = new.instancemethod(decorated_function.__wrapped__, original_instance,
                                         attached_class_name)

    return instance_method
