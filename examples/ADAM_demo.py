"""Device demo

Usage:
  device_demo [--dummy] [--socket] [--debug]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
  --debug    allow debug print statements
"""

from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
use_sockets = commands["--socket"]
debug = commands["--debug"]

import sys
from PyQt5.QtWidgets import QMainWindow, QWidget, QGridLayout


from hardware_control.base import HC_App
from hardware_control.Adam.HC_ADAM import HC_ADAM
from hardware_control.Adam.ADAM_6015 import Adam_6015 as Adam


class Demo(QMainWindow):
    def __init__(self, app, use_sockets: bool):
        super().__init__()
        self.app = app
        # set title of window
        self.setWindowTitle("Demo")
        # this is the main widget, actual device widgets are added to it
        self.main_widget = QWidget(self)

        ##### Add Device(s)
        # add a Backend  with its Visa Adress
        demo = Adam("192.168.1.25:1025", self.app.dummy)
        # add a HC. The corresponding backend, MainWidget and more information are handed over
        self.demo_ctrl = HC_ADAM(
            demo,
            self,
            [1, 5, 9, 4],
            ["HeatPower", "Channel5", "LOX", "AnOtherChannel"],
            "Demo Device Unit",
            "DEFAULT",
        )

        ##### Add above HC to the main Widget
        self.grid = QGridLayout()
        self.grid.addWidget(self.demo_ctrl, 1, 1)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.demo_ctrl.close()


def main():
    app = HC_App([], dummy=dummy)
    ex = Demo(app, use_sockets)  # Change accordingly
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
