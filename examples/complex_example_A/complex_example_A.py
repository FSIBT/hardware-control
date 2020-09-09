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

from docopt import docopt
from PyQt5.QtWidgets import (
    QStyleFactory,
    QTabWidget,
    QWidget,
    QGridLayout,
)

import hardware_control.backends as hc_back
import hardware_control.gui as hc


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


class RootsDemo(hc.MainWindow):
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
        self.python = hc.Qtconsole(app)

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

        self.caen_be = hc_back.Caen_14xxET("192.168.0.1:1470")
        self.caen_wdgt_123 = hc.MultiPowerSupply(
            app,
            self.caen_be,
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
        self.caen_wdgt_456 = hc.MultiPowerSupply(
            app,
            self.caen_be,
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

        self.keysight_ps_be = hc_back.Keysight_36300("TCPIP::192.168.0.3::5025::SOCKET")
        self.keysight_wdgt = hc.MultiPowerSupply(
            app,
            self.keysight_ps_be,
            [1, 2, 3],
            "Keysight Power Supply",
            show_VI_limits=True,
            show_custom_labels=True,
            all_enable_button=hc.MultiPowerSupply.ONLY,
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

        # self.adam_be = ADAM6024Ctrl("192.168.0.5:1025")
        # self.adam_wdgt = hc.IOModule(
        #     app,
        #     self.adam_be,
        #     [
        #         (1, lambda p: p * 100, "Torr", "Pressure"),
        #         (2, lambda i: i / 10 * 3e-3 + 8.1e-6, "A", "Current"),
        #         (3, lambda v: v / 10 * 100e3 + 420, "V", "Voltage"),
        #     ],
        #     [(0, lambda v: v / 10, "kV", "Voltage")],
        #     "ADAM",
        #     lock_until_sync=True,
        # )

        # adam_config = hc.read_channel_file(
        #     "ADAM_init.json",
        #     {
        #         "hook_ai1": lambda p: p * 100,
        #         "hook_ai2": lambda i: i / 10 * 3e-3 + 8.1e-6,
        #         "hook_ai3": lambda v: v / 10 * 100e3 + 420,
        #         "hook_a01": lambda v: v / 10,
        #     },
        # )
        self.adam_be = hc_back.Adam_6015("192.168.0.5:1025")
        self.adam_wdgt = hc.IOModule(
            app,
            self.adam_be,
            channel_data="ADAM_init.json",
            name="ADAM",
            lock_until_sync=True,
            num_columns=2,
        )
        self.adam_wdgt.update_values_hooks["CHI1"].append(lambda s, v: v * 100)
        self.adam_wdgt.update_values_hooks["CHI2"].append(
            lambda s, v: v / 10 * 3e-3 + 8.1e-6
        )
        self.adam_wdgt.update_values_hooks["CHI3"].append(
            lambda s, v: v / 10 * 100e-3 + 420
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

        self.pico1_be = hc_back.Picotech_6000("USB::")
        self.pico1_be.record_length = 70e3
        self.pico1_wdgt = hc.Oscilloscope(app, self.pico1_be, "Pico1")
        self.pico1_wdgt.load_state("./picoscope_init.json")
        self.pico1_wdgt.settings_to_UI()
        self.pico1_wdgt.send_state()

        self.tab_pico1_layout = QGridLayout()
        self.tab_pico1_layout.addWidget(self.pico1_wdgt, 0, 0)
        self.tab_pico1.setLayout(self.tab_pico1_layout)

        #####################################################################
        ######### Aux Tab

        self.zmqtool = hc.ZMQConnectionTool(app, "ZMQ Input Tool", "tcp://*:5555")

        self.tab_aux_layout = QGridLayout()
        self.tab_aux_layout.addWidget(self.zmqtool, 0, 0)
        self.tab_aux.setLayout(self.tab_aux_layout)

        #####################################################################
        ######### Plot Tab

        self.plot_wdgt1 = hc.PlotTool(app, "Heater Current")
        self.plot_wdgt2 = hc.PlotTool(app, "High Voltage")

        self.tab_plot_layout = QGridLayout()
        self.tab_plot_layout.addWidget(self.plot_wdgt1, 0, 0)
        self.tab_plot_layout.addWidget(self.plot_wdgt2, 1, 0)
        self.tab_plot.setLayout(self.tab_plot_layout)

        #####################################################################
        ######## Tab 3

        self.logtool = hc.DataWidget(app, "Data Logger")
        self.logtool.update_groups()

        self.app.data_sets["Autolog"] = hc.Dataset("Autolog")
        self.app.data_sets["Autolog"].start_asynch(3)
        self.app.data_sets["Autolog"].add_instrument(self.keysight_wdgt)

        self.app.data_sets["Keysight"] = hc.Dataset("Keysight")
        self.app.data_sets["Keysight"].start_asynch(1)
        self.app.data_sets["Keysight"].add_instrument(self.keysight_wdgt)

        self.app.data_sets["ADAM"] = hc.Dataset("ADAM")
        self.app.data_sets["ADAM"].start_asynch(1)
        self.app.data_sets["ADAM"].add_instrument(
            self.adam_wdgt, ["CH2_V_meas", "CH3_V_meas"]
        )
        self.app.data_sets["ADAM"].name_channel("ADAM:CH2_V_meas", "HV Current")
        self.app.data_sets["ADAM"].name_channel("ADAM:CH3_V_meas", "High Voltage")

        self.app.data_sets["HEATER"] = hc.Dataset("HEATER")
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

        self.statustool = hc.StatusTool(app, "Connection Status")
        self.statustool.update_instruments()

        self.miniplot = hc.MiniPlotTool(app, "Plot", 220, 220)
        self.miniplot.set_dataset("ADAM")

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.tabs, 0, 0, 3, 1)
        self.master_layout.addWidget(self.statustool, 0, 1)
        self.master_layout.addWidget(self.miniplot, 1, 1)

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
    app = hc.App(dummy=dummy)
    app.print_close_info = True

    ex = RootsDemo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
