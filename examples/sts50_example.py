#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oscilloscope_example to control the hardware_control test stand

Usage:
  sts50_example [--dummy] [--socket] [--debug] [--log]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of pyvisa
  --debug    allow debug print statements
  --log      save log file
"""

from matplotlib import pyplot as plt
import seaborn as sns
import sys

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QIntValidator, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QSizePolicy,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QMessageBox,
    QWidget,
    QLineEdit,
    QPushButton,
    QAction,
    QGridLayout,
    QStyleFactory,
)
import sys
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
use_sockets = commands["--socket"]
debug = commands["--debug"]
log = commands["--log"]

from hardware_control.base import HC_App
from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope
from hardware_control.Oscilloscope.Key4000XCtrl import Key4000XCtrl
from hardware_control.FlowController.HC_FlowController import HC_FlowController
from hardware_control.FlowController.AlicatMSeriesCtrl import AlicatMSeriesCtrl
from hardware_control.PulseGenerator.HC_PulseGen import HC_PulseGen
from hardware_control.PulseGenerator.SRSDG535Ctrl import SRSDG535Ctrl
from hardware_control.ScanTool.HC_ScanTool import HC_ScanTool
from hardware_control.ConnectionStatusTool.HC_StatusTool import HC_StatusTool
from hardware_control.FunctionGenerator.HC_FunctionGenerator import HC_FunctionGenerator
from hardware_control.FunctionGenerator.Key33500BCtrl import Key33500BCtrl


class STS50Demo(QMainWindow):
    def __init__(self, app, use_sockets: bool):
        super().__init__()
        self.app = app

        self.setWindowTitle("Oscilloscope Demo")

        self.main_widget = QWidget(self)

        scpi_scope = Key4000XCtrl(
            "TCPIP0::192.168.0.14::INSTR", True, True, use_sockets, "192.168.0.14", 5025
        )
        self.scope_ctrl = HC_Oscilloscope(
            scpi_scope, self, "Keysight", "DEFAULT", True, debug
        )

        # awg = Key33500BCtrl("Some-address-goes-here", dummy, True, use_sockets, "192.168.0.18", 5025)
        awg = Key33500BCtrl(
            "USB0::0x0957::0x2907::MY52500624::INSTR",
            dummy,
            True,
            use_sockets,
            "192.168.0.18",
            5025,
        )
        self.awg_ctrl = HC_FunctionGenerator(
            awg, self, "RF Generator", "DEFAULT", True, 1, debug
        )

        self.flow = AlicatMSeriesCtrl("192.168.0.15", True, True)
        self.flow_ctrl = HC_FlowController(
            self.flow, self, "Flow Controller", "flowcontroller_state.json", True
        )

        self.trig1 = SRSDG535Ctrl("GPIB0::10::INSTR", True, True)
        self.trig1_ctrl = HC_PulseGen(self.trig1, self, "Trigger 1", "DEFAULT", True)

        self.trig2 = SRSDG535Ctrl("GPIB0::15::INSTR", True, True)
        self.trig2_ctr = HC_PulseGen(self.trig2, self, "Trigger 2", "DEFAULT", True)

        self.scantool = HC_ScanTool(self, "Scan Control", "DEFAULT", True)
        self.scantool.update_instruments()

        self.statustool = HC_StatusTool(self, "Connection Status", "DEFAULT", True)
        self.statustool.update_instruments()

        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0, 3, 3)
        self.grid.addWidget(self.flow_ctrl, 0, 3)
        self.grid.addWidget(self.trig1_ctrl, 1, 3)
        self.grid.addWidget(self.trig2_ctr, 2, 3)
        self.grid.addWidget(self.scantool, 0, 4)
        self.grid.addWidget(self.statustool, 2, 4)
        self.grid.addWidget(self.awg_ctrl, 3, 0, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)

        # ['macintosh', 'Windows', 'Fusion']
        self.app.setStyle(QStyleFactory.create("Fusion"))

        self.show()

    def close(self):
        self.scope_ctrl.close()
        self.awg_ctrl.close()

        if log:
            with open("example_sts50.log", "w") as f:
                for item in self.app.log:
                    f.write("%s\n" % item)


def main(argv):
    app = HC_App([])
    ex = STS50Demo(app, use_sockets)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main(sys.argv[1:])
