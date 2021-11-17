import logging
from pathlib import Path
import sys
from typing import Optional


def setup_logging(
    logger,
    logoutput: Optional[Path] = None,
    loglevel: Optional[int] = None,
):
    """Set up the log level and direct the logger output to the console or a file.

    Parameters
    ----------
    logger :
        A logger needs to be defined in the main instance, e.g. using
        logging.getLogger(__name__)
    logoutput :
        "console" creates a loghandler that logs to stdout. If a path
        is given, a filehandler is created
    loglevel :
        The log level requested
    """
    if loglevel == logging.DEBUG:
        loglevelname = "Debug"
    elif loglevel == logging.INFO:
        loglevelname = "Info"
    else:
        loglevel = logging.WARNING
        loglevelname = "Warning"

    # Create file or stream handler
    format_str = "[%(asctime)s] %(name)s - %(levelname)s: %(message)s"
    if logoutput:
        handler = logging.FileHandler(logoutput)
        print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: File")
    else:
        handler = logging.StreamHandler(sys.stdout)
        print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: Console")
    handler.setFormatter(logging.Formatter(format_str))
    handler.setLevel(loglevel)

    # Clear all other handlers
    for name in logging.root.manager.loggerDict:

        lgr = logging.getLogger(name)
        lgr.propagate = False

        if "hardware_control" in name:
            lgr.setLevel(loglevel)
            lgr.handlers = []
            lgr.addHandler(handler)
        else:
            lgr.setLevel(logging.CRITICAL)
            lgr.handlers = []

    logger.setLevel(loglevel)
    logger.handlers = []
    logger.addHandler(handler)


def setup_logging_docopt(logger, commands):
    """Set up logging by parsing the output of a docopt dictionary for certain command line options.

    The function recognizes '--debug', '--info', and '--console' to set the log level and the output.
    """
    if commands["--debug"]:
        loglevel = logging.DEBUG
    elif commands["--info"]:
        loglevel = logging.INFO
    else:
        loglevel = logging.WARNING

    if commands["--console"]:
        logoutput = None
    else:
        logoutput = Path("hardware-control.log")

    setup_logging(logger, logoutput, loglevel)
