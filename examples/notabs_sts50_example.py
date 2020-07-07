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

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout, QStyleFactory
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
if commands["--socket"]:
    connection_type = "socket"
else:
    connection_type = "visa"
debug = commands["--debug"]
log = commands["--log"]

from hardware_control.base import HC_App
from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope
from hardware_control.Oscilloscope.Key4000XCtrl import Key4000XCtrl
from hardware_control.FlowController.HC_FlowController import HC_FlowController
from hardware_control.FlowController.AlicatMSeriesCtrl import AlicatMSeriesCtrl
from hardware_control.PulseGenerator.HC_PulseGen import HC_PulseGen
from hardware_control.PulseGenerator.SRSDG535Ctrl import SRSDG535Ctrl
from hardware_control.FunctionGenerator.HC_FunctionGenerator import HC_FunctionGenerator
from hardware_control.FunctionGenerator.Key33500BCtrl import Key33500BCtrl
from hardware_control.PowerSupply.HC_MultiPowerSupply import HC_MultiPowerSupply
from hardware_control.PowerSupply.TDKLGenHCtrl import TDKLGenHCtrl
from hardware_control.widgets import (
    HC_ZMQConnectionTool,
    HC_MacroRunnerTool,
    HC_VariableEditTool,
    HC_ScanTool,
    HC_StatusTool,
)


class STS50Demo(QMainWindow):
    def __init__(self, app, connection_type: str):
        super().__init__()
        self.app = app

        self.setWindowTitle("Oscilloscope Demo")

        self.main_widget = QWidget(self)

        scpi_scope = Key4000XCtrl(
            "TCPIP0::192.168.0.14::INSTR",
            dummy,
            True,
            connection_type,
            "192.168.0.14",
            5025,
        )
        self.scope_ctrl = HC_Oscilloscope(scpi_scope, self, "Keysight", "DEFAULT", True)

        # awg = Key33500BCtrl("Some-address-goes-here", dummy, True, connection_type, "192.168.0.18", 5025)
        awg = Key33500BCtrl(
            "USB0::0x0957::0x2907::MY52500624::INSTR",
            dummy,
            True,
            connection_type,
            "192.168.0.18",
            5025,
        )
        self.awg_ctrl = HC_FunctionGenerator(
            awg, self, "RF Generator", "DEFAULT", True, 1
        )

        self.psu = TDKLGenHCtrl("TCPIP0::192.168.1.19::INSTR", dummy)
        self.psu_ctrl = HC_MultiPowerSupply(
            self.psu, self, [1], "TDK Lambda (RF Vin)", "DEFAULT"
        )

        self.flow = AlicatMSeriesCtrl("192.168.0.15", True, True)
        self.flow_ctrl = HC_FlowController(
            self.flow, self, "Flow Controller", "flowcontroller_state.json", True
        )

        self.trig1 = SRSDG535Ctrl("GPIB0::10::INSTR", True, True)
        self.trig1_ctrl = HC_PulseGen(self.trig1, self, "Trigger 1", "DEFAULT", True)

        self.trig2 = SRSDG535Ctrl("GPIB0::15::INSTR", True, True)
        self.trig2_ctr = HC_PulseGen(self.trig2, self, "Trigger 2", "DEFAULT", True)

        self.zmqtool = HC_ZMQConnectionTool(self, "ZMQ Input Tool", "tcp://*:5555")

        self.scantool = HC_ScanTool(self, "Scan Control", "DEFAULT", True)
        self.scantool.update_instruments()

        self.statustool = HC_StatusTool(self, "Connection Status", "DEFAULT", True)
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

        self.run_tool = HC_MacroRunnerTool(
            self,
            "Macro Runner",
            {"Dynamic": "Run Macro", "Trigger": "Trigger Beam"},
            {},
        )
        self.run_tool.update_macros()

        self.var_tool = HC_VariableEditTool(
            self,
            "Application Variable Editor",
            {
                "Dynamic": "Value:",
                "FIL_AMPL_V": "Filament Amplitude:",
                "DELAY_TIME_S": "Filament Heating Time:",
            },
        )
        self.var_tool.update_variables()

        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0, 3, 3)
        self.grid.addWidget(self.flow_ctrl, 0, 3)
        self.grid.addWidget(self.trig1_ctrl, 1, 3)
        self.grid.addWidget(self.trig2_ctr, 2, 3)
        self.grid.addWidget(self.scantool, 0, 4)
        self.grid.addWidget(self.statustool, 2, 4)
        self.grid.addWidget(self.awg_ctrl, 3, 0, 1, 1)
        self.grid.addWidget(self.psu_ctrl, 3, 1, 1, 1)
        self.grid.addWidget(self.zmqtool, 3, 3, 1, 1)
        self.grid.addWidget(self.run_tool, 1, 4)
        self.grid.addWidget(self.var_tool, 3, 4)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)

        # ['macintosh', 'Windows', 'Fusion']
        # self.app.setStyle(QStyleFactory.create("Fusion"))
        self.app.setStyle(QStyleFactory.create("Windows"))

        self.show()

    def close(self):
        self.app.close()

        if log:
            with open("example_sts50.log", "w") as f:
                for item in self.app.log:
                    f.write("%s\n" % item)


def main():
    app = HC_App(dummy=dummy)
    ex = STS50Demo(app, connection_type)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
