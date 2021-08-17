import logging
import sys


def setup_logging(logger, commands, logfile_name=None):
    """Setup the loglevel and direct to console or file.

    Parameters
    ----------
    logger :
        A logger needs to be defined in the main instance, e.g. using
        logging.getLogger(__name__)
    commands : dict
        A dictionary (e.g. from docopt). The following keys need to have
        a boolean value set: "--info", "--debug", "--console". The first two
        control the debug level and the last one either logs to the console or
        to a file (in which case a `logfile_name` needs to be defined
    logfile_name : str
        A filename that will be used by the logger
    """

    if commands["--debug"]:
        loglevel = logging.DEBUG
        loglevelname = "Debug"
    elif commands["--info"]:
        loglevel = logging.INFO
        loglevelname = "Info"
    else:
        loglevel = logging.WARNING
        loglevelname = "Warning"

    # Create file or stream handler
    format_str = "[%(asctime)s] %(name)s - %(levelname)s: %(message)s"
    if commands["--console"]:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(format_str))
        handler.setLevel(loglevel)
        print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: Console")
    else:
        if logfile_name is None:
            print("Error: No logfilename defined")
            sys.exit()
        handler = logging.FileHandler(logfile_name)
        handler.setFormatter(logging.Formatter(format_str))
        handler.setLevel(loglevel)
        print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: File")

    # Clear all other handlers
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
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
