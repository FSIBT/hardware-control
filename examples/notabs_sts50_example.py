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


class STS50Demo(hc.MainWindow):
    def __init__(self, app, connection_type: str):
        super().__init__(app)

        self.setWindowTitle("Oscilloscope Demo")

        self.main_widget = QWidget(self)

        scpi_scope = hc_back.Keysight_4000X("TCPIP0::192.168.0.14::INSTR",)
        self.scope_ctrl = hc.Oscilloscope(app, scpi_scope, "Keysight")

        # awg = Key33500BCtrl("Some-address-goes-here", dummy, True, connection_type, "192.168.0.18", 5025)
        awg = hc_back.Keysight_33500B("USB0::0x0957::0x2907::MY52500624::INSTR",)
        self.awg_ctrl = hc.FunctionGenerator(app, awg, "RF Generator", 1)

        self.psu = hc_back.TDKL_GenH("TCPIP0::192.168.1.19::INSTR")
        self.psu_ctrl = hc.MultiPowerSupply(app, self.psu, [1], "TDK Lambda (RF Vin)")

        self.flow = hc_back.Alicat_M_Series("192.168.0.15")
        self.flow_ctrl = hc.FlowController(
            self.flow, self, "Flow Controller", "flowcontroller_state.json"
        )

        self.trig1 = hc_back.SRS_DG535("GPIB0::10::INSTR")
        self.trig1_ctrl = hc.DelayGenerator(app, self.trig1, "Trigger 1")

        self.trig2 = hc_back.SRS_DG535("GPIB0::15::INSTR")
        self.trig2_ctr = hc.DelayGenerator(app, self.trig2, "Trigger 2")

        self.zmqtool = hc.ZMQConnectionTool(app, "ZMQ Input Tool", "tcp://*:5555")

        self.ScanWidget = hc.ScanWidget(app, "Scan Control")
        self.ScanWidget.update_instruments()

        self.statustool = hc.StatusTool(app, "Connection Status")
        self.statustool.update_instruments()

        app.add_macro("Safe", ["CMD:PSU:ALL_OFF", "CMD:AWG:ALL_OFF"])

        self.run_tool = hc.MacroRunnerTool(
            app, "Macro Runner", ["Dynamic"], ["Run Macro"]
        )

        self.run_tool.update_macros()

        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0, 3, 3)
        self.grid.addWidget(self.flow_ctrl, 0, 3)
        self.grid.addWidget(self.trig1_ctrl, 1, 3)
        self.grid.addWidget(self.trig2_ctr, 2, 3)
        self.grid.addWidget(self.ScanWidget, 0, 4)
        self.grid.addWidget(self.statustool, 2, 4)
        self.grid.addWidget(self.awg_ctrl, 3, 0, 1, 1)
        self.grid.addWidget(self.psu_ctrl, 3, 1, 1, 1)
        self.grid.addWidget(self.zmqtool, 3, 3, 1, 1)
        self.grid.addWidget(self.run_tool, 1, 4)
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
    app = hc.App(dummy=dummy)
    ex = STS50Demo(app, connection_type)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
