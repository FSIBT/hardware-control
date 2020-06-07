#!/usr/bin/env python3
"""PSU demo

Usage:
  psu_demo [--dummy] [--socket] [--debug]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
"""

import sys

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
debug = commands["--debug"]

from hardware_control.base import HC_App
from hardware_control.PowerSupply.CAEN14xxETCtrl import CAEN14xxETCtrl
from hardware_control.PowerSupply.HC_MultiPowerSupply import HC_MultiPowerSupply


class PSUDemo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.setWindowTitle("PSU Demo")

        self.main_widget = QWidget(self)

        # psu = TDKLGenHCtrl("TCPIP0::192.168.1.19::INSTR", dummy)
        # self.psu_ctrl = HC_MultiPowerSupply(
        #     psu, self, [1], "Power Supply Unit", "DEFAULT"
        # )

        psu = CAEN14xxETCtrl("TCPIP::192.168.1.20::1470::SOCKET", dummy)
        self.psu_ctrl = HC_MultiPowerSupply(
            psu, self, [1, 2, 3], "Power Supply Unit", "DEFAULT"
        )

        self.grid = QGridLayout()
        self.grid.addWidget(self.psu_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.psu_ctrl.close()


def main():
    app = HC_App(dummy=dummy)
    ex = PSUDemo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
