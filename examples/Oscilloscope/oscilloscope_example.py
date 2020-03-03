#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
use_sockets = commands["--socket"]

from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope
from hardware_control.Oscilloscope.Key4000XCtrl import Key4000XCtrl


class ScopeDemo(QMainWindow):
    def __init__(self, app, use_sockets: bool):
        super().__init__()
        self.app = app

        self.setWindowTitle("Oscilloscope Demo")

        self.main_widget = QWidget(self)

        scpi_scope = Key4000XCtrl(
            "TCPIP0::192.168.0.14::INSTR",
            dummy,
            True,
            use_sockets,
            "192.168.0.14",
            5025,
        )
        self.scope_ctrl = HC_Oscilloscope(scpi_scope, "DEFAULT", True)

        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.scope_ctrl.close()


def main(argv):
    app = QApplication([])
    ex = ScopeDemo(app, use_sockets)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main(sys.argv[1:])
