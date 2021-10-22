#!/usr/bin/env python3
"""Keysight Power Supply demo

Usage:
  KeysightPowerSupply_demo.py [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console

"""

import logging
import sys
from os import getcwd

from docopt import docopt
from pathlib import Path

from PyQt5.QtWidgets import QWidget, QGridLayout
from PyQt5.QtGui import QDoubleValidator

import pkg_resources

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

if commands["--debug"]:
    loglevel = logging.DEBUG
elif commands["--info"]:
    loglevel = logging.INFO
else:
    loglevel = logging.WARNING

if commands["--console"]:
    logoutput = None
else:
    logoutput = Path("hardware-control.log")

logger = logging.getLogger(__name__)
hc.setup_logging(logger, logoutput, loglevel)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("KeysightPowerSupply Demo")

        self.main_widget = QWidget(self)

        # Load a settings file with preset values for the instrument parameters
        cwd = getcwd()
        keysight_settings = cwd + "/settings_files/keysight_powersupply_init.json"

        # Add a keysight power supply to the app
        self.app.add_instrument(
            hc.instruments.Keysight_36300(
                "Keysight_36300", "192.168.0.3:5025", keysight_settings
            )
        )

        # Create a keysight powersupply control with channels 1,2, and 3
        # with color gold, green, and blue, and the option to set voltage
        # and current for each channel
        self.keysight_ctrl = hc.gui.KeysightPowerSupply(
            self.app,
            "Keysight_36300",
            [1, 2, 3],
            ["gold", "green", "blue"],
            set_voltage_channels=[1, 2, 3],
            set_current_channels=[1, 2, 3],
        )
        # Validator for current on channel 1
        self.keysight_ctrl.channel_widgets[0].set_current.setValidator(
            QDoubleValidator(0, 10.0, 3)
        )

        self.grid = QGridLayout()
        self.grid.addWidget(self.keysight_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
