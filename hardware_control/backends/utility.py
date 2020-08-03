import ctypes
import re


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


def get_channel_from_command(command: str):
    """Processes a command from the front end.

    Returns
    -------
    returns a tuple with:
        1.) channel number
        2.) original command with all channel numbers replaced by a single 'X'
    If the channel is not specified, the channel number is returned as 'None'
    and the original command is returned without any replacements.

    The channel is specified by writing CH#_
    """

    # Check command length
    if len(command) < 3:
        return None, command

    # Check 'CH' specifier comes first
    if command[:2] != "CH":
        return None, command

    # Find end of channel number
    idx_underscore = command.find("_")
    if idx_underscore == -1:
        return None, command

    # Get channel number
    try:
        chan = int(command[2:idx_underscore])
    except ValueError:
        chan = command[2:idx_underscore]

    # overwrite channel number for easier comparison
    command_X = command[:2] + "X" + command[idx_underscore:]

    return chan, command_X


def remove_end_carriage_return(text: str):
    try:
        if text.endswith(r"\r"):
            return text[:-2]
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


def ensure_float(x):
    try:
        return float(x)
    except ValueError:
        return "Invalid value"


def converter_ulong_to_IEEE754(x):
    a = (ctypes.c_ulong * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_float))
    return b.contents.value


def converter_IEEE754_to_ulong(x):
    a = (ctypes.c_float * 1)(x)
    b = ctypes.cast(a, ctypes.POINTER(ctypes.c_ulong))
    return b.contents.value
