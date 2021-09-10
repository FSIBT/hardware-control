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

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging(logger, commands, "hardware_control.log")


class TemperatureMonitor(hc.base.MainWindow):
    def __init__(self, app):

        super().__init__(app)

        self.app = app

        # set title of window
        self.setWindowTitle("Temperature Monitor")

        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        # create a backend and a GUI control for the backend
        self.L224 = hc.instruments.Lakeshore_224(
            "lakeshore", "TCPIP::192.168.0.12::7777::SOCKET"
        )
        self.app.add_instrument(self.L224)
        self.temp_wdgt = hc.gui.TempMonitor(
            app, instrument="lakeshore", channel_list=["A", "B", "C1", "D1"]
        )

        # Create data_sets
        self.app.data_sets["Temps"] = hc.Dataset("Temps", self.app)
        for ch in ["A", "B", "C1", "D1"]:
            self.app.data_sets["Temps"].add_instrument(
                self.temp_wdgt.instrument, f"CH{ch}_READ_TEMP"
            )
        self.app.data_sets["Temps"].start_updates(3)
        self.app.data_sets["Temps"].start_autosave()

        # Add control to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.temp_wdgt, 1, 0)
        self.main_widget.setLayout(self.grid)

        self.plot_wdgt = hc.gui.PlotTool(app, "Temperature Plot")
        self.plot_wdgt.set_dataset("Temps")  # Could add
        self.grid.addWidget(self.plot_wdgt, 0, 0)

        self.app.data_sets["Temps"].name_channel("lakeshore:CHA_READ_TEMP", "Temp A")
        self.app.data_sets["Temps"].name_channel("lakeshore:CHB_READ_TEMP", "Temp B")
        self.app.data_sets["Temps"].name_channel("lakeshore:CHC1_READ_TEMP", "Temp C1")
        self.app.data_sets["Temps"].name_channel("lakeshore:CHD1_READ_TEMP", "Temp D1")

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.app.close()


if __name__ == "__main__":
    app = hc.App(dummy=dummy)
    app.print_close_info = True
    ex = TemperatureMonitor(app)
    ex.L224.try_connect()
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())
