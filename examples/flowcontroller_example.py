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

from hardware_control.flowcontroller.hc_flowcontroller import FlowControllerControl
from hardware_control.flowcontroller.AlicatSCPI import AlicatSCPI

class FlowControllerDemo(QMainWindow):

    def __init__(self, app):
        super().__init__();
        self.app = app;

        self.setWindowTitle('Flow Controller Demo')

        self.main_widget = QWidget(self)

        self.instr = AlicatSCPI("TCPIP0::192.168.0.xx::INSTR", True, True);
        self.instr_ctrl = FlowControllerControl(self.instr, "flowcontroller_state.json", True);

        self.grid = QGridLayout()
        self.grid.addWidget(self.instr_ctrl, 0, 0);
        self.main_widget.setLayout(self.grid);

        self.setCentralWidget(self.main_widget);
        self.show()

    def close(self):
        self.instr_ctrl.close()

app = QApplication([]);
ex = FlowControllerDemo(app);
app.aboutToQuit.connect(ex.close)
sys.exit(app.exec_());
