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


from hardware_control.base import HC_App, HC_MainWindow, Dataset, AUTOMATIC, MANUAL
from hardware_control.PowerSupply.HC_MultiPowerSupply import *
from hardware_control.PowerSupply.RigolDP832Ctrl import RigolDP832Ctrl
from hardware_control.widgets import (
    HC_ZMQConnectionTool,
    HC_PlotTool,
    HC_MiniPlotTool,
    HC_LoggerTool,
    HC_StatusTool,
)
from hardware_control.base import HC_ConsoleWidget
from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope


logger = logging.getLogger(__name__)
hc_logger = logging.getLogger("hardware_control")

if print_console:
    # logging.basicConfig(level=loglevel)
    logger.setLevel(level=loglevel)
    hc_logger.setLevel(level=loglevel)
    print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: Console")
else:
    logger.setLevel(level=loglevel)
    hc_logger.setLevel(level=loglevel, filename=logfile_name)
    # logging.basicConfig(filename=logfile_name, level=loglevel)
    print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: {logfile_name}")

# handler = logging.FileHandler('sts50_example.log')
# handler.setLevel(logging.DEBUG)

# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)

# logger.addHandler(handler)

pv_logger = logging.getLogger("pyvisa")
pv_logger.setLevel("ERROR")

logger.info("Roots Example Starting")

# logger.info("Initailizing program")
#
# if info:
#     logger.setLevel(logging.INFO)
#
# if debug:
#     logger.setLevel(logging.DEBUG)


def ramp_func(obj, parameter, present, target):

    # Mark as complete if within 1 unit of target
    if present + 1 > target and present - 1 < target:
        return None

    # Compute ramp speed
    dVal = obj.default_ramp_speed
    if parameter in obj.ramp_speed:
        dVal = obj.ramp_speed[parameter]

    # Compute new value
    if target > present:
        return min(present + dVal, target)
    else:
        return max(present - dVal, target)


class RootsDemo(HC_MainWindow):
    def __init__(self, app):
        super().__init__(app)

        self.setWindowTitle("ROOTS Control")

        self.tabs = QTabWidget()
        self.tab_psu = QWidget()
        self.tab_psu2 = QWidget()
        self.tab_pico1 = QWidget()
        self.tab_aux = QWidget()
        self.tab_plot = QWidget()
        self.tab_data = QWidget()
        self.python = HC_ConsoleWidget(main_app=app)

        self.tabs.addTab(self.tab_psu, "Power Supplies")
        self.tabs.addTab(self.tab_aux, "Aux")
        self.tabs.addTab(self.tab_plot, "Plots")
        self.tabs.addTab(self.tab_data, "Datasets")
        self.tabs.addTab(self.python, "Console")

        self.main_widget = QWidget(self)

        #####################################################################
        ######## Tab 1

        self.psu_be = RigolDP832Ctrl("TCPIP0::192.168.1.83::INSTR")
        self.psu_wdgt1 = HC_MultiPowerSupply(
            self.psu_be,
            self,
            [1, 2],
            "Rigol Channel 1,2",
            show_VI_limits=True,
            show_custom_labels=True,
            show_status_panel=True,
            all_enable_button=ADD,
        )
        self.psu_wdgt1.set_maxV(1, 29)
        self.psu_wdgt1.set_maxV(2, 29)
        self.psu_wdgt1.set_maxI(1, 3)
        self.psu_wdgt1.set_maxI(2, 3)
        self.psu_wdgt1.set_channel_label(1, "1: NaI")
        self.psu_wdgt1.set_channel_label(2, "2: LaBr")
        # self.psu_wdgt1.ramp_mode = AUTOMATIC
        # self.psu_wdgt1.default_ramp_speed = 1
        self.psu_wdgt1.ramp_mode = MANUAL
        self.psu_wdgt1.ramp_hooks.append(ramp_func)
        self.psu_wdgt1.default_ramp_speed = 1
        self.psu_wdgt1.comm.try_connect()
        self.psu_wdgt2 = HC_MultiPowerSupply(
            self.psu_be,
            self,
            [3],
            "Rigol Channel 3",
            show_VI_limits=True,
            show_custom_labels=True,
            show_status_panel=True,
            all_enable_button=ADD,
        )
        self.psu_wdgt2.set_maxV(3, 4)
        self.psu_wdgt2.set_maxI(3, 3)
        self.psu_wdgt2.set_channel_label(3, "3: EJ")

        # Put instrument(s) in tab
        self.tab_psu_layout = QGridLayout()
        # self.tab_psu_layout.addWidget(self.keysight_wdgt, 0, 0)
        # self.tab_psu_layout.addWidget(self.adam_wdgt, 1, 0)
        self.tab_psu_layout.addWidget(self.psu_wdgt1, 0, 1)
        self.tab_psu_layout.addWidget(self.psu_wdgt2, 1, 1)
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
        self.app.data_sets["Autolog"].add_instrument(self.psu_wdgt1)
        # self.app.data_sets["Autolog"].add_instrument(self.psu_wdgt2)
        self.app.data_sets["Output"] = Dataset("Output")
        self.app.data_sets["Output"].start_asynch(1)
        self.app.data_sets["Output"].add_instrument(
            self.psu_wdgt1, ["CH1_V_out", "CH2_V_out"]
        )
        self.app.data_sets["Output"].add_instrument(self.psu_wdgt2, ["CH3_V_out"])
        # self.app.data_sets["ADAM"] = Dataset("ADAM")
        # self.app.data_sets["ADAM"].start_asynch(1)
        # self.app.data_sets["ADAM"].add_instrument(
        #     self.adam_wdgt, ["CH1_V_meas", "CH2_V_meas", "CH3_V_meas"]
        # )
        self.logtool.update_groups()
        self.logtool.set_group("Output")
        self.plot_wdgt.set_dataset("Output")

        self.tab_data_layout = QGridLayout()
        self.tab_data_layout.addWidget(self.logtool, 1, 0)
        self.tab_data.setLayout(self.tab_data_layout)

        #####################################################################
        ######## Set master window layout

        self.statustool = HC_StatusTool(self, "Connection Status")
        self.statustool.update_instruments()

        # self.miniplot = HC_MiniPlotTool(self, "Plot", 220, 220)
        # self.miniplot.set_dataset("Output")

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
