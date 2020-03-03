#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flowcontroller to control the hardware_control test stand

Usage:
  flowcontroller_example [--dummy]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
"""
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout
from docopt import docopt
from hardware_control.PulseGenerator.SRSDG535Int import SRSDG535Int
from hardware_control.PulseGenerator.hc_pulsegen import PulseGenControl

commands = docopt(__doc__)
dummy = commands["--dummy"]


class PuslseGenDemo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.setWindowTitle("Flow Controller Demo")

        self.main_widget = QWidget(self)

        self.instr = SRSDG535Int("GPIB0::10::INSTR", dummy, True)
        self.instr_ctrl = PulseGenControl(self.instr, "DEFAULT", True)

        self.grid = QGridLayout()
        self.grid.addWidget(self.instr_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.instr_ctrl.close()


app = QApplication([])
ex = PuslseGenDemo(app)
app.aboutToQuit.connect(ex.close)
sys.exit(app.exec_())
