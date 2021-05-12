"""temp_monitor

Usage:
  temp_monitor [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""

import logging
import sys

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout
from docopt import docopt

import hardware_control.backends as hc_back
import hardware_control.gui as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging(logger, commands, "hardware_control.log")


class TemperatureMonitor(QMainWindow):
    def __init__(self, app):

        super().__init__()

        self.app = app

        # set title of window
        self.setWindowTitle("Temperature Monitor")

        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # create a backend and a GUI control for the backend
        self.temp_backend = hc_back.Lakeshore_224("TCPIP::192.168.0.12::7777::SOCKET")
        self.temp_wdgt = hc.TempMonitor(app, self.temp_backend)

        # Create data_sets
        self.app.data_sets["Temps"] = hc.Dataset("Temps", self.app)
        self.app.data_sets["Temps"].add_instrument(self.temp_wdgt)
        self.app.data_sets["Temps"].start_asynch(3)
        self.app.data_sets["Temps"].start_autosave()

        # Add control to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.temp_wdgt, 1, 0)
        self.main_widget.setLayout(self.grid)

        self.plot_wdgt = hc.PlotTool(app, "Temperature Plot")
        self.plot_wdgt.set_dataset("Temps")  # Could add
        self.grid.addWidget(self.plot_wdgt, 0, 0)

        self.app.data_sets["Temps"].name_channel(
            "Lakeshore 224 Temperature Monitor:CHA_READ_TEMP", "Temp A"
        )
        self.app.data_sets["Temps"].name_channel(
            "Lakeshore 224 Temperature Monitor:CHB_READ_TEMP", "Temp B"
        )
        self.app.data_sets["Temps"].name_channel(
            "Lakeshore 224 Temperature Monitor:CHC1_READ_TEMP", "Temp C1"
        )
        self.app.data_sets["Temps"].name_channel(
            "Lakeshore 224 Temperature Monitor:CHD1_READ_TEMP", "Temp D1"
        )

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.temp_gui.close()


def main():
    app = hc.App(dummy=dummy)
    app.print_close_info = True
    ex = TemperatureMonitor(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
