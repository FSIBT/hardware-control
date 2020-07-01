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
    loglevel = logging.DEBUG
    loglevelname = "Debug"
elif info:
    loglevel = logging.INFO
    loglevelname = "Info"
else:
    loglevel = logging.WARNING
    loglevelname = "Warning"

from hardware_control.base import HC_App, HC_MainWindow, Dataset
from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope
from hardware_control.Oscilloscope.Key4000XCtrl import Key4000XCtrl
from hardware_control.Oscilloscope.ZMQOscilloscopeCtrl import ZMQOscilloscopeCtrl
from hardware_control.FlowController.HC_FlowController import HC_FlowController
from hardware_control.FlowController.AlicatMSeriesCtrl import AlicatMSeriesCtrl
from hardware_control.DelayGenerator.HC_DelayGenerator import HC_DelayGenerator
from hardware_control.DelayGenerator.SRSDG535Ctrl import SRSDG535Ctrl
from hardware_control.ScanTool.HC_ScanTool import HC_ScanTool
from hardware_control.ConnectionStatusTool.HC_StatusTool import HC_StatusTool
from hardware_control.FunctionGenerator.HC_FunctionGenerator import HC_FunctionGenerator
from hardware_control.FunctionGenerator.Key33500BCtrl import Key33500BCtrl
from hardware_control.PowerSupply.HC_MultiPowerSupply import *
from hardware_control.PowerSupply.TDKLGenHCtrl import TDKLGenHCtrl
from hardware_control.ZMQConnectionTool.HC_ZMQConnectionTool import HC_ZMQConnectionTool
from hardware_control.MacroRunnerTool.HC_MacroRunnerTool import HC_MacroRunnerTool
from hardware_control.VariableEditTool.HC_VariableEditTool import HC_VariableEditTool
from hardware_control.IOModule.HC_Read import HC_Read, HC_singleChannelRead
from hardware_control.IOModule.ADAM_6015 import Adam_6015
from hardware_control.LoggerTool.HC_LoggerTool import HC_LoggerTool
from hardware_control.PowerSupply.NI_DaX_PowerSupplyController import (
    NI_DaX_PowerSupplyController,
)
from hardware_control.PlotTool.HC_PlotTool import HC_PlotTool
from hardware_control.PlotTool.HC_MiniPlotTool import HC_MiniPlotTool


logger = logging.getLogger(__name__)
hc_logger = logging.getLogger("hardware_control")

if print_console:
    logger.setLevel(level=loglevel)
    hc_logger.setLevel(level=loglevel)
    print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: Console")
else:
    logger.setLevel(level=loglevel)
    hc_logger.setLevel(level=loglevel)
    fh = logging.FileHandler(logfile_name)
    fh.setLevel(loglevel)
    hc_logger.addHandler(fh)

logger.info("STS50 Example Starting")


