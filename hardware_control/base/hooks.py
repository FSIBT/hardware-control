"""Functions that can be used in hooks for instrument parameter and commands.

A hook function takes a single argument, the `value`, and returns the
`modified value` or `None`. If `None` is returned no further hooks (if
they exist) will be executed.

To create a hook function that depends on other variables, you can
create a function that returns another function (similar to
decorators), e.g.

Example
-------
>>> def create_hook(arg):
...     def hook(value):
...         return value + arg
...     return hook


"""

import logging
from typing import Optional, List, Dict, Callable

logger = logging.getLogger(__name__)

# Converters
def create_converter(lookuptable: Dict) -> Callable:
    """Replaces the parameter value with one stored in a dictionary.

    The dictionary consists of "old value":"new value" pairs.
    """

    def converter(value: str):
        if value not in lookuptable:
            logger.error(f"Value '{value}'' not in lookuptable '{lookuptable}'")
            return None
        return lookuptable[value]

    return converter


def max_len_converter(max_length: int) -> Callable:
    """Ensure that a string is not longer than `max_length`"""

    def converter(value):
        if len(value) > max_length:
            return value[0:max_length]
        else:
            return value

    return converter


def last_n_values_converter(num_of_values: int) -> Callable:
    """Assumes `value` is a list and only return the last `num_of_values` entries."""

    def converter(value):
        # TODO: should do some type checking here and error logging
        n = len(value)
        if n > num_of_values:
            return value[-num_of_values:]
        return value

    return converter


def substring_hook(min_char, max_char):
    """Return a substring `value[min_char:max_char]`."""

    def converter(value):
        value = value[min_char:max_char]
        return value

    return converter


def scaling_converter(scale_val):
    """Convert `value` to float and scale by `scale_val`."""

    def converter(value):
        return str(float(value) * scale_val)

    return converter


def format_float(format_type=".17"):
    """Convert value to float and format using any f-string format."""

    def converter(value):
        return f"{float(value):{format_type}}"

    return converter


def format_int(value):
    """Convert value to int."""
    return f"{int(float(value))}"


def format_bool(value):
    """Convert True/False string to 1/0"""
    return str(int(value == "True"))


def make_negative(value):
    """Convert to float and multiple by -1."""
    return f"{-1*float(value)}"


def uppercase(value):
    """Convert to uppercase."""
    return value.upper()


# Validators
def range_validator(min_val: float, max_val: float):
    """Ensure `value` is in a certain numerical range.

    If the value is outside of the range, the value gets replaces by the min/max value.
    """

    def validator(value):
        value = float(value)
        return max(min(value, max_val), min_val)

    return validator


def expected_input_validator(types: List, default_val=None):
    """Ensures `value` is in a certain list, returns a default if this is not the case."""

    def validator(value):
        if value not in types and default_val != None:
            logger.info(
                f"Unfamiliar with input '{value}'. Using '{default_val}' instead."
            )
            return default_val
        elif value not in types:
            logger.error(f"Input value of '{value}' is invalid.")
            return
        else:
            return value

    return validator
