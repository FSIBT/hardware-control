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
from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSizePolicy,
                             QHBoxLayout, QVBoxLayout, QLabel, QCheckBox,
                             QMessageBox, QWidget, QLineEdit,
                             QPushButton, QAction, QGridLayout)
import sys
from docopt import docopt

commands = docopt(__doc__)
dummy = commands['--dummy']
use_sockets = commands['--socket']

from hardware_control.Oscilloscope.hc_oscilloscope import OscilloscopeControl
from hardware_control.Oscilloscope.Key4000XSCPI import Key4000XSCPI
from hardware_control.FlowController.hc_flowcontroller import FlowControllerControl
from hardware_control.FlowController.AlicatSCPI import AlicatSCPI
from hardware_control.PulseGenerator.hc_pulsegen import PulseGenControl
from hardware_control.PulseGenerator.SRSDG535Int import SRSDG535Int

class STS50Demo(QMainWindow):

    def __init__(self, app, use_sockets:bool):
        super().__init__();
        self.app = app;

        self.setWindowTitle('Oscilloscope Demo');

        self.main_widget = QWidget(self);

        scpi_scope = Key4000XSCPI("TCPIP0::192.168.0.14::INSTR", dummy, True, use_sockets, "192.168.0.14", 5025);
        self.scope_ctrl = OscilloscopeControl(scpi_scope, "DEFAULT", True);

        self.flow = AlicatSCPI("192.168.0.15", dummy, True);
        self.flow_ctrl = FlowControllerControl(self.flow, "flowcontroller_state.json", True);

        self.trig1 = SRSDG535Int("GPIB0::10::INSTR", dummy, True);
        self.trig1_ctrl = PulseGenControl(self.trig1, "DEFAULT", True);

        self.trig2 = SRSDG535Int("GPIB0::15::INSTR", dummy, True);
        self.trig2_ctr = PulseGenControl(self.trig2, "DEFAULT", True);

        self.grid = QGridLayout();
        self.grid.addWidget(self.scope_ctrl, 0, 0, 3, 1);
        self.grid.addWidget(self.flow_ctrl, 0, 1);
        self.grid.addWidget(self.trig1_ctrl, 1, 1);
        self.grid.addWidget(self.trig2_ctr, 2, 1);
        self.main_widget.setLayout(self.grid);

        self.setCentralWidget(self.main_widget);
        self.show();

    def close(self):
        self.scope_ctrl.close();

def main(argv):
	app = QApplication([]);
	ex = STS50Demo(app, use_sockets);
	app.aboutToQuit.connect(ex.close)
	sys.exit(app.exec_());

main(sys.argv[1:]);
