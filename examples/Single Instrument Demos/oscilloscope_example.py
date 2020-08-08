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

from docopt import docopt

from PyQt5.QtWidgets import QGridLayout, QWidget


import hardware_control.backends as hc_back
import hardware_control.gui as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]
info = commands["--info"]
if commands["--socket"]:
    scope_address = "192.168.0.14:5025"
else:
    scope_address = "TCPIP0::192.168.0.14::INSTR"
debug = commands["--debug"]
print_console = commands["--console"]

logfile_name = "hardware_control.log"

if debug:
    log_level = logging.DEBUG
elif info:
    log_level = logging.INFO
else:
    log_level = logging.WARNING

if print_console:
    logging.basicConfig(level=log_level)
    print("Logger configured:\n\tLevel: Debug\n\tOutput: Console")
else:
    logging.basicConfig(filename=logfile_name, level=log_level)
    print(f"Logger configured:\n\tLevel: Debug\n\tOutput: {logfile_name}")


logger = logging.getLogger(__name__)
logger.info("Scope Example Starting")


class ScopeDemo(hc.MainWindow):
    def __init__(self, app):
        super().__init__(app)

        self.setWindowTitle("Oscilloscope Demo")

        self.main_widget = QWidget(self)

        scpi_scope = hc_back.Keysight_4000X(scope_address)
        self.scope_ctrl = hc.Oscilloscope(app, scpi_scope, "Keysight")

        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.scope_ctrl.close()


def main():
    app = hc.App(dummy=dummy)
    ex = ScopeDemo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
