"""Picoscope demo

Usage:
  Picoscope_demo.py [--dummy] [--debug] [--console] [--info]

Options:
  --dummy               Use dummy connection for instruments that return semi-random data
                        so that one can run the program away from the test stand.
  --debug               Allow debug print statements.
  --info                Allow info print statements.
  --console             Print logger output to console.
"""

import logging
import sys

from PyQt5.QtWidgets import QWidget, QGridLayout
from docopt import docopt

import hardware_control.instruments as hc_inst
import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("Demo")

        # This is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # Create an Picoscope-2000a instrument backend and add it to the app
        channels = [0, 1]
        self.app.add_instrument(
            hc_inst.Picoscope("Picoscope-2000a", pico_series="2000a", channels=channels)
        )

        # Create an Oscilloscope GUI control that connects to the instrument backend
        self.scope_ctrl = hc.gui.Oscilloscope(
            self.app,
            "Picoscope-2000a",
            channels,
            "Picoscope",
            instrument_type="picoscope",
        )

        # Add the control to the main widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
