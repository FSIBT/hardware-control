#!/usr/bin/env python3
"""PSU demo

Usage:
  psu_demo [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console

"""

import logging
import sys

from docopt import docopt

from PyQt5.QtWidgets import QWidget, QGridLayout

import hardware_control as hc


commands = docopt(__doc__)
dummy = commands["--dummy"]

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

logger = logging.getLogger(__name__)
hc.setup_logging(logger, logoutput, loglevel)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("PSU Demo")

        self.main_widget = QWidget(self)

        self.app.add_instrument(hc.instruments.Caen_14xxET("caen", "192.168.1.20:1470"))

        self.psu_ctrl = hc.gui.MultiPowerSupply(
            self.app, "caen", "Caen", [1, 2, 3], "Power Supply Unit", "DEFAULT"
        )

        self.grid = QGridLayout()
        self.grid.addWidget(self.psu_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
