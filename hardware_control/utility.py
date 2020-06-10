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


def change_units(x: float, base_unit: str, decimals: int = 3):

    if x < 1e-9:
        return f"{round(x*1e12, decimals)} p{base_unit}"
    if x < 1e-6:
        return f"{round(x*1e9, decimals)} n{base_unit}"
    if x < 1e-3:
        return f"{round(x*1e6, decimals)} µ{base_unit}"
    if x < 1:
        return f"{round(x*1e3, decimals)} m{base_unit}"
    if x < 1e3:
        return f"{round(x, decimals)} {base_unit}"
    if x < 1e6:
        return f"{round(x*1e-3, decimals)} k{base_unit}"
    if x < 1e9:
        return f"{round(x*1e-6, decimals)} M{base_unit}"
    if x < 1e12:
        return f"{round(x*1e-9, decimals)} G{base_unit}"


def apply_to_label(label, value, units: str = ""):

    if value is not None:
        try:
            label.setText(change_units(float(value), units))
        except:
            label.setText(f"----- {units}")
    else:
        label.setText(f"----- {units}")


def converter_ulong_to_IEEE754(x):
    a = (ctypes.c_ulong * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_float))
    return b.contents.value


def converter_IEEE754_to_ulong(x):
    a = (ctypes.c_float * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_ulong))
    return b.contents.value
