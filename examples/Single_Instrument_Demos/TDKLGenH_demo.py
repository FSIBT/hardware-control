#!/usr/bin/env python3
"""TDKL Power Supply demo

Usage:
  TDKLGenH_demo.py [--conn_addr=CONN_ADD] [--dummy] [--debug] [--console] [--info]

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

from docopt import docopt

from PyQt5.QtWidgets import QWidget, QGridLayout

import hardware_control as hc


commands = docopt(__doc__)
dummy = commands["--dummy"]
conn_addr = commands["--conn_addr"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("TDKL Power Supply Demo")

        # This is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # Create a TDKL_GenH instrument backend and add it to the app
        self.app.add_instrument(hc.instruments.TDKL_GenH("tdkl", conn_addr))

        # Create a MultiPowerSupply control that connects to the nstrument backend
        self.tdkl_ctrl = hc.gui.MultiPowerSupply(
            self.app,
            "tdkl",
            [1],
            "TDKL Power Supply Unit",
            enable_power_buttons="both",
        )

        # Add the three control and the console to the main widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.tdkl_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
