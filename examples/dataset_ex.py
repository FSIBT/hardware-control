#!/usr/bin/env python3
"""oscilloscope_example to control the hardware_control test stand

Usage:
  sts50_example [--dummy] [--socket] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""

import logging

import sys
import warnings
from docopt import docopt

from hardware_control.base import HC_App, HC_MainWindow, Dataset


commands = docopt(__doc__)
dummy = commands["--dummy"]
info = commands["--info"]
if commands["--socket"]:
    connection_type = "socket"
else:
    connection_type = "visa"
debug = commands["--debug"]
print_console = commands["--console"]

logfile_name = "hardware_control.log"

if debug:
    if print_console:
        logging.basicConfig(level=logging.DEBUG)
        print("Logger configured:\n\tLevel: Debug\n\tOutput: Console")
    else:
        logging.basicConfig(filename=logfile_name, level=logging.DEBUG)
        print(f"Logger configured:\n\tLevel: Debug\n\tOutput: {logfile_name}")
elif info:
    if print_console:
        logging.basicConfig(level=logging.INFO)
        print("Logger configured:\n\tLevel: Info\n\tOutput: Console")
    else:
        logging.basicConfig(filename=logfile_name, level=logging.INFO)
        print(f"Logger configured:\n\tLevel: Info\n\tOutput: {logfile_name}")
else:
    if print_console:
        logging.basicConfig(level=logging.WARNING)
        print("Logger configured:\n\tLevel: Warning\n\tOutput: Console")
    else:
        logging.basicConfig(filename=logfile_name, level=logging.WARNING)
        print(f"Logger configured:\n\tLevel: Warning\n\tOutput: {logfile_name}")


logger = logging.getLogger(__name__)
logger.info("STS50 Example Starting")


class DatasetDemo(HC_MainWindow):
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        self.ds1 = Dataset("DS1")
        self.ds9 = Dataset("DS9")

        self.ds9.start_asynch(3, True)
        self.ds9.start_autosave(10, "TXT", "DS9_data.txt")

        self.show()


def main():
    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning
    )  # ToDo Not a solution
    app = HC_App(dummy=dummy)

    if dummy:
        dummy_set = Dataset("Dummy")
        app.data_sets["Dummy"] = dummy_set
        app.data_sets["Dummy"].data["t"] = [1, 2, 3, 4, 5]
        app.data_sets["Dummy"].data["CH1 Vpp"] = [1, 1.5, 2, 2.5, 3]
        app.data_sets["Dummy"].data["CH2 Vpp"] = [-1, -2, -3, -3, -3]

    ex = DatasetDemo(app)
    sys.exit(app.exec_())


main()
