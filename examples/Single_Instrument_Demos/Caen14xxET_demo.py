#!/usr/bin/env python3
"""Caen_RSeries demo

Usage:
  MultiPowerSupply_demo.py [--dummy] [--debug] [--console] [--info]

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

from PyQt5.QtWidgets import QWidget, QGridLayout

import hardware_control as hc


commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("MultiPowerSupply Demo")

        # This is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # Create Caen_RSeries instrument backend and add them to the app
        self.app.add_instrument(hc.instruments.Caen_RSeries("caen", "192.168.0.1:1470"))

        # When not in dummy mode, these set channel voltage and current maximum values for all 16 Caen channels
        for channel in range(4):
            self.app.set_instrument_parameter("caen", f"CH{channel}_V_MAX", 2000)
            self.app.set_instrument_parameter("caen", f"CH{channel}_I_MAX", 100e-6)

        # Create a MultiPowerSupply control that connects to each of the caen backend
        self.caen_ctrl = hc.gui.MultiPowerSupply(
            self.app,
            "caen",
            [x for x in range(4)],
            "Caen Power Supply Unit",
            show_VI_limits=True,
            show_status_panel=True,
            enable_power_buttons="both",
        )

        # Add the three control and the console to the main widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.caen_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
