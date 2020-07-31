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
import sys
from time import gmtime, strftime
import warnings

from PyQt5.QtWidgets import (
    QStyleFactory,
    QTabWidget,
    QGridLayout,
    QWidget,
    QSpacerItem,
    QSizePolicy,
    QGroupBox,
    QLabel,
    QLineEdit,
)
from PyQt5.QtGui import QIcon, QDoubleValidator
from docopt import docopt

from PyQt5 import QtCore
from hardware_control.base import HC_App, HC_MainWindow, Dataset
from hardware_control.Oscilloscope import (
    HC_Oscilloscope,
    Key4000XCtrl,
    ZMQOscilloscopeCtrl,
)
from hardware_control.FlowController import HC_FlowController, AlicatMSeriesCtrl
from hardware_control.DelayGenerator import HC_DelayGenerator, SRSDG535Ctrl
from hardware_control.FunctionGenerator import HC_FunctionGenerator, Key33500BCtrl
from hardware_control.PowerSupply import (
    HC_MultiPowerSupply,
    TDKLGenHCtrl,
    CAEN14xxETCtrl,
)
from hardware_control.IOModule import (
    HC_IOModule,
    read_channel_file,
    NI9000Ctrl,
    HC_Read,
    HC_singleChannelRead,
    ADAM6015Ctrl,
)
from hardware_control.widgets import (
    HC_ZMQConnectionTool,
    HC_MacroRunnerTool,
    HC_LoggerTool,
    HC_ScanTool,
    HC_PlotTool,
    HC_StatusTool,
    HC_Qtconsole,
    load_icon,
)


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
other_logfile_name = "other_hardware_control.log"

if debug:
    loglevel = logging.DEBUG
    loglevelname = "Debug"
elif info:
    loglevel = logging.INFO
    loglevelname = "Info"
else:
    loglevel = logging.WARNING
    loglevelname = "Warning"

logger = logging.getLogger(__name__)
# hc_logger = logging.getLogger("hardware_control")

# Create file or stream handler
format_str = "[%(asctime)s] %(name)s - %(levelname)s: %(message)s"
if print_console:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(format_str))
    handler.setLevel(loglevel)
    print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: Console")
else:
    handler = logging.FileHandler(logfile_name)
    handler.setFormatter(logging.Formatter(format_str))
    handler.setLevel(loglevel)
    print(f"Logger configured:\n\tLevel: {loglevelname}\n\tOutput: File")

# Clear all other handlers
loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
for name in logging.root.manager.loggerDict:

    lgr = logging.getLogger(name)
    lgr.propagate = False

    if "hardware_control" in name:
        lgr.setLevel(loglevel)
        lgr.handlers = []
        lgr.addHandler(handler)
    else:
        lgr.setLevel(logging.CRITICAL)
        lgr.handlers = []

# for lg in loggers:
#
#     if lg is logger or lg is hc_logger:
#         continue
#
#     lg.setLevel(logging.CRITICAL)
#     lg.handlers = []

# Add desired handlers
# hc_logger.setLevel(loglevel)
# hc_logger.handlers = []
# hc_logger.addHandler(handler)
logger.setLevel(loglevel)
logger.handlers = []
logger.addHandler(handler)

logger.info("STS50 Example Starting")


def init_with_JSON(obj):
    """
    This function is used by multiple instruments to sync the instrument state
    and backend once the instrument comes online.
    """

    obj.send_state()


def init_with_instrument(obj):
    """
    This function is used by multiple instruments to sync the instrument state
    and backend once the instrument comes online.
    """

    obj.read_state_from_backend()
    obj.settings_to_UI()


def init_osc_when_online(obj):
    """
    This function is used by the oscilloscope specifically to sync the instrument
    state and configure the oscilloscope when it comes online.
    """

    init_with_JSON(obj)

    obj.command("CONFIG_READ_WAVE")


