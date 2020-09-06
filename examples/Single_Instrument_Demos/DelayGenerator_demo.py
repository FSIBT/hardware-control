"""Device demo

Usage:
  device_demo [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""

import logging
import sys

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout
from docopt import docopt

import hardware_control.backends as hc_back
import hardware_control.gui as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging(logger, commands, "hardware_control.log")


class Demo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        # set title of window
        self.setWindowTitle("Demo")

        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # create a backend and a GUI control for the backend
        self.trigger = hc_back.SRS_DG535("GPIB0::15::INSTR")
        self.trigger_ctrl = hc.DelayGenerator(app, self.trigger, "Trigger", "DEFAULT")

        # Add control to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.trigger_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.trigger_ctrl.close()


def main():
    app = hc.App(dummy=dummy)
    app.print_close_info = True
    ex = Demo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
