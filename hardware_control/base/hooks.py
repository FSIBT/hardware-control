from typing import Optional, List

# Converters
def create_converter(lookuptable):
    def converter(value):
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


def floater(type):
    if type == "6E":

        def converter(value):
            return f"{float(value):.6E}"

    return converter


def uppercase():
    def converter(value):
        return value.upper()

    return converter


# Validators
def range_validator(min, max):
    def validator(value):
        value = float(value)
        return max(min(value, max), min)

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


# Other post_hook functions
def create_return_value(setting, unit: Optional[str] = None):
    def return_value(value):
        if unit == None:
            return f"{setting}={value}"
        else:
            return f"{setting}={value} {unit}"

    return return_value
