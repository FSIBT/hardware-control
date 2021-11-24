#!/usr/bin/env python3
"""Add an interactive python console to the App.

Usage:
  interactive_python.py [--dummy] [--debug] [--console] [--info]

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

from PyQt5.QtWidgets import QGridLayout, QTabWidget

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("Interactive Python Demo")

        self.tabs = QTabWidget()

        self.app.add_instrument(
            hc.instruments.Alicat_M_Series("alicat", "192.168.0.15")
        )
        self.instr_ctrl = hc.gui.FlowController(self.app, "alicat", "Flow Controller")

        self.ipython = hc.gui.Qtconsole(self.app)

        self.tabs.addTab(self.instr_ctrl, "Instruments")

        # This adds an interactive python console as a second tab
        # The user then has access to the app module and can create
        # scripts on the fly
        self.tabs.addTab(self.ipython, "Interactive")

        self.setCentralWidget(self.tabs)
        self.show()


main_window = Demo(dummy=dummy)
sys.exit(main_window.app.exec_())
