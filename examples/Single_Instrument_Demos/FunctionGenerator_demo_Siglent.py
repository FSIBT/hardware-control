#!/usr/bin/env python3
"""Siglent Wave Generator demo

Usage:
  FunctionGenerator_demo_Siglent.py [--conn_addr=CONN_ADD] [--dummy] [--debug] [--console] [--info]

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

        self.setWindowTitle("Wave Gen Demo")

        self.main_widget = QWidget(self)

        self.app.add_instrument(hc.instruments.Siglent_SDG("Siglent", conn_addr))
        self.ctrl = hc.gui.FunctionGenerator(
            self.app,
            "Siglent",
            num_channels=2,
            freq_unit="Hz",
        )

        self.grid = QGridLayout()
        self.grid.addWidget(self.ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_widget = Demo(dummy=dummy)
    sys.exit(main_widget.app.exec_())
