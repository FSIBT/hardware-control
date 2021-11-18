#!/usr/bin/env python3
"""Multi-Channel Power Supply demo

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

        # Create TDKL_GenH, Caen_RSeries, and Rigol_DP832 instrument backends and add them to the app
        self.app.add_instrument(
            hc.instruments.TDKL_GenH("tdkl", "TCPIP0::192.168.1.19::INSTR")
        )
        self.app.add_instrument(
            hc.instruments.Caen_RSeries("caen", "192.168.1.20:1470")
        )
        # Note that this is not the correct address for Rigol
        self.app.add_instrument(
            hc.instruments.Rigol_DP832("rigol", "TCPIP0::192.168.2.83::INSTR")
        )

        # When not in dummy mode, these set channel voltage and current maximum values
        self.app.set_instrument_parameter("caen", "CH1_V_MAX", 20)
        self.app.set_instrument_parameter("caen", "CH1_I_MAX", 25)

        # Create three MultiPowerSupply controls that connects to each of the three instrument backends
        self.tdkl_ctrl = hc.gui.MultiPowerSupply(
            self.app,
            "tdkl",
            [1],
            "TDKL Power Supply Unit",
            enable_power_buttons="both",
        )
        self.caen_ctrl = hc.gui.MultiPowerSupply(
            self.app,
            "caen",
            [2],
            "Caen Power Supply Unit",
            show_VI_limits=True,
            show_status_panel=True,
            enable_power_buttons="both",
        )
        self.rigol_ctrl = hc.gui.MultiPowerSupply(
            self.app,
            "rigol",
            [3],
            "RigolDP832 Power Supply Unit",
            show_VI_limits=True,
            enable_power_buttons="both",
        )

        # Add the three control and the console to the main widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.tdkl_ctrl, 1, 1)
        self.grid.addWidget(self.caen_ctrl, 1, 2)
        self.grid.addWidget(self.rigol_ctrl, 1, 3)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()


if __name__ == "__main__":
    main_window = Demo(dummy=dummy)
    sys.exit(main_window.app.exec_())
