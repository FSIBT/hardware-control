#!/usr/bin/env python3
"""wavegen demo

Usage:
  wavegen_demo [--dummy] [--socket] [--debug] [--console] [--info]

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

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout
from docopt import docopt

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


if commands["--socket"]:
    address = "192.168.0.20"
else:
    address = "TCPIP0::192.168.2.12::INSTR"


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("Wave Gen Demo")

        self.main_widget = QWidget(self)

        self.app.add_instrument(hc.instruments.Siglent_SDG("Siglent", address))
        self.awg_ctrl = hc.gui.FunctionGenerator(self.app, "Siglent", num_channels=2)

        self.grid = QGridLayout()
        self.grid.addWidget(self.awg_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_widget = Demo(dummy=dummy)
    sys.exit(main_widget.app.exec_())
