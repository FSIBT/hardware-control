#!/usr/bin/env python3
"""PSU demo

Usage:
  psu_demo [--dummy]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand

"""

import sys

from docopt import docopt

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout

import hardware_control.backends as hc_back
import hardware_control.gui as hc


commands = docopt(__doc__)
dummy = commands["--dummy"]


class PSUDemo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.setWindowTitle("PSU Demo")

        self.main_widget = QWidget(self)

        psu = hc_back.Caen_14xxET("TCPIP::192.168.1.20::1470::SOCKET")
        self.psu_ctrl = hc.MultiPowerSupply(
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
    app = hc.App(dummy=dummy)
    ex = PSUDemo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
