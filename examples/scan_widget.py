#!/usr/bin/env python3
"""Add a scan widget window to the App. Run at logger level 'info'
(with --info flag) to see what the scan widget does at each scan
step.

Usage:
  scan_widget.py [--dummy] [--debug] [--info] [--console]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""
import logging
import sys
import random

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

        # This is the title that appears in the Qt Window
        self.setWindowTitle("Scan Widget Demo")

        # This is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # Create an Keysight_36300 instrument backend and add it to the app
        self.app.add_instrument(
            hc.instruments.Keysight_36300("Keysight_36300", "192.168.0.3:5025")
        )
        # Create a keysight powersupply control with channels 1, 2, and 3
        self.keysight_ctrl = hc.gui.KeysightPowerSupply(
            self.app,
            "Keysight_36300",
            [1, 2, 3],
            ["gold", "green", "blue"],
            set_voltage_channels=[1, 2, 3],
            set_current_channels=[1, 2, 3],
        )

        # Create a scan widget window with the option of running a Gaussian process
        self.scan_widget = hc.gui.ScanWidget(
            self.app,
            name="Scan Control",
            actions={"Trigger": self.trigger_fxn},
            scan_parameters={"Keysight_36300": ["CH1_I_SET", "CH1_V_SET"]},
            GP_option=True,
            get_measured_values_fxn=self.return_measured_vals,
            scan_cycle_fxn=self.scan_cycle_fxn,
            finish_scan_fxn=self.finish_fxn,
        )
        # Set both the pause before and pause after measurement to 2 seconds
        self.scan_widget.pause_edit_before.setText("2")
        self.scan_widget.pause_edit_after.setText("2")

        # Add the keysight control and scan widget to the main widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.keysight_ctrl, 0, 0)
        self.grid.addWidget(self.scan_widget, 0, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def trigger_fxn(self):
        """Function that runs before each measurement."""
        logger.info(
            f"Triggering at value {self.scan_widget.val_list[self.scan_widget.count]} for parameter {self.scan_widget.scan_parameter}"
        )

    def scan_cycle_fxn(self):
        """Function that runs after each measurement."""
        logger.info(
            f"Finished cycle {self.scan_widget.count + 1} of {len(self.scan_widget.val_list)}."
        )
        logger.info(
            f"Values measured so far:\nX-axis: {self.scan_widget.val_list[: self.scan_widget.count + 1]}\nY-Axis: {self.measured_values[: self.scan_widget.count + 1]}"
        )

    def return_measured_vals(self):
        """Function that returns all the values measured up to this point."""
        # Check if the list of measured values exists; if it does not, create it
        if not hasattr(self, "measured_values"):
            self.measured_values = []
        # Add a random "measured value" to the list of measured values
        self.measured_values.append(random.uniform(0.0, 100.0))
        return self.measured_values

    def finish_fxn(self):
        """Function that runs at the conclusion of every scan."""
        logger.info(f"Finished scan. Goodbye!")


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
