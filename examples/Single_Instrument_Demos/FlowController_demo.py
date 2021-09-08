#!/usr/bin/env python3
"""Flowcontroller to control the hardware_control test stand

Usage:
  flowcontroller_example [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console

"""
import logging
import sys

from docopt import docopt

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QTabWidget

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging(logger, commands, "hardware_control.log")


class Demo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.setWindowTitle("Flow Controller Demo")

        self.tabs = QTabWidget()

        self.app.add_instrument(
            hc.instruments.Alicat_M_Series("alicat", "192.168.0.15")
        )
        self.instr_ctrl = hc.gui.FlowController(app, "alicat", "Flow Controller", True)

        self.ipython = hc.gui.Qtconsole(self.app)

        self.tabs.addTab(self.instr_ctrl, "Instruments")
        self.tabs.addTab(self.ipython, "Interactive")

        self.setCentralWidget(self.tabs)
        self.show()

    def close(self):
        self.app.close()


app = hc.App(dummy=dummy)
ex = Demo(app)
app.aboutToQuit.connect(ex.close)
sys.exit(app.exec_())
