#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oscilloscope_example to control the hardware_control test stand

Usage:
  oscilloscope_example [--dummy]
  oscilloscope_example [--socket]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of pyvisa
"""
from matplotlib import pyplot as plt
import seaborn as sns
import sys

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QIntValidator, QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSizePolicy,
                             QHBoxLayout, QVBoxLayout, QLabel, QCheckBox,
                             QMessageBox, QWidget, QLineEdit,
                             QPushButton, QAction, QGridLayout)
import sys
from docopt import docopt

commands = docopt(__doc__)
dummy = commands['--dummy']
use_sockets = commands['--socket']

from hardware_control.QHelper import QHardwareApp
from hardware_control.Oscilloscope.QOscilloscope import QOscilloscope
from hardware_control.Oscilloscope.Key4000XCtrl import Key4000XCtrl
from hardware_control.FlowController.QFlowController import QFlowController
from hardware_control.FlowController.AlicatMSeriesCtrl import AlicatMSeriesCtrl
from hardware_control.PulseGenerator.QPulseGen import QPulseGen
from hardware_control.PulseGenerator.SRSDG535Ctrl import SRSDG535Ctrl
from hardware_control.ScanTool.HScanTool import HScanTool
from hardware_control.ConnectionStatusTool.HStatusTool import HStatusTool
from hardware_control.FunctionGenerator.HFunctionGenerator import HFunctionGenerator
from hardware_control.FunctionGenerator.Key_Ctrl import Key_Ctrl

class STS50Demo(QMainWindow):

    def __init__(self, app, use_sockets:bool):
        super().__init__();
        self.app = app;

        self.setWindowTitle('Oscilloscope Demo');

        self.main_widget = QWidget(self);

        scpi_scope = Key4000XCtrl("TCPIP0::192.168.0.14::INSTR", dummy, True, use_sockets, "192.168.0.14", 5025);
        self.scope_ctrl = QOscilloscope(scpi_scope, self, "Keysight", "DEFAULT", True);

        awg = Key_Ctrl("Some-address-goes-here", dummy, True, use_sockets, "192.168.0.18", 5025);
        self.awg_ctrl = HFunctionGenerator(awg, self, "RF Generator", "DEFAULT", True, 2);

        self.flow = AlicatMSeriesCtrl("192.168.0.15", dummy, True);
        self.flow_ctrl = QFlowController(self.flow, self, "Flow Controller", "flowcontroller_state.json", True);

        self.trig1 = SRSDG535Ctrl("GPIB0::10::INSTR", dummy, True);
        self.trig1_ctrl = QPulseGen(self.trig1, self, "Trigger 1", "DEFAULT", True);

        self.trig2 = SRSDG535Ctrl("GPIB0::15::INSTR", dummy, True);
        self.trig2_ctr = QPulseGen(self.trig2, self, "Trigger 2", "DEFAULT", True);

        self.scantool = HScanTool(self, "Scan Control", "DEFAULT", True);
        self.scantool.update_instruments();
        
        self.statustool = HStatusTool(self, "Connection Status", "DEFAULT", True);
        self.statustool.update_instruments();

        self.grid = QGridLayout();
        self.grid.addWidget(self.scope_ctrl, 0, 0, 3, 3);
        self.grid.addWidget(self.flow_ctrl, 0, 3);
        self.grid.addWidget(self.trig1_ctrl, 1, 3);
        self.grid.addWidget(self.trig2_ctr, 2, 3);
        self.grid.addWidget(self.scantool, 0, 4)
        self.grid.addWidget(self.statustool, 2, 4)
        self.grid.addWidget(self.awg_ctrl, 3, 0, 1, 1)
        self.main_widget.setLayout(self.grid);

        self.setCentralWidget(self.main_widget);
        self.show();

    def close(self):
        self.scope_ctrl.close();

def main(argv):
	app = QHardwareApp([]);
	ex = STS50Demo(app, use_sockets);
	app.aboutToQuit.connect(ex.close)
	sys.exit(app.exec_());

main(sys.argv[1:]);