def power_off(window):

    # Disable CAEN
    window.psu_caen_wdgt.update_setting("CH3_enable", "False")
    window.psu_caen_wdgt.update_setting("CH8_enable", "False")
    window.psu_caen_wdgt.settings_to_UI()

    # Disable RF Generator
    window.awg_ctrl.update_setting("CH1_enabled", "False")
    window.awg_ctrl.settings_to_UI()

    # Disable TDK Lambda
    window.psu_ctrl.update_setting("CH1_enabled", "False")
    window.psu_ctrl.settings_to_UI()

    # Shut off gas
    window.flow_ctrl.update_setting("rate", "0")
    window.flow_ctrl.settings_to_UI()

    # Shut off NI-DAQ Power Supplies
    window.iomod_usb_wdgt.update_setting("CHcDAQ1Mod1/ao0_analog_write", "0")
    window.iomod_usb_wdgt.update_setting("CHcDAQ1Mod1/ao1_analog_write", "0")
    window.iomod_float_wdgt.update_setting(
        "CHcDAQ9188-1AEF742Mod7/ao4_analog_write", "0"
    )
    window.iomod_usb_wdgt.settings_to_UI()
    window.iomod_float_wdgt.settings_to_UI()


def trigger_function(window):
    """
    This function is used by the app to describe the beam triggering sequence. It
    is called when the beam trigger button is pressed or the trigger macro is run.
    """

    # Update shot number and shot number widget
    window.app.variables["SHOT_ID_NUM"] = strftime("%H%M%S", gmtime())
    window.run_tool.update_indicators()

    # Check all time delay fields from trigger 1, get max delay time
    max_t = 0
    for cw in window.trig1_ctrl.channel_widgets:

        # Get text from field
        delay_text = cw.time_edit.text()

        # Convert text to float
        try:
            t_delay = float(delay_text)
        except:
            t_delay = 0

        # Compare maxima
        max_t = max(t_delay, max_t)

    # Start countdown timer and widget
    window.run_tool.start_countdown(max_t)

    # Disable trigger button
    window.run_tool.button_widgets[0].setEnabled(False)

    # Set Keysight oscilloscope to single trigger
    window.scope_ctrl.command("SINGLE_TRIGGER")

    # Set Picoscope to single trigger
    window.pico_ctrl.command("SINGLE_TRIGGER")

    # Trigger the delay generator
    window.trig1_ctrl.command("single_trigger")


def countdown_end_fn(macro_runner_tool):
    """
    This function is called at the end of the trigger button countdown timer. It
    re-enables the trigger button (which is disabled during countdown).
    """

    # Re-enable trigger button
    macro_runner_tool.button_widgets[0].setEnabled(True)


def save_shot_format(dataset, filename: str):
    """
    Saves data in the format expected by STS-50 data processing scripts.
    """

    # Write file data
    with open(filename, "a") as outfile:

        outfile.write("# ALPHA experiment\n")
        outfile.write("# setting hash: \n")
        outfile.write("# date: \n")

        # length = self.len_min()
        # while self.autosave_next_row < length:
        #
        #     # Write line
        #     line = " ".join(
        #         [
        #             str(self.data[key][self.autosave_next_row])
        #             for key in self.data
        #         ]
        #     )
        #     outfile.write(line + "\n")
        #
        #     # Move pointer to next line
        #     self.autosave_next_row += 1
    # if "Keysight:" dataset.data


