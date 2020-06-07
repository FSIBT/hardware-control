#!/usr/bin/env python3
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
from hardware_control.DelayGenerator.SRSDG535Ctrl import SRSDG535Ctrl
from hardware_control.DelayGenerator.HC_DelayGenerator import HC_DelayGenerator
from hardware_control.base import HC_App, HC_MainWindow, Dataset

commands = docopt(__doc__)
dummy = commands["--dummy"]


class PuslseGenDemo(HC_MainWindow):
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        self.setWindowTitle("Flow Controller Demo")

        self.main_widget = QWidget(self)

        self.instr = SRSDG535Ctrl("GPIB0::10::INSTR")
        self.instr_ctrl = HC_DelayGenerator(self.instr, self)

        self.trig1 = SRSDG535Ctrl("GPIB0::10::INSTR")
        self.trig1_ctrl = HC_DelayGenerator(self.trig1, self, "Trigger 1", "DEFAULT")

        self.grid = QGridLayout()
        self.grid.addWidget(self.instr_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.instr_ctrl.close()


app = HC_App(dummy=dummy)
app.print_close_info = True
ex = PuslseGenDemo(app)
app.aboutToQuit.connect(ex.close)
sys.exit(app.exec_())
