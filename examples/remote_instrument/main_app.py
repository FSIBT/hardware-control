#!/usr/bin/env python3
"""Example on how to use an instrument driver on a remote computer or running in another program.

Usage:
  main_app.py [--dummy] [--debug] [--console] [--info]

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

        self.setWindowTitle("Remote Demo")

        self.tabs = QTabWidget()

        # to connect to a remote instrument, the remote program needs to be running
        # and we need to know the IP address and port number that we have defined in that
        # progra,. See client.py
        self.app.add_remote_instrument("alicat", "127.0.0.1:4444")

        self.instr_ctrl = hc.gui.FlowController(self.app, "alicat", "Flow Controller")

        self.ipython = hc.gui.Qtconsole(self.app)

        self.tabs.addTab(self.instr_ctrl, "Instruments")
        self.tabs.addTab(self.ipython, "Interactive")

        self.setCentralWidget(self.tabs)
        self.show()


print("*** client.py must already be running ***")
main_window = Demo(dummy=dummy)
sys.exit(main_window.app.exec_())
