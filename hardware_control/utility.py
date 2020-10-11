def convertibleToFloat(input: str) -> bool:
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


def remove_end_carriage_return(text: str) -> str:
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
