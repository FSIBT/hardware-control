"""Device demo

Usage:
  device_demo [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
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

        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # create a backend and a GUI control for the backend
        self.app.add_instrument(
            hc_inst.Ni_9000(instrument_name="NI-9000", connection_addr="cDAQ1")
        )
        self.iomodule = hc.gui.IOModule(
            self.app, "NI-9000", "IOModule_channel_data.json", num_columns=4
        )

        # Add control to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.iomodule, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
