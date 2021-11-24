"""Functions that can be used in hooks for instrument parameters and commands.

A hook function takes a single argument, the `value`, and returns the
`modified value` or `None`. If `None` is returned no further hooks (if
they exist) will be executed.

To create a hook function that depends on other variables, you can
create a function that returns another function (similar to
decorators), e.g.:

Example
-------
>>> def create_hook(arg):
...     def hook(value):
...         return value + arg
...     return hook


"""

import logging
from typing import Optional, List, Dict, Callable

from PyQt5.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)


def call_hooks(hooks_list: List[Callable], value: str) -> Optional[str]:
    """Call a list of functions.

    If any of the functions returns None, the final value will be
    ignored and no further hooks will be called.

    Every hook function must take a single parameter: the value of the
    parameter to be set (set to None for commands)

    If a hook needs several parameters, one should pass these in when
    defining the hook using lambda functions, e.g.:

    app.add_hook(instrument, parameter, 'pre_set_hooks', lambda x: change_ui(app, x, widget))

    where app and widget are defined in the environment where add_hook
    is called.

    Parameters
    ----------
    hooks_list
       A list of functions or callable objects
    values
       The value to be manipulated
    """
    if value is None or value == "None":
        return None

    for hook in hooks_list:
        if callable(hook):
            value = hook(value)
            if value is None:
                return None
    return str(value)


# Converters
def add_offset(offset):
    """Convert `value` to float and add `offset` to it."""

    def converter(value):
        value = float(value) + float(offset)
        return value

    return converter


def create_converter(lookuptable: Dict) -> Callable:
    """Replaces the parameter value with one stored in a dictionary.

    The dictionary consists of "old value":"new value" pairs.
    """

    def converter(value: str):
        if value not in lookuptable:
            logger.error(f"Value '{value}' not in lookuptable '{lookuptable}'")
            return None
        return lookuptable[value]

    return converter


def format_bool(value):
    """Convert True/False string to 1/0."""
    return str(int(value == "True"))


def format_float(format_type=".17"):
    """Convert value to float and format using any f-string format."""

    def converter(value):
        return f"{float(value):{format_type}}"

    return converter


def format_int(value):
    """Convert value to int."""
    return f"{int(float(value))}"


def last_n_values_converter(num_of_values: int) -> Callable:
    """Assume `value` is a list and only return the last `num_of_values` entries."""

    def converter(value):
        # TODO: should do some type checking here and error logging
        n = len(value)
        if n > num_of_values:
            return value[-num_of_values:]
        return value

    return converter


def make_negative(value):
    """Convert to float and multiple by -1."""
    return f"{-1*float(value)}"


def max_len_converter(max_length: int) -> Callable:
    """Ensure that a string is not longer than `max_length`."""

    def converter(value):
        if len(value) > max_length:
            return value[0:max_length]
        return value

    return converter


def scaling_converter(scale_val):
    """Convert `value` to float and scale by `scale_val`."""

    def converter(value):
        return str(float(value) * scale_val)

    return converter


def substring_hook(min_char, max_char):
    """Return a substring `value[min_char:max_char]`."""

    def converter(value):
        if min_char is None:
            value = value[:max_char]
        elif max_char is None:
            value = value[min_char:]
        else:
            value = value[min_char:max_char]
        return value

    return converter


def uppercase(value):
    """Convert to uppercase."""
    return value.upper()


# Validators
def expected_input_validator(types: List, default_val=None):
    """Ensures `value` is in a specified list, returns a default if this is not the case."""

    def validator(value):
        if (value not in types) and (default_val is not None):
            logger.info(
                f"Unfamiliar with input '{value}'. Using '{default_val}' instead."
            )
            return default_val
        if value not in types:
            logger.error(f"Input value of '{value}' is invalid.")
            return
        return value

    return validator


def range_validator(min_val: float, max_val: float):
    """Ensure `value` is in a specified numerical range.

    If the value is outside of the range, the value gets replaces by the min/max value.
    """

    def validator(value):
        value = float(value)
        return max(min(value, max_val), min_val)

    return validator


class Ramp(QObject):
    """Ramp a setting up and down via a timer.

    This can be useful for, e.g., high voltage power supplies that do
    not support ramping.

    The class can be used as a hook. If there are several hooks, this
    should be the first one, so that the ramp units are all in the
    same units as on the UI, e.g. before any scaling happens.

    Parameters
    ----------
    app
        The main app.
    instrument
        The instrument name
    set_parameter
        The instrument parameter for setting the voltage
    ramp_speed
        The change in the parameter (in UI units) per second.
    read_parameter
        The instrument parameter to reading the current voltage (if empty, then set_parameter will be used)
    timer_step
        The time between steps, in ms. (default 500 ms)
    min_value
        Only scan when we are above this value
    epsilon
        Stop when we are within epsilon of target value

    """

    def __init__(
        self,
        app,
        instrument: str,
        set_parameter: str,
        ramp_speed: int,
        read_parameter: str = "",
        timer_step: int = 500,
        min_value: float = 0,
        epsilon: float = 1e-4,
    ):
        super().__init__()
        self.app = app
        self.instrument = instrument
        self.set_parameter = set_parameter
        self.read_parameter = read_parameter or set_parameter

        self.ramp_speed = ramp_speed
        self.timer_step = timer_step  # in ms
        self.min_value = min_value
        self.epsilon = epsilon

        self.target_value = 0
        self.current_value = 0
        self.next_value = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.do_step)

    def do_step(self):
        """Execute one ramping step.

        Calculated the next value in the ramping cycle and set it via the app.
        """
        delta = self.ramp_speed * (self.timer_step / 1000)

        if self.target_value > self.current_value:
            self.next_value = self.current_value + delta
        else:
            self.next_value = self.current_value - delta

        # no ramping below min_value
        if self.next_value < self.min_value:
            self.next_value = self.min_value

        # if we are close just go directly to the target_value value and stop the timer
        if abs(self.next_value - self.target_value) < self.epsilon + delta:
            self.next_value = self.target_value
            self.timer.stop()

        self.app.set_instrument_parameter(
            self.instrument, self.set_parameter, self.next_value, priority=2
        )
        self.current_value = self.next_value

    def __call__(self, value):
        """This is the function that is used as a hook

        We need to let expected values pass through and start the ramp otherwise.
        """
        value_orig = value
        value = float(value)

        # if we get the next value in the ramp, just pass it through
        # or next value is smaller than the min value
        if (value < self.min_value + self.epsilon) or (
            abs(value - self.next_value) < self.epsilon
        ):
            return value_orig

        # start a new ramp cycle
        self.target_value = value
        self.timer.start(self.timer_step)
        # adjust current value (e.g. if instrument already on when starting the program)
        if abs(self.current_value - value) > self.epsilon:
            read_value = float(
                self.app.get_instrument_parameter(self.instrument, self.read_parameter)
            )
            self.current_value = read_value
