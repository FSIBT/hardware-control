#!/usr/bin/env python3
"""oscilloscope_example to control the hardware_control test stand

Usage:
  sts50_example [--dummy] [--socket] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""

import logging
import sys
import warnings

from PyQt5.QtWidgets import QDoubleSpinBox, QStyleFactory, QTabWidget, QGroupBox
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
info = commands["--info"]
if commands["--socket"]:
    connection_type = "socket"
else:
    connection_type = "visa"
debug = commands["--debug"]
print_console = commands["--console"]

logfile_name = "hardware_control.log"

if debug:
    loglevel = logging.DEBUG
    loglevelname = "Debug"
elif info:
    loglevel = logging.INFO
    loglevelname = "Info"
else:
    loglevel = logging.WARNING
    loglevelname = "Warning"

if print_console:
    logging.basicConfig(level=loglevel)
    print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: Console")
else:
    logging.basicConfig(filename=logfile_name, level=loglevel)
    print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: {logfile_name}")


from hardware_control.base import HC_App, HC_MainWindow, Dataset
from hardware_control.PowerSupply.HC_MultiPowerSupply import *
from hardware_control.PowerSupply.CAEN14xxETCtrl import CAEN14xxETCtrl
from hardware_control.PowerSupply.Key36300Ctrl import Key36300Ctrl
from hardware_control.widgets import (
    HC_ZMQConnectionTool,
    HC_StatusTool,
    HC_PlotTool,
    HC_MiniPlotTool,
    HC_LoggerTool,
)
from hardware_control.IOModule.ADAM_6024Ctrl import ADAM_6024Ctrl
from hardware_control.IOModule.HC_IOModule import HC_IOModule
from hardware_control.base import HC_ConsoleWidget
from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope
from hardware_control.Oscilloscope.Pico5000ACtrl import Pico5000ACtrl


logger = logging.getLogger(__name__)

# handler = logging.FileHandler('sts50_example.log')
# handler.setLevel(logging.DEBUG)

# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)

# logger.addHandler(handler)

logger.info("Roots Example Starting")

# logger.info("Initailizing program")
#
# if info:
#     logger.setLevel(logging.INFO)
#
# if debug:
#     logger.setLevel(logging.DEBUG)


class RootsDemo(HC_MainWindow):
    def __init__(self, app):
        super().__init__(app)

        self.setWindowTitle("Comm Demo")

        self.tabs = QTabWidget()
        self.tab_psu = QWidget()
        # self.tab_psu2 = QWidget()
        # self.tab_pico1 = QWidget()
        self.tab_aux = QWidget()
        self.tab_plot = QWidget()
        self.tab_data = QWidget()
        self.python = HC_ConsoleWidget(main_app=app)

        self.tabs.addTab(self.tab_psu, "Power Supplies 1")
        # self.tabs.addTab(self.tab_psu2, "Power Supplies 2")
        # self.tabs.addTab(self.tab_pico1, "Picoscope")
        self.tabs.addTab(self.tab_aux, "Aux")
        self.tabs.addTab(self.tab_plot, "Plots")
        self.tabs.addTab(self.tab_data, "Datasets")
        self.tabs.addTab(self.python, "Console")

        self.main_widget = QWidget(self)

        #####################################################################
        ######## Tab 1

        self.caen_be = CAEN14xxETCtrl("192.168.0.1:1470")
        self.caen_wdgt_123 = HC_MultiPowerSupply(
            self.caen_be,
            self,
            [1, 2, 3],
            "CAEN Power Supply 1-3",
            show_VI_limits=True,
            show_custom_labels=True,
            show_status_panel=True,
        )
        self.caen_wdgt_123.set_maxV(1, 2e3)
        self.caen_wdgt_123.set_maxV(2, 1e3)
        self.caen_wdgt_123.set_maxV(3, 1.1e3)
        self.caen_wdgt_123.set_maxI(1, 300e-6)
        self.caen_wdgt_123.set_maxI(2, 300e-6)
        self.caen_wdgt_123.set_maxI(3, 300e-6)
        self.caen_wdgt_123.set_channel_label(1, "1: NaI")
        self.caen_wdgt_123.set_channel_label(2, "2: LaBr")
        self.caen_wdgt_123.set_channel_label(3, "3: YAP")
        self.caen_wdgt_456 = HC_MultiPowerSupply(
            self.caen_be,
            self,
            [4, 5, 6],
            "CAEN Power Supply 4-6",
            show_VI_limits=True,
            show_custom_labels=True,
            show_status_panel=True,
        )
        self.caen_wdgt_456.set_maxV(4, 1705)
        self.caen_wdgt_456.set_maxV(5, 2e3)
        self.caen_wdgt_456.set_maxV(6, 500)
        self.caen_wdgt_456.set_maxI(4, 300e-6)
        self.caen_wdgt_456.set_maxI(5, 300e-6)
        self.caen_wdgt_456.set_maxI(6, 800e-6)
        self.caen_wdgt_456.set_channel_label(4, "4: EJ")
        self.caen_wdgt_456.set_channel_label(5, "5: UCB")
        self.caen_wdgt_456.set_channel_label(6, "6: Target")

        # Put instrument(s) in tab
        self.tab_psu_layout = QGridLayout()
        # self.tab_psu_layout.addWidget(self.keysight_wdgt, 0, 0)
        # self.tab_psu_layout.addWidget(self.adam_wdgt, 1, 0)
        self.tab_psu_layout.addWidget(self.caen_wdgt_123, 0, 1)
        self.tab_psu_layout.addWidget(self.caen_wdgt_456, 1, 1)
        self.tab_psu.setLayout(self.tab_psu_layout)

        #####################################################################
        ######### Aux Tab

        self.zmqtool = HC_ZMQConnectionTool(self, "ZMQ Input Tool", "tcp://*:5555")

        self.tab_aux_layout = QGridLayout()
        self.tab_aux_layout.addWidget(self.zmqtool, 0, 0)
        self.tab_aux.setLayout(self.tab_aux_layout)

        #####################################################################
        ######### Plot Tab

        self.plot_wdgt = HC_PlotTool(self, "Plot")

        self.tab_plot_layout = QGridLayout()
        self.tab_plot_layout.addWidget(self.plot_wdgt, 0, 0)
        self.tab_plot.setLayout(self.tab_plot_layout)

        #####################################################################
        ######## Tab 3

        self.logtool = HC_LoggerTool(self, "Data Logger")
        self.logtool.update_groups()

        self.app.data_sets["Autolog"] = Dataset("Autolog")
        self.app.data_sets["Autolog"].start_asynch(3)
        self.app.data_sets["Autolog"].add_instrument(self.caen_wdgt_123)
        self.app.data_sets["Autolog"].add_instrument(self.caen_wdgt_456)
        # self.app.data_sets["Keysight"] = Dataset("Keysight")
        # self.app.data_sets["Keysight"].start_asynch(1)
        # self.app.data_sets["Keysight"].add_instrument(self.keysight_wdgt)
        # self.app.data_sets["ADAM"] = Dataset("ADAM")
        # self.app.data_sets["ADAM"].start_asynch(1)
        # self.app.data_sets["ADAM"].add_instrument(
        #     self.adam_wdgt, ["CH1_V_meas", "CH2_V_meas", "CH3_V_meas"]
        # )
        self.logtool.update_groups()
        self.logtool.set_group("Autolog")
        # self.plot_wdgt.set_dataset("ADAM")

        self.tab_data_layout = QGridLayout()
        self.tab_data_layout.addWidget(self.logtool, 1, 0)
        self.tab_data.setLayout(self.tab_data_layout)

        #####################################################################
        ######## Set master window layout

        self.statustool = HC_StatusTool(self, "Connection Status")
        self.statustool.update_instruments()
        #
        # self.miniplot = HC_MiniPlotTool(self, "Plot", 220, 220)
        # self.miniplot.set_dataset("ADAM")

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.tabs, 0, 0, 3, 1)
        self.master_layout.addWidget(self.statustool, 0, 1)
        # self.master_layout.addWidget(self.miniplot, 1, 1)

        self.main_widget = QWidget(self)
        self.main_widget.setLayout(self.master_layout)
        self.setCentralWidget(self.main_widget)

        # ['macintosh', 'Windows', 'Fusion']
        self.app.setStyle(QStyleFactory.create("Fusion"))
        # self.app.setStyle(QStyleFactory.create("Windows"))

        self.show()

    def close(self):
        print("Closing")
        self.app.close()


def main():
    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning
    )  # ToDo Not a solution
    app = HC_App(dummy=dummy)
    app.print_close_info = True

    ex = RootsDemo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
