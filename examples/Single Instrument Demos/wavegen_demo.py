#!/usr/bin/env python3
"""wavegen demo

Usage:
  wavegen_demo [--dummy] [--socket]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
"""

import sys

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout
from docopt import docopt

import hardware_control.backends as hc_back
import hardware_control.gui as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]
if commands["--socket"]:
    connection_type = "socket"
    address = "192.168.0.15"
else:
    connection_type = "visa"
    address = "USB0::0x0957::0x2907::MY52500624::INSTR"


class WavegenDemo(QMainWindow):
    def __init__(self, app, connection_type: str):
        super().__init__()
        self.app = app

        self.setWindowTitle("Wave Gen Demo")

        self.main_widget = QWidget(self)

        awg = hc_back.Keysight_33500B(address)

        self.awg_ctrl = hc.FunctionGenerator(awg, self, "RF Generator")

        self.grid = QGridLayout()
        self.grid.addWidget(self.awg_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.awg_ctrl.close()


def main():
    app = hc.App(dummy=dummy)
    ex = WavegenDemo(app, connection_type)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
