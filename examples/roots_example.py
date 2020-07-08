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
import time

from PyQt5.QtWidgets import (
    QDoubleSpinBox,
    QStyleFactory,
    QTabWidget,
    QGroupBox,
    QWidget,
    QGridLayout,
)
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


from hardware_control.base import HC_App, HC_MainWindow, Dataset, AUTOMATIC
from hardware_control.PowerSupply.HC_MultiPowerSupply import HC_MultiPowerSupply, ONLY
from hardware_control.PowerSupply.CAEN14xxETCtrl import CAEN14xxETCtrl
from hardware_control.PowerSupply.Key36300Ctrl import Key36300Ctrl
from hardware_control.IOModule.ADAM6024Ctrl import ADAM6024Ctrl
from hardware_control.IOModule.HC_IOModule import HC_IOModule, read_channel_file
from hardware_control.base import HC_ConsoleWidget
from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope
from hardware_control.Oscilloscope.Pico6000Ctrl import Pico6000Ctrl
from hardware_control.widgets import (
    HC_PlotTool,
    HC_MiniPlotTool,
    HC_MonitorTool,
    HC_StatusTool,
    HC_ZMQConnectionTool,
    HC_LoggerTool,
)


logger = logging.getLogger(__name__)
hc_logger = logging.getLogger("hardware_control")

if print_console:
    logger.setLevel(level=loglevel)
    hc_logger.setLevel(level=loglevel)
    print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: Console")
else:
    logger.setLevel(level=loglevel)
    hc_logger.setLevel(level=loglevel)
    fh = logging.FileHandler(logfile_name)
    fh.setLevel(loglevel)
    hc_logger.addHandler(fh)

logger.info("Roots Example Starting")


