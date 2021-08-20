def create_converter(lookuptable):
    def converter(value):
        return lookuptable[value]

    return converter


def range_validator(min, max):
    def validator(value):
        return max(min(value, max), min)
