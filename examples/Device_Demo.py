"""Device demo

Usage:
  device_demo [--dummy] [--socket] [--debug]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
  --debug    allow debug print statements
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
)
import sys
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
use_sockets = commands["--socket"]
debug = commands["--debug"]

from hardware_control.base import HC_App
from hardware_control.TemplateDeviceType.DeviceBackend import DeviceBackend
from hardware_control.TemplateDeviceType.HC_DeviceType import HC_DeviceType


class Demo(QMainWindow):
    def __init__(self, app, use_sockets: bool):
        super().__init__()
        self.app = app
        #set title of window
        self.setWindowTitle("Demo")
        #this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        ##### Add Device(s)
        #add a Backend
        demo = DeviceBackend("TCPIP::192.168.1.20::1470::SOCKET", dummy)
        #add a HC. The corresponding backend, MainWidget and more information are handed over
        self.demo_ctrl = HC_DeviceType(
            demo, self, [1, 2, 3], "Power Supply Unit", "DEFAULT"
        )

        ##### Add above HC to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.demo_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.psu_ctrl.close()


def main(argv):
    app = HC_App([])
    ex = Demo(app, use_sockets)         #Change accordingly
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main(sys.argv[1:])
