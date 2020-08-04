#!/usr/bin/env python3
"""Flowcontroller to control the hardware_control test stand

Usage:
  flowcontroller_example [--dummy]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
"""
import sys

from docopt import docopt

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout

import hardware_control.backends as hc_back
import hardware_control.gui as hc


commands = docopt(__doc__)
dummy = commands["--dummy"]


class PuslseGenDemo(hc.MainWindow):
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        self.setWindowTitle("Flow Controller Demo")

        self.main_widget = QWidget(self)

        self.instr = hc_back.SRS_DG535("GPIB0::10::INSTR")
        self.instr_ctrl = hc.DelayGenerator(self.instr, self)

        self.trig1 = hc_back.SRS_DG535("GPIB0::15::INSTR")
        self.trig1_ctrl = hc.DelayGenerator(self.trig1, self, "Trigger 1", "DEFAULT")

        self.grid = QGridLayout()
        self.grid.addWidget(self.instr_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.instr_ctrl.close()


app = hc.App(dummy=dummy)
app.print_close_info = True
ex = PuslseGenDemo(app)
app.aboutToQuit.connect(ex.close)
sys.exit(app.exec_())
