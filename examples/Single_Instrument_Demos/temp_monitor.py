"""temp_monitor

Usage:
  temp_monitor [--dummy] [--debug] [--console] [--info]

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


class TemperatureMonitor(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        # set title of window
        self.setWindowTitle("Temperature Monitor")

        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # create a backend and a GUI control for the backend
        self.temp_backend = hc_back.Lakeshore_224("TCPIP0::192.168.0.14::INSTR") ## need to adjust to actual IP
        self.temp_gui = hc.TempMonitor(app, self.temp_backend)

        # Add control to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.temp_gui, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.temp_gui.close()


def main():
    app = hc.App(dummy=dummy)
    app.print_close_info = True
    ex = TemperatureMonitor(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
