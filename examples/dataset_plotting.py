#!/usr/bin/env python3
"""Add a dataset and plotting window to the App

Usage:
  dataset_plotting.py [--dummy] [--debug] [--console] [--info]

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

from PyQt5.QtWidgets import QGridLayout, QTabWidget

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("Interactive Python Demo")

        # connect two instruments
        self.app.add_instrument(
            hc.instruments.Alicat_M_Series("alicat1", "192.168.0.15")
        )
        self.app.add_instrument(
            hc.instruments.Alicat_M_Series("alicat2", "192.168.0.15")
        )

        # add GUI widgets
        self.alicat1_ctrl = hc.gui.FlowController(
            self.app, "alicat1", "Flow Controller A"
        )
        self.alicat2_ctrl = hc.gui.FlowController(
            self.app, "alicat2", "Flow Controller B"
        )

        # create a dataset
        dataset = hc.Dataset("mydata", self.app)
        # and then define two parameters of existing instruments to track here
        dataset.track_instrument("alicat1", "RATE", alias="Nitrogen rate")
        dataset.track_instrument("alicat2", "PRESSURE", alias="Air pressure")

        # automatically update the dataset every 2 seconds
        dataset.start_updates(2)

        # add it to the app (so that the app can for example save all datasets to disk)
        self.app.add_dataset(dataset)

        # optionally create a dataset widget that allows to browse all datasets
        self.data_widget = hc.gui.DataWidget(self.app, "Data Browser")

        # let's also plot the data
        self.plot = hc.gui.PlotTool(self.app)
        self.plot.set_dataset("mydata")

        # display all the widgets we created so far as tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.alicat1_ctrl, "Instrument A")
        self.tabs.addTab(self.alicat2_ctrl, "Instrument B")
        self.tabs.addTab(self.data_widget, "Data")
        self.tabs.addTab(self.plot, "Plotting")

        self.setCentralWidget(self.tabs)
        self.show()


main_window = Demo(dummy=dummy)
sys.exit(main_window.app.exec_())
