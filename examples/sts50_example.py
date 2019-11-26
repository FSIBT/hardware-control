#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oscilloscope_example to control the hardware_control test stand

Usage:
  sts50_example [--dummy] [--socket] [--debug] [--log]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --socket   use sockets instead of visa
  --debug    allow debug print statements
  --log      save log file
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
    QDoubleSpinBox,
    QLabel,
    QCheckBox,
    QMessageBox,
    QWidget,
    QLineEdit,
    QPushButton,
    QAction,
    QGridLayout,
    QStyleFactory,
    QTabWidget,
    QAction,
    QGroupBox,
)
import sys
from docopt import docopt

commands = docopt(__doc__)
dummy = commands["--dummy"]
use_sockets = commands["--socket"]
debug = commands["--debug"]
log = commands["--log"]

from hardware_control.base import HC_App
from hardware_control.Oscilloscope.HC_Oscilloscope import HC_Oscilloscope
from hardware_control.Oscilloscope.Key4000XCtrl import Key4000XCtrl
from hardware_control.Oscilloscope.ZMQOscilloscopeCtrl import ZMQOscilloscopeCtrl
from hardware_control.FlowController.HC_FlowController import HC_FlowController
from hardware_control.FlowController.AlicatMSeriesCtrl import AlicatMSeriesCtrl
from hardware_control.PulseGenerator.HC_PulseGen import HC_PulseGen
from hardware_control.PulseGenerator.SRSDG535Ctrl import SRSDG535Ctrl
from hardware_control.ScanTool.HC_ScanTool import HC_ScanTool
from hardware_control.ConnectionStatusTool.HC_StatusTool import HC_StatusTool
from hardware_control.FunctionGenerator.HC_FunctionGenerator import HC_FunctionGenerator
from hardware_control.FunctionGenerator.Key33500BCtrl import Key33500BCtrl
from hardware_control.PowerSupply.HC_MultiPowerSupply import HC_MultiPowerSupply
from hardware_control.PowerSupply.CAEN14xxETCtrl import CAEN14xxETCtrl
from hardware_control.PowerSupply.TDKLGenHCtrl import TDKLGenHCtrl
from hardware_control.ZMQConnectionTool.HC_ZMQConnectionTool import HC_ZMQConnectionTool
from hardware_control.MacroRunnerTool.HC_MacroRunnerTool import HC_MacroRunnerTool
from hardware_control.VariableEditTool.HC_VariableEditTool import HC_VariableEditTool


