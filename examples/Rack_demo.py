"""Device demo

Usage:
  device_demo [--dummy] [--socket] [--debug]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
"""

import sys

from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
debug = commands["--debug"]

from hardware_control.base import HC_App
from hardware_control.TemplateDeviceType.DeviceBackend import DeviceBackend
from hardware_control.TemplateDeviceType.HC_DeviceType import HC_DeviceType


class Rack_Demo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        # set title of window
        self.setWindowTitle("Rack Demo")
        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        ##### Add Device(s)
        # add a Backend
        demo = DeviceBackend("TCPIP::000.000.000.000::1234::SOCKET", dummy)
        # add a HC. The corresponding backend, MainWidget and more information are handed over
        self.demo_ctrl = HC_DeviceType(
            demo, self, [1, 2, 3, 4], "Demo Device Unit", "DEFAULT"
        )

        ##### Add above HC to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.demo_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    #
    def close(self):
        self.demo_ctrl.close()


def main():
    app = HC_App(dummy=dummy)
    ex = Rack_Demo(app)  # Change accordingly
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
