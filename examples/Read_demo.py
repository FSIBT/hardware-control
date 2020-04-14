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
from hardware_control.IOModule.ADAM_6015 import Adam_6015
from hardware_control.IOModule.HC_Read import HC_Read


class Read_Demo(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        # set title of window
        self.setWindowTitle("Demo")
        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        ##### Add Device(s)
        # add a Backend  with its Visa Adress
        demo = Adam_6015("192.168.1.25", dummy)
        # add a HC. The corresponding backend, MainWidget and more information are handed over
        self.demo_ctrl = HC_Read(
            demo,
            self,
            [0, 4, 5, 6],
            ["HeatPower :", "Channel4 :", "LOX5 :", "AnOtherChannel6 :"],
            "TEMP",
            "(C)",
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
    ex = Read_Demo(app)  # Change accordingly
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