class STS50Demo(QMainWindow):
    def __init__(self, app, use_sockets: bool):
        super().__init__()
        self.app = app

        self.setWindowTitle("STS-50 Control Panel")

        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab1_5 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()

        self.tabs.addTab(self.tab4, "Plasma Source")
        self.tabs.addTab(self.tab1, "Scope Tab")
        self.tabs.addTab(self.tab1_5, "Pico Tab")
        self.tabs.addTab(self.tab2, "Power Tab")
        self.tabs.addTab(self.tab3, "Other Tab")

        self.main_widget = QWidget(self)

        #####################################################################
        ######## Tab 1

        scpi_scope = Key4000XCtrl(
            "TCPIP0::192.168.1.14::INSTR",
            dummy,
            True,
            use_sockets,
            "192.168.1.14",
            5025,
        )
        self.scope_ctrl = HC_Oscilloscope(scpi_scope, self, "Keysight", "DEFAULT", True)

        # Put instrument(s) in tab
        self.tab1_layout = QGridLayout()
        self.tab1_layout.addWidget(self.scope_ctrl, 0, 0)
        self.tab1.setLayout(self.tab1_layout)

        #####################################################################
        ######## PicoTab

        self.pico = ZMQOscilloscopeCtrl("tcp://192.168.0.30:6000", dummy)
        self.pico_ctrl = HC_Oscilloscope(self.pico, self, "PicoScope", "DEFAULT", True)

        self.tab1_5_layout = QGridLayout()
        self.tab1_5_layout.addWidget(self.pico_ctrl, 0, 0)
        self.tab1_5.setLayout(self.tab1_5_layout)

        #####################################################################
        ######## Tab 2

        # awg = Key33500BCtrl("Some-address-goes-here", dummy, True, use_sockets, "192.168.0.18", 5025)
        awg = Key33500BCtrl(
            "TCPIP0::192.168.1.18::INSTR",
            dummy,
            True,
            use_sockets,
            "192.168.1.18",
            5025,
        )  # "USB0::0x0957::0x2907::MY52500624::INSTR"
        awg.debug = debug
        self.awg_ctrl = HC_FunctionGenerator(
            awg, self, "RF Generator", "DEFAULT", True, 1
        )

        self.psu = TDKLGenHCtrl("TCPIP0::192.168.1.19::INSTR", dummy)
        awg.psu = debug
        self.psu_ctrl = HC_MultiPowerSupply(
            self.psu, self, [1], "TDK Lambda (RF Vin)", "DEFAULT"
        )

        # Put instrument(s) in tab
        self.tab2_layout = QGridLayout()
        self.tab2_layout.addWidget(self.awg_ctrl, 0, 0)
        self.tab2_layout.addWidget(self.psu_ctrl, 0, 1)
        self.tab2.setLayout(self.tab2_layout)

        #####################################################################
        ######## Tab 3

        self.flow = AlicatMSeriesCtrl("192.168.1.15", dummy, True)
        self.flow_ctrl = HC_FlowController(
            self.flow, self, "Flow Controller", "flowcontroller_state.json", True
        )

        # Todo: crashes if ZMQ address already in use. Add try-except

        # Todo: linux-gpib is a dependency on some systems
        self.trig1 = SRSDG535Ctrl("GPIB0::10::INSTR", dummy, True)
        self.trig1.debug = debug
        self.trig1_ctrl = HC_PulseGen(self.trig1, self, "Trigger 1", "DEFAULT", True)

        self.trig2 = SRSDG535Ctrl("GPIB0::15::INSTR", dummy, True)
        self.trig2.debug = debug
        self.trig2_ctrl = HC_PulseGen(self.trig2, self, "Trigger 2", "DEFAULT", True)

        self.zmqtool = HC_ZMQConnectionTool(self, "ZMQ Input Tool", "tcp://*:5555")

        self.scantool = HC_ScanTool(self, "Scan Control", "DEFAULT", True)
        self.scantool.update_instruments()

        self.statustool = HC_StatusTool(self, "Connection Status", "DEFAULT", True)
        self.statustool.update_instruments()

        app.add_variable("FIL_AMPL_V", "5.0")  # Add a filament amplitude variable
        app.add_variable("DELAY_TIME_S", "7.5")  # Add a delay time variable
        app.add_variable("PULSE_TIME_S", "500e-6")  # Add a spark time variable
        app.add_macro(
            "Trigger",
            [
                "SET:Filament DAC:VOLT:FIL_AMPL",
                "CMD:Keysight Scope:SINGLE",
                "SET:Filament DAC:VOLT:0",
            ],
        )  # Add a trigger macro
        app.add_macro("Safe", ["CMD:PSU:ALL_OFF", "CMD:AWG:ALL_OFF"])
        app.add_macro("Wait_1s", ["FUNC:time:sleep:1"])

        self.run_tool = HC_MacroRunnerTool(
            self,
            "Macro Runner",
            {"Dynamic": "Run Macro", "Trigger": "Trigger Beam"},
            {},
        )
        self.run_tool.update_macros()

        self.var_tool = HC_VariableEditTool(
            self,
            "Application Variable Editor",
            {
                "Dynamic": "Value:",
                "FIL_AMPL_V": "Filament Amplitude:",
                "DELAY_TIME_S": "Filament Heating Time:",
            },
        )
        self.var_tool.update_variables()

        self.scantool.update_macros()

        #####################################################################
        ######## Tab 3

        # self.source_frame = QFrame(self.)

        # Put instrument(s) in tab
        self.tab3_layout = QGridLayout()
        # self.tab3_layout.addWidget(self.flow_ctrl, 0, 0)
        self.tab3_layout.addWidget(self.trig1_ctrl, 1, 0)
        self.tab3_layout.addWidget(self.trig2_ctrl, 2, 0)
        self.tab3_layout.addWidget(self.zmqtool, 3, 0)
        # self.tab3_layout.addWidget(self.scantool, 0, 1)
        self.tab3_layout.addWidget(self.run_tool, 1, 1)
        self.tab3_layout.addWidget(self.var_tool, 2, 1)
        # self.tab3_layout.addWidget(self.statustool, 3, 1)
        self.tab3.setLayout(self.tab3_layout)

        #####################################################################
        ######## Custom Tab

        self.tab_sts_layout = QGridLayout()

        ########### High Voltage Panel
        #
        self.hv_panel = QGroupBox("High Voltage Control")
        self.hv_panel_layout = QGridLayout()
        #
        self.v_extrac_label = QLabel("Extraction Voltage - Set Point (V):")
        self.v_extrac_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.v_extrac_edit = QDoubleSpinBox()
        # self.v_extrac_edit.editingFinished.connect(lambda: self..comm.update_setting(f"CH{channel}_volts_div", self.v_div_edit.text()))
        self.v_extrac_edit.setValue(0)
        self.v_extrac_edit.setDecimals(1)
        self.v_extrac_edit.setSingleStep(100)
        #
        self.v_extrac_meas_label = QLabel("Measured Value:")
        self.v_extrac_meas_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.v_extrac_meas_readout = QLabel("---- V")
        self.v_extrac_meas_readout.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        #
        #
        self.v_float_label = QLabel("Floating Rack Voltage  - Set Point (V):")
        self.v_float_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.v_float_edit = QDoubleSpinBox()
        # self.v_float_edit.editingFinished.connect(lambda: self..comm.update_setting(f"CH{channel}_volts_div", self.v_div_edit.text()))
        self.v_float_edit.setValue(0)
        self.v_float_edit.setDecimals(1)
        self.v_float_edit.setSingleStep(1000)
        #
        self.v_float_meas_label = QLabel("Measured Value:")
        self.v_float_meas_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.v_float_meas_readout = QLabel("---- V")
        self.v_float_meas_readout.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        #
        self.fil_ampl_label = QLabel("Filament 'On' Voltage (V):")
        self.fil_ampl_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.fil_ampl_edit = QDoubleSpinBox()
        # self.fil_ampl_edit.editingFinished.connect(lambda: self..comm.update_setting(f"CH{channel}_volts_div", self.v_div_edit.text()))
        self.fil_ampl_edit.setValue(0)
        self.fil_ampl_edit.setDecimals(2)
        self.fil_ampl_edit.setSingleStep(0.5)
        #
        #
        self.hv_panel_layout.addWidget(self.v_extrac_label, 0, 0)
        self.hv_panel_layout.addWidget(self.v_extrac_edit, 0, 1)
        self.hv_panel_layout.addWidget(self.v_extrac_meas_label, 0, 2)
        self.hv_panel_layout.addWidget(self.v_extrac_meas_readout, 0, 3)
        self.hv_panel_layout.addWidget(self.v_float_label, 1, 0)
        self.hv_panel_layout.addWidget(self.v_float_edit, 1, 1)
        self.hv_panel_layout.addWidget(self.v_float_meas_label, 1, 2)
        self.hv_panel_layout.addWidget(self.v_float_meas_readout, 1, 3)
        self.hv_panel.setLayout(self.hv_panel_layout)

        ########## Timing Panel
        #
        self.timing_panel = QGroupBox("Timing Panel")
        self.timing_panel_layout = QGridLayout()
        #
        self.t_heat_label = QLabel("Filament 'On' time (s):")
        self.t_heat_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.t_heat_edit = QDoubleSpinBox()
        # self.t_heat_edit.editingFinished.connect(lambda: self..comm.update_setting(f"CH{channel}_volts_div", self.v_div_edit.text()))
        self.t_heat_edit.setValue(7.5)
        self.t_heat_edit.setDecimals(2)
        self.t_heat_edit.setSingleStep(0.5)
        self.t_heat_edit.setMaximum(10e3)
        #
        self.t_delay_label = QLabel("Filament spark delay (s):")
        self.t_delay_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.t_delay_edit = QDoubleSpinBox()
        # self.t_delay_edit.editingFinished.connect(lambda: self..comm.update_setting(f"CH{channel}_volts_div", self.v_div_edit.text()))
        self.t_delay_edit.setValue(6.5)
        self.t_delay_edit.setDecimals(2)
        self.t_delay_edit.setSingleStep(0.5)
        self.t_delay_edit.setMaximum(10e3)
        #
        self.t_arc_label = QLabel("Filament arc duration (ms):")
        self.t_arc_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.t_arc_edit = QDoubleSpinBox()
        # self.t_arc_edit.editingFinished.connect(lambda: self..comm.update_setting(f"CH{channel}_volts_div", self.v_div_edit.text()))
        self.t_arc_edit.setValue(0.5)
        self.t_arc_edit.setDecimals(3)
        self.t_arc_edit.setMaximum(10e3)
        self.t_arc_edit.setSingleStep(0.5)
        #
        self.timing_panel_layout.addWidget(self.t_heat_label, 0, 0)
        self.timing_panel_layout.addWidget(self.t_heat_edit, 0, 1)
        self.timing_panel_layout.addWidget(self.t_delay_label, 1, 0)
        self.timing_panel_layout.addWidget(self.t_delay_edit, 1, 1)
        self.timing_panel_layout.addWidget(self.t_arc_label, 2, 0)
        self.timing_panel_layout.addWidget(self.t_arc_edit, 2, 1)
        self.timing_panel.setLayout(self.timing_panel_layout)

        ######## Set Tab Layout
        #
        self.tab_sts_layout.addWidget(self.hv_panel, 0, 0, 2, 4)
        self.tab_sts_layout.addWidget(self.timing_panel, 2, 0, 2, 2)
        self.tab_sts_layout.addWidget(self.flow_ctrl, 2, 2, 2, 2)
        self.tab4.setLayout(self.tab_sts_layout)

        #####################################################################
        ######## Add Menu Bar

        self.bar = self.menuBar()  # self.menuBar() is a function in QMainWindow

        ###### File menu
        #
        self.file_menu = self.bar.addMenu("File")
        self.file_menu.triggered[QAction].connect(self.process_file_menu)
        #
        self.save_state_act = QAction("Save Instrument States", self)
        self.save_state_act.setShortcut("Ctrl+Shift+S")
        self.file_menu.addAction(self.save_state_act)
        #
        self.save_data_act = QAction("Save App Variables", self)
        self.save_data_act.setShortcut("Ctrl+S")
        self.file_menu.addAction(self.save_data_act)
        #
        self.file_menu.addSeparator()
        #
        self.close_act = QAction("Close Window", self)
        self.close_act.setShortcut("Ctrl+W")
        self.file_menu.addAction(self.close_act)

        ####### Instrument Menu
        #
        self.instr_menu = self.bar.addMenu("Instrument")
        self.instr_menu.triggered[QAction].connect(self.process_instr_menu)
        #
        self.sync_from_ui_act = QAction("Sync from UI", self)
        self.instr_menu.addAction(self.sync_from_ui_act)
        #
        self.sync_from_instr_act = QAction("Sync from Instrument", self)
        self.instr_menu.addAction(self.sync_from_instr_act)
        #
        self.sync_from_file_act = QAction("Sync from File", self)
        self.instr_menu.addAction(self.sync_from_file_act)
        #
        self.instr_menu.addSeparator()
        #
        self.print_addresses_act = QAction("Print Addresses", self)
        self.instr_menu.addAction(self.print_addresses_act)

        ####### Scripting Menu
        #
        self.scripting_menu = self.bar.addMenu("Scripting")
        self.scripting_menu.triggered[QAction].connect(self.process_scripting_menu)
        #
        self.run_command_act = QAction("Run Command", self)
        self.run_command_act.setShortcut("Ctrl+R")
        self.scripting_menu.addAction(self.run_command_act)
        #
        self.run_script_act = QAction("Run Macro")
        self.scripting_menu.addAction(self.run_script_act)
        #
        self.scripting_menu.addSeparator()
        #
        self.add_macro_act = QAction("Add Macro")
        self.scripting_menu.addAction(self.add_macro_act)
        #
        self.add_variable_act = QAction("Add Variable")
        self.scripting_menu.addAction(self.add_variable_act)
        #
        self.scripting_menu.addSeparator()
        #
        self.show_variables_act = QAction("Show Variables")
        self.scripting_menu.addAction(self.show_variables_act)

        #####################################################################
        ######## Set master window layout

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.tabs, 0, 0, 3, 1)
        self.master_layout.addWidget(self.scantool, 0, 1)
        self.master_layout.addWidget(self.statustool, 1, 1)

        self.main_widget = QWidget(self)
        self.main_widget.setLayout(self.master_layout)
        self.setCentralWidget(self.main_widget)

        # ['macintosh', 'Windows', 'Fusion']
        # self.app.setStyle(QStyleFactory.create("Fusion"))
        # self.app.setStyle(QStyleFactory.create("Windows"))

        self.show()

    def close(self):
        print("Closing")
        self.app.close()

        if log:
            with open("example_sts50.log", "w") as f:
                for item in self.app.log:
                    f.write("%s\n" % item)

    def process_file_menu(self, q):

        if q.text() == "Save Instrument States":  # TODO: impliment
            print("This is where I save a state")
        elif q.text() == "Save App Variables":  # TODO: impliment
            print("This is where I save a state")
        elif q.text() == "Close Window":
            self.close()
            sys.exit(0)
        else:
            print("Error: function not supported")

    def process_instr_menu(self, q):

        if q.text() == "Sync from Instrument":  # TODO: impliment
            print("Not implimented")
            # Todo: impliment sync from instr
        elif q.text() == "Sync from UI":  # TODO: impliment
            print("Not implimented")
            # Todo: impliment sync from ui
        elif q.text() == "Sync from File":  # TODO: impliment
            print("Not implimented")
            # Todo: impliment sync from file
        else:
            print("Error: function not supported")

    def process_scripting_menu(self, q):
        if q.text() == "Run Command":  # TODO: impliment
            print("Not implimented")
        elif q.text() == "Run Macro":  # TODO: impliment
            print("Not implimented")
        elif q.text() == "Add Variable":  # TODO: impliment
            print("Not implimented")
        elif q.text() == "Add Macro":  # TODO: impliment
            print("Not implimented")
        elif q.text() == "Show Variables":  # TODO: impliment
            print("Not implimented")
        elif q.text() == "Show Macros":  # TODO: impliment
            print("Not implimented")
        else:
            print("Error: function not supported")


def main(argv):
    app = HC_App([])
    app.print_debug = debug
    ex = STS50Demo(app, use_sockets)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main(sys.argv[1:])
