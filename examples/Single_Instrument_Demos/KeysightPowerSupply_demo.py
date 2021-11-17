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
from pathlib import Path
import sys

from docopt import docopt

from PyQt5.QtWidgets import QWidget, QGridLayout
from PyQt5.QtGui import QDoubleValidator

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("KeysightPowerSupply Demo")

        # This is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # Create an Keysight_36300 instrument backend and add it to the app
        self.app.add_instrument(
            hc.instruments.Keysight_36300("Keysight_36300", "192.168.0.3:5025")
        )

        # Load a settings file with preset values for the instrument parameters
        keysight_settings = (
            Path.cwd() / "settings_files" / "keysight_powersupply_init.json"
        )
        self.app.add_load_settings_hook("Keysight_36300", keysight_settings)

        # Create a keysight powersupply control with channels 1, 2, and 3
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

        # Add the control to the main widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.keysight_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