class CustomControlWidget(QGroupBox):
    def __init__(self, window, filament_dg, arc_dg, name="Timing Control"):

        super().__init__()

        self.filament_dg = filament_dg
        self.arc_dg = arc_dg

        self.plasma_timing_label = QLabel()
        self.plasma_timing_label.setPixmap(
            load_icon("plasma_source_timing_settings_label.svg")
        )
        self.plasma_timing_label.setAlignment(
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter
        )

        self.filament_label = QLabel("Filament duration (sec): ")

        instr_idx = window.app.get_instrument_idx("Trigger 1")
        self.filament_edit = QLineEdit()
        self.filament_edit.setValidator(QDoubleValidator())
        if instr_idx != -1:
            self.filament_edit.editingFinished.connect(
                lambda idx=instr_idx: window.app.instruments[idx].remote_update_setting(
                    "CH2_delay", self.filament_edit.text()
                )
            )
        self.filament_edit.setText(filament_dg.settings["CH2_delay"])

        self.filament_amp_label = QLabel("Filament amplitude (a.u.): ")

        self.filament_amp_edit = QLineEdit()
        self.filament_amp_edit.setValidator(QDoubleValidator())
        if instr_idx != -1:
            self.filament_amp_edit.editingFinished.connect(
                lambda idx=instr_idx: window.app.instruments[idx].remote_update_setting(
                    "CH12_output_amplitude", self.filament_amp_edit.text()
                )
            )
        self.filament_amp_edit.setText(
            self.filament_dg.settings["CH12_output_amplitude"]
        )

        self.spark_delay_label = QLabel("Spark delay (sec): ")

        self.spark_delay_edit = QLineEdit()
        self.spark_delay_edit.setValidator(QDoubleValidator())
        if instr_idx != -1:
            self.spark_delay_edit.editingFinished.connect(
                lambda idx=instr_idx: window.app.instruments[idx].remote_update_setting(
                    "CH3_delay", self.spark_delay_edit.text()
                )
            )
        self.spark_delay_edit.setText(filament_dg.settings["CH3_delay"])

        self.spark_duration_label = QLabel("Spark duration (sec): ")

        instr_idx = window.app.get_instrument_idx("Trigger 2")

        self.spark_duration_edit = QLineEdit()
        self.spark_duration_edit.setValidator(QDoubleValidator())
        if instr_idx != -1:
            self.spark_duration_edit.editingFinished.connect(
                lambda idx=instr_idx: window.app.instruments[idx].remote_update_setting(
                    "CH4_delay", self.spark_duration_edit.text()
                )
            )
        self.spark_duration_edit.setText(arc_dg.settings["CH4_delay"])

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.plasma_timing_label, 0, 0, 1, 4)
        self.master_layout.addWidget(self.filament_label, 1, 0)
        self.master_layout.addWidget(self.filament_edit, 1, 1)
        self.master_layout.addWidget(self.filament_amp_label, 1, 2)
        self.master_layout.addWidget(self.filament_amp_edit, 1, 3)
        self.master_layout.addWidget(self.spark_delay_label, 2, 0)
        self.master_layout.addWidget(self.spark_delay_edit, 2, 1)
        self.master_layout.addWidget(self.spark_duration_label, 2, 2)
        self.master_layout.addWidget(self.spark_duration_edit, 2, 3)

        self.setLayout(self.master_layout)


