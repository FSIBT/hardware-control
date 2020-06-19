import re
import ctypes


def regex_compare(pattern: str, comp: str):
    """Compares 'comp' to the pattern 'pattern'. periods ('.') act as a wildcard in the regular expression.
    Returns true if 'comp' matches the regex."""
    regex = re.compile(pattern)
    return bool(re.match(regex, comp))


def returnChannelNumber(s: str):
    """Return channel number for a string like 'CH###_TEMP' """
    if s[:2] == "CH":
        number = s[2 : s.find("_")]
        if number.isdigit():
            return number
    else:
        return None


def remove_end_carriage_return(text: str):
    try:
        if text.endswith(r"\r"):
            return text[:-2]
        else:
            return text
    except:
        return text


def convertibleToFloat(input: str):
    """ Checks if a string can be converted to a float and returns T/F """

    try:
        float(input)
        return True
    except:
        return False


# These functions are helpful for converting numbers to
# specific number formats for strings


def to_NR3(x: float):
    return f" {x:.6E}"


def str_NR3(x: str):
    x_float = float(x)
    return f" {x_float:.6E}"


def to_NR1(x: int):
    return f"{x:d}"


def bool_NR1(x: bool):
    if x:
        return "1"
    else:
        return "0"


def str_NR1(x: str):
    x_int = int(x)
    return f"{x_int:d}"


def boolstr_NR1(x: str):
    if x == "True":
        return "1"
    else:
        return "0"


def str_to_bool(x: str):
    if x == "True":
        return True
    else:
        return False


def ensure_float(x):
    try:
        return float(x)
    except ValueError:
        return "Invalid value"


def change_units(x: float, base_unit: str, decimals: int = 3, min_width: int = -1):

    if abs(x) < 1e-9:
        rval = f"{round(x*1e12, decimals)} p{base_unit}"
    elif abs(x) < 1e-6:
        rval = f"{round(x*1e9, decimals)} n{base_unit}"
    elif abs(x) < 1e-3:
        rval = f"{round(x*1e6, decimals)} µ{base_unit}"
    elif abs(x) < 1:
        rval = f"{round(x*1e3, decimals)} m{base_unit}"
    elif abs(x) < 1e3:
        rval = f"{round(x, decimals)} {base_unit}"
    elif abs(x) < 1e6:
        rval = f"{round(x*1e-3, decimals)} k{base_unit}"
    elif abs(x) < 1e9:
        rval = f"{round(x*1e-6, decimals)} M{base_unit}"
    elif abs(x) < 1e12:
        rval = f"{round(x*1e-9, decimals)} G{base_unit}"

    if min_width >= 1:
        rval = rval.rjust(min_width)

    return rval


def apply_to_label(
    label, value, units: str = "", decimals: int = 3, min_width: int = -1
):

    if value is not None:
        try:
            new_str = change_units(
                float(value), units, decimals=decimals, min_width=min_width - 3
            )
        except Exception as e:
            new_str = f"----- {units}"
    else:
        new_str = f"----- {units}"

    if min_width != -1:
        new_str.rjust(min_width)

    label.setText(new_str)


def converter_ulong_to_IEEE754(x):
    a = (ctypes.c_ulong * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_float))
    return b.contents.value


def converter_IEEE754_to_ulong(x):
    a = (ctypes.c_float * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_ulong))
    return b.contents.value