class STS50Demo(HC_MainWindow):
    def __init__(self, app):
        super().__init__(app)
        self.app = app

        self.setWindowTitle("STS-50 Control Panel")

        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab1_5 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tab6 = QWidget()

        self.tabs.addTab(self.tab4, "Plasma Source")
        self.tabs.addTab(self.tab1, "Oscilloscope")
        self.tabs.addTab(self.tab1_5, "Picoscope")
        self.tabs.addTab(self.tab2, "Power Supplies")
        self.tabs.addTab(self.tab3, "Aux 1")
        self.tabs.addTab(self.tab5, "Plots")
        self.tabs.addTab(self.tab6, "Datasets")

        self.main_widget = QWidget(self)

        #####################################################################
        ######## Tab 1

        scpi_scope = Key4000XCtrl(
            "TCPIP0::192.168.0.14::INSTR",  # Enter socket address as ip:port, ex: 192.168.0.14:5025
        )
        self.scope_ctrl = HC_Oscilloscope(scpi_scope, self, "Keysight")
        self.scope_ctrl.load_state("scope_state.json")

        # Put instrument(s) in tab
        self.tab1_layout = QGridLayout()
        self.tab1_layout.addWidget(self.scope_ctrl, 0, 0)
        self.tab1.setLayout(self.tab1_layout)

        #####################################################################
        ######## PicoTab

        self.pico = ZMQOscilloscopeCtrl("tcp://192.168.0.30:6000")
        self.pico_ctrl = HC_Oscilloscope(self.pico, self, "PicoScope")

        self.tab1_5_layout = QGridLayout()
        self.tab1_5_layout.addWidget(self.pico_ctrl, 0, 0)
        self.tab1_5.setLayout(self.tab1_5_layout)

        #####################################################################
        ######## Tab 2

        # awg = Key33500BCtrl("Some-address-goes-here", dummy, True, connection_type, "192.168.0.18", 5025)
        awg = Key33500BCtrl(
            "TCPIP0::192.168.0.18::INSTR",  # toDo "TCPIP0::192.168.1.18::INSTR"
        )  # "USB0::0x0957::0x2907::MY52500624::INSTR"
        self.awg_ctrl = HC_FunctionGenerator(awg, self, "RF Generator", 1)

        self.psu = TDKLGenHCtrl("TCPIP0::192.168.1.19::INSTR")
        self.psu_ctrl = HC_MultiPowerSupply(self.psu, self, [1], "TDK Lambda (RF Vin)",)

        # Put instrument(s) in tab
        self.tab2_layout = QGridLayout()
        self.tab2_layout.addWidget(self.awg_ctrl, 0, 0)
        self.tab2_layout.addWidget(self.psu_ctrl, 0, 1)
        self.tab2.setLayout(self.tab2_layout)

        #####################################################################
        ######## Tab 3

        self.temp = Adam_6015("192.168.1.25")
        self.temp_ctrl = HC_Read(
            self.temp,
            self,
            [0, 3, 5],
            ["Chamber", "Source", "Cabinet"],
            "TEMP",
            "K",
            "Temperature Instrument",
        )
        self.randomReadout = HC_singleChannelRead(
            self.temp_ctrl, 0, "Random Readout", "TEMP", "Unit"
        )

        self.flow = AlicatMSeriesCtrl("192.168.0.15")  # todo "192.168.1.15"
        self.flow_ctrl = HC_FlowController(self.flow, self, "Flow Controller")

        # Todo: linux-gpib is a dependency on some systems
        self.trig1 = SRSDG535Ctrl("GPIB0::10::INSTR")
        self.trig1_ctrl = HC_DelayGenerator(self.trig1, self, "Trigger 1")
        self.trig1_ctrl.load_state("Trigger1_state.json")
        self.trig1_ctrl.settings_to_UI()

        self.trig2 = SRSDG535Ctrl("GPIB0::15::INSTR")
        self.trig2_ctrl = HC_DelayGenerator(self.trig2, self, "Trigger 2")
        self.trig2_ctrl.load_state("Trigger2_state.json")
        self.trig2_ctrl.settings_to_UI()

        self.zmqtool = HC_ZMQConnectionTool(self, "ZMQ Input Tool", "tcp://*:5555")

        self.scantool = HC_ScanTool(self, "Scan Control", True)
        self.scantool.update_instruments()

        self.logtool = HC_LoggerTool(self, "Data Logger")
        self.logtool.update_groups()
        # self.logtool.update_instruments()

        self.PS_NIDaQCtrl = NI_DaX_PowerSupplyController()
        self.PS_NIDaQ = HC_MultiPowerSupply(self.PS_NIDaQCtrl, self, [1], "NIDAXTEST")

        self.statustool = HC_StatusTool(self, "Connection Status")
        self.statustool.update_instruments()

        app.function_handles["trigger_function"] = self.trigger_function
        app.function_handles["print_fil"] = self.print_fil

        app.add_variable("FIL_AMPL_V", "5.0")  # Add a filament amplitude variable
        app.add_variable("DELAY_TIME_S", "7.5")  # Add a delay time variable
        app.add_variable("PULSE_TIME_S", "500e-6")  # Add a spark time variable
        app.add_variable("SHOT_ID_NUM", "--")  # Add a shot number variable
        # app.add_macro(
        #     "Trigger",
        #     [
        #         "SET:Filament DAC:VOLT:FIL_AMPL",
        #         "CMD:Keysight Scope:SINGLE",
        #         "SET:Filament DAC:VOLT:0",
        #     ],
        # )  # Add a trigger macro
        app.add_macro("Trigger", ["FUNC:HANDLE:trigger_function"])
        # "Trigger", ["FUNC:VAR:SHOT_ID_NUM:10", "FUNC:UPDATE:MACRO_IND",],
        app.add_macro("Safe", ["CMD:PSU:ALL_OFF", "CMD:AWG:ALL_OFF"])
        app.add_macro("Wait_1s", ["FUNC:time:sleep:1"])
        app.add_macro("print_fil_ampl", ["FUNC:HANDLE:print_fil"])
        app.add_macro("MeasurementRequest", ["FUNC:DISP:str:MEAS:REQ"])

        # self.run_tool = HC_MacroRunnerTool(
        #     self,
        #     "Trigger Beam",
        #     {"Dynamic": "Run Macro", "Trigger": "Trigger Beam"},
        #     {"FIL_AMPL_V" : "Filament Amplitude: "},
        # )
        self.run_tool = HC_MacroRunnerTool(
            self,
            "Beam Trigger",
            {"Trigger": "Trigger Beam"},
            {"SHOT_ID_NUM": "Shot ID Number: "},
        )
        self.run_tool.update_macros()

        # Create Datasets
        self.app.data_sets["Autolog"] = Dataset("Autolog")
        self.app.data_sets["Autolog"].start_asynch(3)
        self.app.data_sets["Autolog"].add_instrument(self.PS_NIDaQ)
        self.app.data_sets["Autolog"].add_instrument(self.psu_ctrl)

        self.app.data_sets["High Voltage"] = Dataset("High Voltage")
        self.app.data_sets["High Voltage"].start_asynch(3)
        self.app.data_sets["High Voltage"].add_instrument(self.PS_NIDaQ, ["CH1_V_meas"])

        self.logtool.update_groups()
        self.logtool.set_group("Autolog")

        # self.var_tool = HC_VariableEditTool(
        #     self,
        #     "Application Variable Editor",
        #     {
        #         "Dynamic": "Value:",
        #         "FIL_AMPL_V": "Filament Amplitude:",
        #         "DELAY_TIME_S": "Filament Heating Time:",
        #     },
        # )
        # self.var_tool.update_variables()

        self.scantool.update_macros()

        #####################################################################
        ######## Tab 3

        # self.source_frame = QFrame(self.)

        # Put instrument(s) in tab
        self.tab3_layout = QGridLayout()
        # self.tab3_layout.addWidget(self.flow_ctrl, 0, 0)
        self.tab3_layout.addWidget(self.flow_ctrl, 1, 0, 2, 1)
        # self.tab3_layout.addWidget(self.trig2_ctrl, 2, 0)
        self.tab3_layout.addWidget(self.zmqtool, 3, 0, 2, 1)
        self.tab3_layout.addWidget(self.PS_NIDaQ, 2, 2, 3, 1)
        self.tab3_layout.addWidget(self.temp_ctrl, 1, 2)
        # self.tab3_layout.addWidget(self.scantool, 0, 1)
        # self.tab3_layout.addWidget(self.run_tool, 1, 1)
        # self.tab3_layout.addWidget(self.var_tool, 2, 1)

        # self.tab3_layout.addWidget(self.statustool, 3, 1)
        self.tab3.setLayout(self.tab3_layout)

        # #####################################################################
        # ######## Custom Tab

        self.tab_sts_layout = QGridLayout()

        self.tab_sts_layout.addWidget(self.trig1_ctrl, 0, 0)
        self.tab_sts_layout.addWidget(self.trig2_ctrl, 1, 0)
        self.tab4.setLayout(self.tab_sts_layout)

        # ########## Tab 5 - Experimental

        self.plot_wdgt1 = HC_PlotTool(self, "Floating Rack")

        self.tab5_layout = QGridLayout()
        self.tab5_layout.addWidget(self.plot_wdgt1, 0, 0)

        self.tab5.setLayout(self.tab5_layout)

        #####################################

        self.tab6_layout = QGridLayout()

        self.tab6_layout.addWidget(self.logtool, 0, 0)

        self.tab6.setLayout(self.tab6_layout)

        #####################################################################
        ######## Set master window layout

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.tabs, 0, 0, 3, 1)
        self.master_layout.addWidget(self.run_tool, 0, 1)
        self.master_layout.addWidget(self.scantool, 1, 1)
        self.master_layout.addWidget(self.statustool, 2, 1)
        # self.master_layout.addWidget(self.logtool, 2, 1)

        self.main_widget = QWidget(self)
        self.main_widget.setLayout(self.master_layout)
        self.setCentralWidget(self.main_widget)

        # ['macintosh', 'Windows', 'Fusion']
        self.app.setStyle(QStyleFactory.create("Fusion"))
        # self.app.setStyle(QStyleFactory.create("Windows"))

        self.show()

    def close(self):
        print("Closing")
        self.app.close()

        # if log:
        #     with open("example_sts50.log", "w") as f:
        #         for item in self.app.log:
        #             f.write("%s\n" % item)

    def trigger_function(self):

        self.app.variables["SHOT_ID_NUM"] = str(time.time())
        self.run_tool.update_indicators()

    def print_fil(self):

        print("Filament amplitude = " + str(self.app.variables["FIL_AMPL_V"]))


def main():
    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning
    )  # ToDo Not a solution
    app = HC_App(dummy=dummy)
    app.print_close_info = True

    ex = STS50Demo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
