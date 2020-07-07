#!/usr/bin/env python3
"""oscilloscope_example to control the hardware_control test stand

Usage:
  sts50_example [--dummy] [--socket] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""

import logging

import sys, warnings
import time
from PyQt5.QtWidgets import QDoubleSpinBox, QStyleFactory, QTabWidget, QGroupBox
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
info = commands["--info"]
if commands["--socket"]:
    connection_type = "socket"
else:
    connection_type = "visa"
debug = commands["--debug"]
print_console = commands["--console"]

logfile_name = "hardware_control.log"

if debug:
    if print_console:
        logging.basicConfig(level=logging.DEBUG)
        print("Logger configured:\n\tLevel: Debug\n\tOutput: Console")
    else:
        logging.basicConfig(filename=logfile_name, level=logging.DEBUG)
        print(f"Logger configured:\n\tLevel: Debug\n\tOutput: {logfile_name}")
elif info:
    if print_console:
        logging.basicConfig(level=logging.INFO)
        print("Logger configured:\n\tLevel: Info\n\tOutput: Console")
    else:
        logging.basicConfig(filename=logfile_name, level=logging.INFO)
        print(f"Logger configured:\n\tLevel: Info\n\tOutput: {logfile_name}")
else:
    if print_console:
        logging.basicConfig(level=logging.WARNING)
        print("Logger configured:\n\tLevel: Warning\n\tOutput: Console")
    else:
        logging.basicConfig(filename=logfile_name, level=logging.WARNING)
        print(f"Logger configured:\n\tLevel: Warning\n\tOutput: {logfile_name}")

from hardware_control.base import HC_App, HC_MainWindow, Dataset
from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope
from hardware_control.Oscilloscope.Key4000XCtrl import Key4000XCtrl
from hardware_control.Oscilloscope.ZMQOscilloscopeCtrl import ZMQOscilloscopeCtrl
from hardware_control.FlowController.HC_FlowController import HC_FlowController
from hardware_control.FlowController.AlicatMSeriesCtrl import AlicatMSeriesCtrl
from hardware_control.DelayGenerator.HC_DelayGenerator import HC_DelayGenerator
from hardware_control.DelayGenerator.SRSDG535Ctrl import SRSDG535Ctrl

# from hardware_control.widgets.scan import HC_ScanTool
from hardware_control.FunctionGenerator.HC_FunctionGenerator import HC_FunctionGenerator
from hardware_control.FunctionGenerator.Key33500BCtrl import Key33500BCtrl
from hardware_control.PowerSupply.HC_MultiPowerSupply import *
from hardware_control.PowerSupply.TDKLGenHCtrl import TDKLGenHCtrl
from hardware_control.widgets import (
    HC_StatusTool,
    HC_ZMQConnectionTool,
    HC_LoggerTool,
    HC_MacroRunnerTool,
    HC_VariableEditTool,
)
from hardware_control.IOModule.HC_Read import HC_Read, HC_singleChannelRead
from hardware_control.IOModule.ADAM_6015 import Adam_6015
from hardware_control.PowerSupply.NI_DaX_PowerSupplyController import (
    NI_DaX_PowerSupplyController,
)


logger = logging.getLogger(__name__)

# handler = logging.FileHandler('sts50_example.log')
# handler.setLevel(logging.DEBUG)

# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)

# logger.addHandler(handler)

logger.info("STS50 Example Starting")

# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """oscilloscope_example to control the hardware_control test stand
#
# Usage:
#   oscilloscope_example [--dummy]
#   oscilloscope_example [--socket]
#
# Options:
#   --dummy    use dummy connection for instruments that return semi-random data
#              so that one run the program away from the test stand
#   --socket   use sockets instead of visa
# """
#
# import sys
#
# from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout
# from docopt import docopt
#
# commands = docopt(__doc__)
# dummy = commands["--dummy"]
# if commands["--socket"]:
#     connection_type = "socket"
# else:
#     connection_type = "visa"
#
# from hardware_control.base import HC_App, HC_MainWindow, Dataset
# from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope
# from hardware_control.Oscilloscope.Key4000XCtrl import Key4000XCtrl


class ScopeDemo(HC_MainWindow):
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        self.setWindowTitle("Oscilloscope Demo")

        self.main_widget = QWidget(self)

        scpi_scope = Key4000XCtrl("TCPIP0::192.168.0.14::INSTR", connection_type,)
        self.scope_ctrl = HC_Oscilloscope(scpi_scope, self, "Keysight")

        self.grid = QGridLayout()
        self.grid.addWidget(self.scope_ctrl, 0, 0)
        self.main_widget.setLayout(self.grid)

        self.setCentralWidget(self.main_widget)
        self.show()

    def close(self):
        self.scope_ctrl.close()


def main(argv):
    app = HC_App(dummy=dummy)
    ex = ScopeDemo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main(sys.argv[1:])
