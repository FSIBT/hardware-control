"""Device demo

Usage:
  device_demo [--dummy] [--socket]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
"""

import sys

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout
from docopt import docopt

import hardware_control.backends as hc_back
import hardware_control.gui as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]


class Demo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        # set title of window
        self.setWindowTitle("Demo")
        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        ##### Add Device(s)
        self.trig1 = hc_back.SRS_DG535("GPIB0::15::INSTR")
        self.trig1_ctrl = hc.DelayGenerator(app, self.trig1, "Trigger 1", "DEFAULT")

        ##### Add above HC to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.trig1_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.trig1_ctrl.close()


def main():
    app = hc.App(dummy=dummy)
    app.print_close_info = True
    ex = Demo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
