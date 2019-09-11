#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flowcontroller to control the hardware_control test stand

Usage:
  flowcontroller_example [--dummy]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
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

from hardware_control.PulseGenerator.hc_pulsegen import PulseGenControl
from hardware_control.PulseGenerator.SRSDG535Int import SRSDG535Int

from docopt import docopt

commands = docopt(__doc__)
dummy = commands['--dummy']

class PuslseGenDemo(QMainWindow):

    def __init__(self, app):
        super().__init__();
        self.app = app;

        self.setWindowTitle('Flow Controller Demo')

        self.main_widget = QWidget(self);

        self.instr = SRSDG535Int("GPIB0::10::INSTR", dummy, True);
        self.instr_ctrl = PulseGenControl(self.instr, "DEFAULT", True);

        self.grid = QGridLayout();
        self.grid.addWidget(self.instr_ctrl, 0, 0);
        self.main_widget.setLayout(self.grid);

        self.setCentralWidget(self.main_widget);
        self.show();

    def close(self):
        self.instr_ctrl.close()

app = QApplication([]);
ex = PuslseGenDemo(app);
app.aboutToQuit.connect(ex.close)
sys.exit(app.exec_());
