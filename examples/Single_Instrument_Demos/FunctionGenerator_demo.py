#!/usr/bin/env python3
"""Function Generator demo

Usage:
  FunctionGenerator_demo.py [--conn_addr=CONN_ADD] [--dummy] [--debug] [--console] [--info]

Options:
  --conn_addr=CONN_ADD  Connection address of physical instrument [default: None].
                        Required if not in dummy mode.
  --dummy               Use dummy connection for instruments that return semi-random data
                        so that one can run the program away from the test stand.
  --debug               Allow debug print statements.
  --info                Allow info print statements.
  --console             Print logger output to console.
"""

import logging
import sys

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout
from docopt import docopt

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]
conn_addr = commands["--conn_addr"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("Keysight 33500B Wave Generator Demo")

        # This is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # Create an Keysight_33500B instrument backend and add it to the app
        # One must specify the number of channels for this instrument
        self.app.add_instrument(
            hc.instruments.Keysight_33500B("keysight", conn_addr, number_of_channels=2)
        )

        # Create a FunctionGenerator GUI control that connects to the instrument backend
        # One must specify the number of channels for this control
        self.awg_ctrl = hc.gui.FunctionGenerator(self.app, "keysight", num_channels=2)

        # Add the control to the main widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.awg_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_widget = Demo(dummy=dummy)
    sys.exit(main_widget.app.exec_())
