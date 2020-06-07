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

from hardware_control.FlowController.AlicatMSeriesCtrl import AlicatMSeriesCtrl
from hardware_control.FlowController.HC_FlowController import HC_FlowController

commands = docopt(__doc__)
dummy = commands["--dummy"]


class FlowControllerDemo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.setWindowTitle("Flow Controller Demo")

        self.main_widget = QWidget(self)

        self.instr = AlicatMSeriesCtrl("192.168.0.15", dummy, True)
        self.instr_ctrl = HC_FlowController(
            self.instr, "flowcontroller_state.json", True
        )

        self.grid = QGridLayout()
        self.grid.addWidget(self.instr_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.instr_ctrl.close()


app = QApplication([])
ex = FlowControllerDemo(app)
app.aboutToQuit.connect(ex.close)
sys.exit(app.exec_())
