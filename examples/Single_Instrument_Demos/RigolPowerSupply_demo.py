#!/usr/bin/env python3
"""Rigol Power Supply demo

Usage:
  RigolPowerSupply_demo.py [--conn_addr=CONN_ADD] [--dummy] [--debug] [--console] [--info]

Options:
  --conn_addr=CONN_ADD  Connection address of first physical instrument [default: None].
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

        self.setWindowTitle("Rigol Power Supply Demo")

        # This is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # Create Rigol_DP832 instrument backend and add it to the app
        self.app.add_instrument(hc.instruments.Rigol_DP832("rigol", conn_addr))

        # Create a MultiPowerSupply control that connects to the instrument backend
        self.rigol_ctrl = hc.gui.MultiPowerSupply(
            self.app,
            "rigol",
            [1, 2, 3],
            "Rigol DP832 Power Supply Unit",
            show_VI_limits=True,
            enable_power_buttons="both",
        )

        # Add the control to the main widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.rigol_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
