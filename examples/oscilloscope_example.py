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

from hardware_control.Oscilloscope.hc_oscilloscope import OscilloscopeControl
from hardware_control.Oscilloscope.Key4000XSCPI import Key4000XSCPI

class ScopeDemo(QMainWindow):

    def __init__(self, app):
        super().__init__();
        self.app = app;

        self.setWindowTitle('Oscilloscope Demo')

        self.main_widget = QWidget(self)

        scpi_scope = Key4000XSCPI("TCPIP0::192.168.0.14::INSTR", False, True, True, "192.168.0.14", 5025);
        self.scope_ctrl = OscilloscopeControl(scpi_scope, "DEFAULT", True);

        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0);
        self.main_widget.setLayout(self.grid);

        self.setCentralWidget(self.main_widget);
        self.show()

    def close(self):
        self.scope_ctrl.close()


app = QApplication([]);
ex = ScopeDemo(app);
app.aboutToQuit.connect(ex.close)
sys.exit(app.exec_());
