"""Device demo

Usage:
  device_demo [--dummy] [--socket] [--debug]

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

# from hardware_control.DelayGenerator.SRSDG535Ctrl import SRSDG535Ctrl
from hardware_control.DelayGenerator.SRSDG535Ctrl import SRSDG535Ctrl
from hardware_control.DelayGenerator.HC_DelayGenerator import HC_DelayGenerator


class Demo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        # set title of window
        self.setWindowTitle("Demo")
        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        ##### Add Device(s)
        self.trig1 = SRSDG535Ctrl("GPIB0::15::INSTR", dummy, debug)
        self.trig1_ctrl = HC_DelayGenerator(self.trig1, self, "Trigger 1", "DEFAULT")

        ##### Add above HC to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.trig1_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    #
    def close(self):
        self.trig1_ctrl.close()


def main():
    app = HC_App(dummy=dummy)
    app.print_close_info = True
    ex = Demo(app)  # Change accordingly
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