def example_function(tool, hook_name):

    print(f"{tool.name} called hook {hook_name}")

    try:
        tool.counter
    except:
        print("Created counter")
        tool.counter = 0

    if tool.counter < 1:
        tool.set_indicator(hook_name, "GREEN")
    elif tool.counter < 2:
        tool.set_indicator(hook_name, "RED")
    elif tool.counter < 3:
        tool.set_indicator(hook_name, "GREY")
    elif tool.counter < 4:
        tool.set_indicator(hook_name, "DARKGREY")
    elif tool.counter < 5:
        tool.set_indicator(hook_name, "BLUE")
    else:
        tool.counter = -0.5
    tool.counter += 0.5

    print(f"\t{tool.counter}")


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

        self.tabs.addTab(self.tab_psu, "Power Supplies 1")
        self.tabs.addTab(self.tab_psu2, "Power Supplies 2")
        self.tabs.addTab(self.tab_pico1, "Picoscope")
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
            lock_until_sync=True,
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
            lock_until_sync=True,
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

        self.keysight_ps_be = Key36300Ctrl("TCPIP::192.168.0.3::5025::SOCKET")
        self.keysight_wdgt = HC_MultiPowerSupply(
            self.keysight_ps_be,
            self,
            [1, 2, 3],
            "Keysight Power Supply",
            show_VI_limits=True,
            show_custom_labels=True,
            all_enable_button=ONLY,
            lock_until_sync=True,
        )
        self.keysight_wdgt.set_maxV(1, 5)
        self.keysight_wdgt.set_maxV(2, 5)
        self.keysight_wdgt.set_maxV(3, 5)
        self.keysight_wdgt.set_maxI(1, 2.5)
        self.keysight_wdgt.set_maxI(2, 0.5)
        self.keysight_wdgt.set_maxI(3, 0.5)
        self.keysight_wdgt.set_channel_label(1, "1: Heater")
        self.keysight_wdgt.set_channel_label(2, "Channel 2")
        self.keysight_wdgt.set_channel_label(3, "Channel 3")
        self.keysight_wdgt.ramp_mode = AUTOMATIC
        self.keysight_wdgt.default_ramp_speed = 1

        # self.adam_be = ADAM6024Ctrl("192.168.0.5:1025")
        # self.adam_wdgt = HC_IOModule(
        #     self.adam_be,
        #     self,
        #     [
        #         (1, lambda p: p * 100, "Torr", "Pressure"),
        #         (2, lambda i: i / 10 * 3e-3 + 8.1e-6, "A", "Current"),
        #         (3, lambda v: v / 10 * 100e3 + 420, "V", "Voltage"),
        #     ],
        #     [(0, lambda v: v / 10, "kV", "Voltage")],
        #     "ADAM",
        #     lock_until_sync=True,
        # )

        adam_config = read_channel_file(
            "adam_config.json",
            {
                "hook_ai1": lambda p: p * 100,
                "hook_ai2": lambda i: i / 10 * 3e-3 + 8.1e-6,
                "hook_ai3": lambda v: v / 10 * 100e3 + 420,
                "hook_a01": lambda v: v / 10,
            },
        )
        self.adam_be = ADAM6024Ctrl("192.168.0.5:1025")
        self.adam_wdgt = HC_IOModule(
            self.adam_be,
            self,
            adam_config,
            "ADAM",
            lock_until_sync=True,
            num_columns=2,
        )

        # Put instrument(s) in tab
        self.tab_psu_layout = QGridLayout()
        # self.tab_psu_layout.addWidget(self.keysight_wdgt, 0, 0)
        # self.tab_psu_layout.addWidget(self.adam_wdgt, 1, 0)
        self.tab_psu_layout.addWidget(self.caen_wdgt_123, 0, 1)
        self.tab_psu_layout.addWidget(self.caen_wdgt_456, 1, 1)
        self.tab_psu.setLayout(self.tab_psu_layout)

        self.tab_psu2_layout = QGridLayout()
        self.tab_psu2_layout.addWidget(self.keysight_wdgt, 0, 0)
        self.tab_psu2_layout.addWidget(self.adam_wdgt, 1, 0)
        self.tab_psu2.setLayout(self.tab_psu2_layout)

        #####################################################################
        ######### Pico Tab

        self.pico1_be = Pico6000Ctrl("?")
        self.pico1_be.record_length = 70e3
        self.pico1_wdgt = HC_Oscilloscope(self.pico1_be, self, "Pico1")
        self.pico1_wdgt.load_state("./picoscope_init.json")
        self.pico1_wdgt.settings_to_UI()
        self.pico1_wdgt.send_state()

        self.tab_pico1_layout = QGridLayout()
        self.tab_pico1_layout.addWidget(self.pico1_wdgt, 0, 0)
        self.tab_pico1.setLayout(self.tab_pico1_layout)

        #####################################################################
        ######### Aux Tab

        self.zmqtool = HC_ZMQConnectionTool(self, "ZMQ Input Tool", "tcp://*:5555")

        self.tab_aux_layout = QGridLayout()
        self.tab_aux_layout.addWidget(self.zmqtool, 0, 0)
        self.tab_aux.setLayout(self.tab_aux_layout)

        #####################################################################
        ######### Plot Tab

        self.plot_wdgt1 = HC_PlotTool(self, "Heater Current")
        self.plot_wdgt2 = HC_PlotTool(self, "High Voltage")

        self.tab_plot_layout = QGridLayout()
        self.tab_plot_layout.addWidget(self.plot_wdgt1, 0, 0)
        self.tab_plot_layout.addWidget(self.plot_wdgt2, 1, 0)
        self.tab_plot.setLayout(self.tab_plot_layout)

        #####################################################################
        ######## Tab 3

        self.logtool = HC_LoggerTool(self, "Data Logger")
        self.logtool.update_groups()

        self.app.data_sets["Autolog"] = Dataset("Autolog")
        self.app.data_sets["Autolog"].start_asynch(3)
        self.app.data_sets["Autolog"].add_instrument(self.keysight_wdgt)

        self.app.data_sets["Keysight"] = Dataset("Keysight")
        self.app.data_sets["Keysight"].start_asynch(1)
        self.app.data_sets["Keysight"].add_instrument(self.keysight_wdgt)

        self.app.data_sets["ADAM"] = Dataset("ADAM")
        self.app.data_sets["ADAM"].start_asynch(1)
        self.app.data_sets["ADAM"].add_instrument(
            self.adam_wdgt, ["CH2_V_meas", "CH3_V_meas"]
        )
        self.app.data_sets["ADAM"].name_channel("ADAM:CH2_V_meas", "HV Current")
        self.app.data_sets["ADAM"].name_channel("ADAM:CH3_V_meas", "High Voltage")

        self.app.data_sets["HEATER"] = Dataset("HEATER")
        self.app.data_sets["HEATER"].start_asynch(1)
        self.app.data_sets["HEATER"].add_instrument(self.keysight_wdgt, ["CH1_I_out"])
        self.app.data_sets["HEATER"].add_instrument(self.adam_wdgt, ["CH1_V_meas"])
        self.app.data_sets["HEATER"].name_channel(
            "Keysight Power Supply:CH1_I_out", "Heater Current"
        )
        self.app.data_sets["HEATER"].name_channel("ADAM:CH1_V_meas", "Pressure")

        self.logtool.update_groups()
        self.logtool.set_group("Autolog")
        self.plot_wdgt1.set_dataset("HEATER")
        self.plot_wdgt2.set_dataset("ADAM")

        self.tab_data_layout = QGridLayout()
        self.tab_data_layout.addWidget(self.logtool, 1, 0)
        self.tab_data.setLayout(self.tab_data_layout)

        #####################################################################
        ######## Set master window layout

        self.statustool = HC_StatusTool(self, "Connection Status")
        self.statustool.update_instruments()

        self.miniplot = HC_MiniPlotTool(self, "Plot", 220, 220)
        self.miniplot.set_dataset("ADAM")

        self.monitor = HC_MonitorTool(self, "Error Monitor")
        self.monitor.add_hook("Hook 1", example_function)
        self.monitor.add_hook("Hook 2", example_function)
        self.monitor.add_spacer()

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.tabs, 0, 0, 3, 1)
        self.master_layout.addWidget(self.statustool, 0, 1)
        self.master_layout.addWidget(self.miniplot, 1, 1)
        self.master_layout.addWidget(self.monitor, 2, 1)

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
