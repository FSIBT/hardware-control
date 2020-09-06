#!/usr/bin/env python3
"""oscilloscope_example to control the hardware_control test stand

Usage:
  oscilloscope_example [--dummy]
  oscilloscope_example [--socket]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
"""

import sys

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
if commands["--socket"]:
    connection_type = "socket"
    address = "192.168.0.14"

else:
    connection_type = "visa"
    address = "TCPIP0::192.168.0.14::INSTR"

import hardware_control.backends as hc_back
import hardware_control.gui as hc


class ScopeWindow(QMainWindow):
    def __init__(self, app, connection_type: str):
        super().__init__()
        self.app = app

        self.setWindowTitle("Oscilloscope Demo")

        self.main_widget = QWidget(self)

        scpi_scope = hc_back.Keysight_4000X(address)
        self.scope_ctrl = hc.Oscilloscope(app, scpi_scope, "Oscilloscope Control")

        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.scope_ctrl.close()


def main():
    app = hc.App(dummy=dummy)
    ex = ScopeWindow(app, connection_type)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
