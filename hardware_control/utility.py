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
        except Exception:
            new_str = f"----- {units}"
    else:
        new_str = f"----- {units}"

    if min_width != -1:
        new_str.rjust(min_width)

    label.setText(new_str)


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


def remove_end_carriage_return(text: str):
    try:
        if text.endswith(r"\r"):
            return text[:-2]
        return text
    except:
        return text


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
