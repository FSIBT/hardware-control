"""Delay Generator demo

Usage:
  DelayGenerator_demo.py [--conn_addr=CONN_ADD] [--dummy] [--debug] [--console] [--info]

Options:
  --conn_addr=CONN_ADD  Connection address of physical instrument [default: None].
                        Required if not in dummy mode.
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

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]
conn_addr = commands["--conn_addr"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("Demo")

        # This is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # Create an SRS_DG535 instrument backend and add it to the app
        self.app.add_instrument(hc.instruments.SRS_DG535("DG5353", conn_addr))

        # Create a DelayGenerator GUI control that connects to the instrument backend
        self.trigger_ctrl = hc.gui.DelayGenerator(self.app, "DG5353", "Delay Generator")

        # Create an interactive ipython console
        self.ipython = hc.gui.Qtconsole(self.app)

        # Add the control and the console to the main widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.trigger_ctrl, 0, 0)
        self.grid.addWidget(self.ipython, 1, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