class STS50Demo(HC_MainWindow):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.app.main_window = self

        self.setWindowTitle("STS-50 Control Panel")

        self.tabs = QTabWidget()
        self.tab0 = QWidget()
        self.tab1 = QWidget()
        self.tab1_5 = QWidget()
        self.tab2 = QWidget()
        # self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tab6 = QWidget()
        self.console_tab = HC_Qtconsole(main_app=app)

        self.tabs.addTab(self.tab0, "Main")
        self.tabs.addTab(self.tab4, "Plasma Source")
        self.tabs.addTab(self.tab1, "Oscilloscope")
        self.tabs.addTab(self.tab1_5, "Picoscope")
        self.tabs.addTab(self.tab2, "Power Supplies")
        # self.tabs.addTab(self.tab3, "Aux 1")
        self.tabs.addTab(self.tab5, "Plots")
        self.tabs.addTab(self.tab6, "Datasets")
        self.tabs.addTab(self.console_tab, "Console")

        self.main_widget = QWidget(self)

        #####################################################################
        ######## Tab 1

        # Enter socket address as ip:port, ex: 192.168.0.14:5025
        # scpi_scope = Key4000XCtrl("TCPIP0::192.168.0.14::INSTR")
        scpi_scope = Key4000XCtrl("192.168.0.14")
        self.scope_ctrl = HC_Oscilloscope(scpi_scope, self, "Keysight Scope")
        self.scope_ctrl.load_state("Key4000_init.json")
        self.scope_ctrl.settings_to_UI()
        self.scope_ctrl.set_online_callback(init_with_JSON)

        # Put instrument(s) in tab
        self.tab1_layout = QGridLayout()
        self.tab1_layout.addWidget(self.scope_ctrl, 0, 0)
        self.tab1.setLayout(self.tab1_layout)

        #####################################################################
        ######## PicoTab

        self.pico = ZMQOscilloscopeCtrl("tcp://192.168.0.30:6000")
        self.pico_ctrl = HC_Oscilloscope(self.pico, self, "PicoScope")
        self.pico_ctrl.load_state("picoscope_init.json")
        self.pico_ctrl.settings_to_UI()
        self.pico_ctrl.set_online_callback(init_with_JSON)

        self.tab1_5_layout = QGridLayout()
        self.tab1_5_layout.addWidget(self.pico_ctrl, 0, 0)
        self.tab1_5.setLayout(self.tab1_5_layout)

        #####################################################################
        ######## Tab 2

        # usb pyvisa address is # "USB0::0x0957::0x2907::MY52500624::INSTR"
        awg = Key33500BCtrl("TCPIP0::192.168.0.18::INSTR",)
        self.awg_ctrl = HC_FunctionGenerator(awg, self, "RF Generator", 1)

        self.psu = TDKLGenHCtrl("TCPIP0::192.168.1.19::INSTR")
        self.psu_ctrl = HC_MultiPowerSupply(self.psu, self, [1], "TDK Lambda (RF Vin)",)

        self.psu_caen = CAEN14xxETCtrl("192.168.0.1:1470")
        self.psu_caen_wdgt = HC_MultiPowerSupply(
            self.psu_caen, self, [3, 8], "CAEN High Voltage Power Supply"
        )
        self.psu_caen_wdgt.set_online_callback(init_with_instrument)

        # Put instrument(s) in tab
        self.tab2_layout = QGridLayout()
        self.tab2_layout.addWidget(self.awg_ctrl, 0, 0)
        self.tab2_layout.addWidget(self.psu_ctrl, 0, 1)
        self.tab2_layout.addWidget(self.psu_caen_wdgt, 1, 0, 1, 2)
        self.tab2.setLayout(self.tab2_layout)

        #####################################################################
        ######## Tab 3

        self.flow = AlicatMSeriesCtrl("192.168.0.15")
        self.flow_ctrl = HC_FlowController(self.flow, self, "Flow Controller")

        # Todo: linux-gpib is a dependency on some systems
        self.trig1 = SRSDG535Ctrl("GPIB0::10::INSTR")
        self.trig1_ctrl = HC_DelayGenerator(self.trig1, self, "Trigger 1")
        self.trig1_ctrl.load_state("delaygen_filament_init.json")
        self.trig1_ctrl.settings_to_UI()
        self.trig1_ctrl.set_online_callback(init_with_JSON)

        self.trig2 = SRSDG535Ctrl("GPIB0::15::INSTR")
        self.trig2_ctrl = HC_DelayGenerator(self.trig2, self, "Trigger 2")
        self.trig2_ctrl.load_state("delaygen_arc_init.json")
        self.trig2_ctrl.settings_to_UI()
        self.trig2_ctrl.set_online_callback(init_with_JSON)

        self.iomod_float = NI9000Ctrl()
        self.iomod_float_wdgt = HC_IOModule(
            self.iomod_float,
            self,
            channel_data=None,
            name="Floating Rack Power Supplies",
            num_columns=2,
            channel_file="nidaq_extraction_conf.json",
            hooks={
                "cDAQ9188-1AEF742Mod7/ao4": lambda v: -v / 1000,
                "cDAQ9188-1AEF742Mod6/ai6": lambda v: v * 1e-3,
                "cDAQ9188-1AEF742Mod6/ai7": lambda v: v * 1000,
            },
        )

        self.iomod_usb = NI9000Ctrl()
        self.iomod_usb_wdgt = HC_IOModule(
            self.iomod_usb,
            self,
            channel_data=None,
            name="USB NI-DAC",
            num_columns=2,
            channel_file="nidaq_grid_conf.json",
            hooks={
                "cDAQ1Mod1/ao0": lambda v: v / 3000,
                "cDAQ1Mod1/ao1": lambda v: v / 3000,
                "cDAQ1Mod2/ai0": lambda v: v * 3000,
                "cDAQ1Mod2/ai1": lambda v: v * 1e-3,
                "cDAQ1Mod2/ai2": lambda v: v * 1e-3,
                "cDAQ1Mod2/ai3": lambda v: v * 3000,
                "cDAQ1Mod2/ai4": lambda v: 10 ** (v - 11),
            },
        )
        self.iomod_usb_wdgt.command("DISPLAY_CONFIGURATION")

        self.zmqtool = HC_ZMQConnectionTool(self, "ZMQ Input Tool", "tcp://*:5555")

        self.scantool = HC_ScanTool(self, "Scan Control", True)
        self.scantool.update_instruments()

        self.logtool = HC_LoggerTool(self, "Data Logger")
        self.logtool.update_groups()
        # self.logtool.update_instruments()

        self.statustool = HC_StatusTool(self, "Connection Status")

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
        app.add_macro("PowerOff", ["FUNC:HANDLE:power_off"])
        # "Trigger", ["FUNC:VAR:SHOT_ID_NUM:10", "FUNC:UPDATE:MACRO_IND",],
        app.add_macro("Safe", ["CMD:PSU:ALL_OFF", "CMD:AWG:ALL_OFF"])
        app.add_macro("Wait_1s", ["FUNC:time:sleep:1"])
        app.add_macro("print_fil_ampl", ["FUNC:HANDLE:print_fil"])
        app.add_macro("MeasurementRequest", ["FUNC:DISP:str:MEAS:REQ"])

        app.function_handles["trigger_function"] = lambda: trigger_function(self)
        app.function_handles["power_off"] = lambda: power_off(self)
        app.function_handles["print_fil"] = self.print_fil

        buttons = {}
        buttons["Trigger"] = "Trigger Beam"
        buttons["PowerOff"] = "Power Down"
        self.run_tool = HC_MacroRunnerTool(
            self,
            "Operations",
            ["Trigger", "PowerOff"],
            ["Trigger Beam", "Power Down"],
            # {"Trigger": "Trigger Beam", "PowerOff": "Power Down"},
            {"SHOT_ID_NUM": "Shot ID Number: "},
            add_countdown=True,
        )
        self.run_tool.update_macros()
        self.run_tool.countdown_end = countdown_end_fn
        self.power_off_ind = load_icon("voltage_off.svg")
        self.run_tool.button_widgets[1].setIcon(QIcon(self.power_off_ind))

        # self.kill_tool = HC_MacroRunnerTool(
        #     self,
        #     "Shut",
        #     {"Trigger": "Trigger Beam"},
        #     {"SHOT_ID_NUM": "Shot ID Number: "},
        #     add_countdown=True,
        # )
        # self.run_tool.update_macros()

        # self.run_tool = HC_MacroRunnerTool(
        #     self,
        #     "Trigger Beam",
        #     {"Dynamic": "Run Macro", "Trigger": "Trigger Beam"},
        #     {"FIL_AMPL_V" : "Filament Amplitude: "},
        # )

        # Create Datasets
        self.app.data_sets["High Voltage"] = Dataset("High Voltage", self.app)
        self.app.data_sets["High Voltage"].start_asynch(3)
        self.app.data_sets["High Voltage"].add_instrument(self.iomod_usb_wdgt)
        # {'CHcDAQ1Mod2/ai0_analog_read': '', 'CHcDAQ1Mod2/ai1_analog_read': '', 'CHcDAQ1Mod2/ai2_analog_read': '', 'CHcDAQ1Mod2/ai3_analog_read': '', 'CHcDAQ1Mod2/ai4_analog_read': ''}

        self.app.data_sets["High Voltage"].name_channel(
            "USB NI-DAC:CHcDAQ1Mod2/ai0_analog_read", "V float"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "USB NI-DAC:CHcDAQ1Mod2/ai1_analog_read", "I float"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "USB NI-DAC:CHcDAQ1Mod2/ai2_analog_read", "I grid"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "USB NI-DAC:CHcDAQ1Mod2/ai3_analog_read", "V grid"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "USB NI-DAC:CHcDAQ1Mod2/ai4_analog_read", "Pressure"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "USB NI-DAC:CHcDAQ9188-1AEF742Mod6/ai7_analog_read", "V extract"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "USB NI-DAC:CHcDAQ9188-1AEF742Mod6/ai6_analog_read", "I extract"
        )

        self.logtool.update_groups()
        self.logtool.set_group("High Voltage")

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
        # self.tab3_layout = QGridLayout()
        # # self.tab3_layout.addWidget(self.flow_ctrl, 0, 0)
        # # self.tab3_layout.addWidget(self.flow_ctrl, 0, 0)
        # # self.tab3_layout.addWidget(self.trig2_ctrl, 2, 0)
        # # self.tab3_layout.addWidget(self.zmqtool, 1, 0)
        # # self.tab3_layout.addWidget(self.iomod_float_wdgt, 2, 1)
        # # self.tab3_layout.addWidget(self.iomod_usb_wdgt, 0, 1, 2, 1)
        # # self.tab3_layout.addWidget(self.temp_ctrl, 2, 0)
        # self.tab3_spacer = QSpacerItem(
        #     10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        # )
        # self.tab3_layout.addItem(self.tab3_spacer, 3, 0, 1, 2)
        # # self.tab3_layout.addWidget(self.scantool, 0, 1)
        # # self.tab3_layout.addWidget(self.run_tool, 1, 1)
        # # self.tab3_layout.addWidget(self.var_tool, 2, 1)
        #
        # # self.tab3_layout.addWidget(self.statustool, 3, 1)
        # self.tab3.setLayout(self.tab3_layout)

        # #####################################################################
        # ######## Custom Tab

        self.tab_sts_layout = QGridLayout()

        self.tab_sts_layout.addWidget(self.trig1_ctrl, 0, 0)
        self.tab_sts_layout.addWidget(self.trig2_ctrl, 1, 0)
        self.tab4.setLayout(self.tab_sts_layout)

        # ########## Tab 5 - Experimental

        self.plot_wdgt1 = HC_PlotTool(self, "Floating Rack")
        self.plot_wdgt1.set_dataset("High Voltage")

        self.tab5_layout = QGridLayout()
        self.tab5_layout.addWidget(self.plot_wdgt1, 0, 0)

        self.tab5.setLayout(self.tab5_layout)

        #####################################

        self.tab6_layout = QGridLayout()

        self.tab6_layout.addWidget(self.logtool, 0, 0)

        self.tab6.setLayout(self.tab6_layout)

        #####################################################################
        ######## Tab 0

        self.custom_wdgt = CustomControlWidget(
            self, self.trig1_ctrl, self.trig2_ctrl, "Main Control"
        )

        # self.grid_ps_label_spacer = QSpacerItem(
        #     10, 25, QSizePolicy.Minimum, QSizePolicy.Fixed
        # )

        self.grid_ps_label = QLabel()
        self.grid_ps_label.setPixmap(load_icon("grid_power_supplies_label.svg"))
        self.grid_ps_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        self.grid_plot_label = QLabel()
        self.grid_plot_label.setPixmap(load_icon("grid_monitor_label.svg"))
        self.grid_plot_label.setAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
        )

        self.gas_flow_label = QLabel()
        self.gas_flow_label.setPixmap(load_icon("gas_flow_label.svg"))
        self.gas_flow_label.setAlignment(QtCore.Qt.AlignHCenter)

        self.plot_wdgt_custom = HC_PlotTool(self, "Voltage Monitor")
        self.plot_wdgt_custom.set_dataset("High Voltage")

        self.main_bottom_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.tab0_layout = QGridLayout()
        self.tab0_layout.addWidget(self.custom_wdgt, 0, 0, 1, 2)
        # self.tab0_layout.addItem(self.grid_ps_label_spacer, 1, 0)
        self.tab0_layout.addWidget(self.grid_ps_label, 2, 0)

        self.tab0_layout.addWidget(self.iomod_float_wdgt, 3, 0, 1, 1)
        self.tab0_layout.addWidget(self.iomod_usb_wdgt, 4, 0, 2, 1)
        self.tab0_layout.addWidget(self.gas_flow_label, 2, 1)
        self.tab0_layout.addWidget(self.flow_ctrl, 3, 1)
        self.tab0_layout.addWidget(self.grid_plot_label, 4, 1)
        self.tab0_layout.addWidget(self.plot_wdgt_custom, 5, 1)
        self.tab0_layout.addItem(self.main_bottom_spacer, 10, 0, 1, 2)

        # self.tab0_layout.addWidget(self.iomod_float_wdgt, 3, 0)
        # self.tab0_layout.addWidget(self.iomod_usb_wdgt, 3, 1)
        # self.tab0_layout.addWidget(self.flow_ctrl, 5, 0)
        # self.tab0_layout.addWidget(self.plot_wdgt_custom, 5, 1)
        # self.tab0_layout.addItem(self.main_bottom_spacer, 10, 0, 1, 2)
        self.tab0.setLayout(self.tab0_layout)

        #####################################################################
        ######## Set master window layout

        self.statustool.update_instruments()

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

    def print_fil(self):

        print("Filament amplitude = " + str(self.app.variables["FIL_AMPL_V"]))


def main():
    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning
    )  # ToDo Not a solution
    app = HC_App(dummy=dummy)
    app.print_close_info = True

    app.add_save_format("SHOT", save_shot_format)

    ex = STS50Demo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
