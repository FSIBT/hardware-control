import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# Converters
def create_converter(lookuptable):
    def converter(value):
        if value not in lookuptable:
            logger.error(f"Value '{value}'' not in lookuptable '{lookuptable}'")
            return None
        return lookuptable[value]

    return converter


def min_len_converter(min_length):
    def converter(value):
        value = float(value)
        if len(value) > min_length:
            return value[0:min_length]
        else:
            return value

    return converter


def parse_converter(min_char, max_char):
    def converter(value):
        value = value[min_char:max_char]
        return value

    return converter


def scaling_converter(scale_val):
    def converter(value):
        return str(float(value) * scale_val)

    return converter


def format_float(format_type=".17"):
    def converter(value):
        return f"{float(value):{format_type}}"

    return converter


def format_int():
    def converter(value):
        return f"{int(float(value))}"

    return converter


def make_negative():
    def converter(value):
        return f"{-1*(value)}"

    return converter


def uppercase():
    def converter(value):
        return value.upper()

    return converter


# Validators
def range_validator(min_val, max_val):
    def validator(value):
        value = float(value)
        return max(min(value, max_val), min_val)

    return validator


def expected_input_validator(types: List, default_val=None):
    def validator(value):
        if value not in types and default_val != None:
            logger.info(
                f"Unfamiliar with input '{value}'. Using '{deault_val}' instead."
            )
            return default_val
        elif value not in types:
            logger.error(f"Input value of '{value}' is invalid.")
            return
        else:
            return value

    return validator


# Other hooks
def write_to_log(statement: str, log_type: str):
    if log_type == "debug":
        logger.debug(statement)
    elif log_type == "info":
        logger.info(statement)
    elif log_type == "error":
        logger.error(statement)
    elif log_type == "trace":
        logger.trace(statement)
    elif log_type == "warn":
        logger.warn(statement)
    elif log_type == "fatal":
        logger.fatal(statement)
