"""Rigol Oscilloscope demo

Usage:
  Oscilloscope_demo_Rigol.py [--conn_addr=CONN_ADD] [--dummy] [--debug] [--console] [--info]

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

import hardware_control.instruments as hc_inst
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

        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # create a backend and a GUI control for the backend
        self.app.add_instrument(hc_inst.Rigol_DS1000Z("Rigol-1000", conn_addr))

        self.scope_ctrl = hc.gui.Oscilloscope(
            self.app,
            "Rigol-1000",
            [1, 2, 3, 4],
            "Rigol Oscilloscope",
            instrument_type="rigol",
        )

        # Add control to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
