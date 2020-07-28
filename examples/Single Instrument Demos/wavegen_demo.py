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

from hardware_control.base import HC_App
from hardware_control.FunctionGenerator import HC_FunctionGenerator, Key33500BCtrl

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

        awg = Key33500BCtrl(address)

        self.awg_ctrl = HC_FunctionGenerator(awg, self, "RF Generator")

        self.grid = QGridLayout()
        self.grid.addWidget(self.awg_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.awg_ctrl.close()


def main():
    app = HC_App(dummy=dummy)
    ex = WavegenDemo(app, connection_type)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
