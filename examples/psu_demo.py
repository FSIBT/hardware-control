#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PSU demo

Usage:
  psu_demo [--dummy] [--socket] [--debug]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of pyvisa
  --debug    allow debug print statements
"""

from matplotlib import pyplot as plt
import seaborn as sns
import sys

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QIntValidator, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QSizePolicy,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QMessageBox,
    QWidget,
    QLineEdit,
    QPushButton,
    QAction,
    QGridLayout,
)
import sys
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
use_sockets = commands["--socket"]
debug = commands["--debug"]

from hardware_control.base import HC_App
from hardware_control.PowerSupply.TDKLGenHCtrl import TDKLGenHCtrl
from hardware_control.PowerSupply.HC_MultiPowerSupply import HC_MultiPowerSupply


class PSUDemo(QMainWindow):
    def __init__(self, app, use_sockets: bool):
        super().__init__()
        self.app = app

        self.setWindowTitle("PSU Demo")

        self.main_widget = QWidget(self)

        psu = TDKLGenHCtrl("TCPIP0::192.168.1.19::INSTR", dummy)
        self.psu_ctrl = HC_MultiPowerSupply(
            psu, self, [1], "Power Supply Unit", "DEFAULT"
        )

        self.grid = QGridLayout()
        self.grid.addWidget(self.psu_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.psu_ctrl.close()


def main(argv):
    app = HC_App([])
    ex = PSUDemo(app, use_sockets)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main(sys.argv[1:])
