#!/usr/bin/env python3
"""Keysight Power Supply demo

Usage:
  KeysightPowerSupply_demo.py [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console

"""

import logging
import sys
from os import getcwd

from docopt import docopt

from PyQt5.QtWidgets import QWidget, QGridLayout
from PyQt5.QtGui import QDoubleValidator

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("Adam 6024 Demo")

        self.main_widget = QWidget(self)

        # Add an Adam 6024 to the app
        self.app.add_instrument(hc.instruments.Adam_6024("ADAM_6024", "192.168.0.5"))
        self.adam_ctrl = hc.gui.Adam6024Control(self.app, "ADAM_6024")

        self.grid = QGridLayout()
        self.grid.addWidget(self.adam_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
