#!/usr/bin/env python3
"""oscilloscope_example to control the hardware_control test stand

Usage:
  sts50_example [--dummy] [--socket] [--debug] [--log]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
  --debug    allow debug print statements
  --log      save log file
"""

import sys

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout, QStyleFactory, QTabWidget
from docopt import docopt

import hardware_control.backends as hc_back
import hardware_control.gui as hc


commands = docopt(__doc__)
dummy = commands["--dummy"]
if commands["--socket"]:
    connection_type = "socket"
else:
    connection_type = "visa"
debug = commands["--debug"]
log = commands["--log"]


class STS50Demo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.setWindowTitle("Oscilloscope Demo")

        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()

        self.tabs.addTab(self.tab1, "Scope Tab")
        self.tabs.addTab(self.tab2, "Power Tab")
        self.tabs.addTab(self.tab3, "Other Tab")

        self.main_widget = QWidget(self)

        #####################################################################
        ######## Tab 1

        scpi_scope = hc_back.Keysight_4000X(
            "TCPIP0::192.168.0.14::INSTR",  # Enter socket address as ip:port, ex: 192.168.0.14:5025
        )
        self.scope_ctrl = hc.Oscilloscope(scpi_scope, self, "Keysight")

        # Put instrument(s) in tab
        self.tab1_layout = QGridLayout()
        self.tab1_layout.addWidget(self.scope_ctrl, 0, 0)
        self.tab1.setLayout(self.tab1_layout)

        #####################################################################
        ######## Tab 2

        awg = hc_back.Keysight_33500B(
            "TCPIP0::192.168.1.18::INSTR",
        )  # "USB0::0x0957::0x2907::MY52500624::INSTR"
        self.awg_ctrl = hc.FunctionGenerator(awg, self, "RF Generator")

        self.psu = hc_back.TDKL_GenH("TCPIP0::192.168.1.19::INSTR")
        awg.psu = debug
        self.psu_ctrl = hc.MultiPowerSupply(
            self.psu, self, [1], "TDK Lambda (RF Vin)", "DEFAULT"
        )

        # Put instrument(s) in tab
        self.tab2_layout = QGridLayout()
        self.tab2_layout.addWidget(self.awg_ctrl, 0, 0)
        self.tab2_layout.addWidget(self.psu_ctrl, 0, 1)
        self.tab2.setLayout(self.tab2_layout)

        #####################################################################
        ######## Tab 3

        self.flow = hc_back.Alicat_M_Series("192.168.1.15")
        self.flow_ctrl = hc.FlowController(
            self.flow, self, "Flow Controller", "flowcontroller_state.json"
        )

        # Todo: linux-gpib is a dependency on some systems
        self.trig1 = hc_back.SRS_DG535("GPIB0::10::INSTR")
        self.trig1_ctrl = hc.DelayGenerator(self.trig1, self, "Trigger 1", "DEFAULT")

        self.trig2 = hc_back.SRS_DG535("GPIB0::15::INSTR")
        self.trig2_ctrl = hc.DelayGenerator(self.trig2, self, "Trigger 2", "DEFAULT")
        try:
            self.zmqtool = hc.ZMQConnectionTool(self, "ZMQ Input Tool", "tcp://*:5555")
        except Exception as e:
            print("ZMQConnection failed! ")
            print(e)

        self.ScanWidget = hc.ScanWidget(self, "Scan Control", True)
        self.ScanWidget.update_instruments()

        self.statustool = hc.StatusTool(self, "Connection Status")
        self.statustool.update_instruments()

        app.add_variable("FIL_AMPL_V", "5.0")  # Add a filament amplitude variable
        app.add_variable("DELAY_TIME_S", "7.5")  # Add a delay time variable
        app.add_variable("PULSE_TIME_S", "500e-6")  # Add a spark time variable
        app.add_macro(
            "Trigger",
            [
                "SET:Filament DAC:VOLT:FIL_AMPL",
                "CMD:Keysight Scope:SINGLE",
                "SET:Filament DAC:VOLT:0",
            ],
        )  # Add a trigger macro
        app.add_macro("Safe", ["CMD:PSU:ALL_OFF", "CMD:AWG:ALL_OFF"])
        app.add_macro("Wait_1s", ["FUNC:time:sleep:1"])

        self.run_tool = hc.MacroRunnerTool(
            self, "Macro Runner", ["Dynamic", "Trigger"], ["Run Macro", "Trigger Beam"],
        )
        self.run_tool.update_macros()

        self.ScanWidget.update_actions()

        # Put instrument(s) in tab
        self.tab3_layout = QGridLayout()
        self.tab3_layout.addWidget(self.flow_ctrl, 0, 0)
        self.tab3_layout.addWidget(self.trig1_ctrl, 1, 0)
        self.tab3_layout.addWidget(self.trig2_ctrl, 2, 0)
        self.tab3_layout.addWidget(self.zmqtool, 3, 0)
        self.tab3_layout.addWidget(self.ScanWidget, 0, 1)
        self.tab3_layout.addWidget(self.run_tool, 1, 1)
        self.tab3_layout.addWidget(self.statustool, 3, 1)
        self.tab3.setLayout(self.tab3_layout)

        #####################################################################
        ######## Set master window layout

        # self.grid = QGridLayout()
        # # self.grid.addWidget(self.scope_ctrl, 0, 0, 3, 3)
        # # self.grid.addWidget(self.flow_ctrl, 0, 3)
        # # self.grid.addWidget(self.trig1_ctrl, 1, 3)
        # # self.grid.addWidget(self.trig2_ctr, 2, 3)
        # # self.grid.addWidget(self.ScanWidget, 0, 4)
        # # self.grid.addWidget(self.statustool, 2, 4)
        # # self.grid.addWidget(self.awg_ctrl, 3, 0, 1, 1)
        # # self.grid.addWidget(self.psu_ctrl, 3, 1, 1, 1)
        # # self.grid.addWidget(self.zmqtool, 3, 3, 1, 1)
        # # self.grid.addWidget(self.run_tool, 1, 4)
        # # self.grid.addWidget(self.var_tool, 3, 4)
        # self.grid.addWidget(self.tabs, 0, 0)
        # self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.tabs)

        # ['macintosh', 'Windows', 'Fusion']
        self.app.setStyle(QStyleFactory.create("Fusion"))
        # self.app.setStyle(QStyleFactory.create("Windows"))

        self.show()

    def close(self):
        self.app.close()

        if log:
            with open("example_sts50.log", "w") as f:
                for item in self.app.log:
                    f.write("%s\n" % item)


def main():
    app = hc.App(dummy=dummy)
    ex = STS50Demo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
