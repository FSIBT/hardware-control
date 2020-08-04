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
from time import localtime, strftime
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
    QPushButton,
)
from PyQt5.QtGui import QIcon, QDoubleValidator
from docopt import docopt
from PyQt5.QtCore import QTimer
from PyQt5 import QtCore

import hardware_control.backends as hc_back
import hardware_control.gui as hc


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
    timestamp = strftime("%H%M%S", localtime())
    window.app.variables["SHOT_ID_NUM"] = timestamp
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

    # Add timestamp to dataset
    window.app.data_sets["Shots"].data["Timestamp"].append(timestamp)

    print(max_t * 1e3)
    QTimer.singleShot((max_t + 2) * 1e3, lambda: save_waveforms_to_set(window))


def save_waveforms_to_set(window):

    pico_idx = window.app.get_instrument_idx("PicoScope")
    key_idx = window.app.get_instrument_idx("Keysight Scope")

    picoscope_data = window.app.instruments[pico_idx].get_last_waveform()
    keysight_data = window.app.instruments[key_idx].get_last_waveform()

    window.app.data_sets["Shots"].data["Picoscope_waveform"].append(picoscope_data)
    window.app.data_sets["Shots"].data["Keysight_waveform"].append(keysight_data)

    window.app.data_sets["Shots"].save(f"beam_data.txt", "SHOT")


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

    loc_time = localtime()
    header_datestamp = strftime("%Y-%m-%d %H:%M:%S", loc_time)
    datestamp = strftime("%Y-%m-%d-%H%M%S", loc_time)

    # Ensure minimum length
    if dataset.len_min() < 1:
        logger.warning(
            f"Failed to save data for dataset {dataset.name} because it contains no data."
        )
        return

    def save_scope_file(scope_key, scope_filename):

        # Write oscilloscope data

        with open(scope_filename, "a") as outfile:

            outfile.write("# ALPHA experiment\n")
            outfile.write("# setting hash: \n")
            outfile.write("# date: {header_datestamp}\n")
            outfile.write("# columns: time, ch1, ch2, ch3, ch4\n\n")

            T = dataset.data[scope_key][-1][0][0]
            ch1 = dataset.data[scope_key][-1][0][1]
            ch2 = dataset.data[scope_key][-1][1][1]
            ch3 = dataset.data[scope_key][-1][2][1]
            ch4 = dataset.data[scope_key][-1][3][1]

            for t, a, b, c, d in zip(T, ch1, ch2, ch3, ch4):
                outfile.write(f"{t} {a} {b} {c} {d}\n")

    save_scope_file("Keysight_waveform", f"./Outputs/scope-data-{datestamp}.txt")
    save_scope_file("Picoscope_waveform", f"Outputs/picoscope-data-{datestamp}.txt")

    misc_fn = f"Outputs/misc-data-{datestamp}.txt"

    with open(misc_fn, "a") as outfile:

        outfile.write("# ALPHA experiment\n")
        outfile.write("# setting hash: \n")
        outfile.write(f"# date: {header_datestamp}\n\n")
        col_titles = [
            "time",
            "Floating-rack-current",
            "Floating-rack-voltage",
            "Grid-current",
            "Grid-voltage",
            "Pressure",
            "Extraction-current",
            "Extraction-voltage",
        ]
        for ct in col_titles:
            outfile.write(f"{ct} ")
        outfile.write("\n")

        # Grid -> USB NI-DAC
        # ext -> Floating Rack Power Supplies

        col_vals = []
        col_vals.append(header_datestamp)
        col_vals.append(
            dataset.app.get_instrument_value(
                "USB NI-DAC", "CHcDAQ1Mod2/ai0_analog_read"
            )
        )
        col_vals.append(
            dataset.app.get_instrument_value(
                "USB NI-DAC", "CHcDAQ1Mod2/ai1_analog_read"
            )
        )
        col_vals.append(
            dataset.app.get_instrument_value(
                "USB NI-DAC", "CHcDAQ1Mod2/ai2_analog_read"
            )
        )
        col_vals.append(
            dataset.app.get_instrument_value(
                "USB NI-DAC", "CHcDAQ1Mod2/ai3_analog_read"
            )
        )
        col_vals.append(
            dataset.app.get_instrument_value(
                "USB NI-DAC", "CHcDAQ1Mod2/ai4_analog_read"
            )
        )
        col_vals.append(
            dataset.app.get_instrument_value(
                "Floating Rack Power Supplies", "CHcDAQ9188-1AEF742Mod6/ai6_analog_read"
            )
        )
        col_vals.append(
            dataset.app.get_instrument_value(
                "Floating Rack Power Supplies", "CHcDAQ9188-1AEF742Mod6/ai7_analog_read"
            )
        )

        outfile.write(" ".join([str(cv) for cv in col_vals]))
        outfile.write("\n")

    # ALPHA experiment


# setting hash: 3e5ded4e5772d2e9806092557606462c
# date: 2016-12-20 10:03:55

# time	Grid3 Imon	Grid3 Vmon	Grid2 Imon	Grid2 Vmon	Grid3 Pulser Imon	Grid3 Pulser Vmon	Vacuum main chamber	HV Grid I mon	HV Grid V mon	HV Floating V mon	HV Floating I mon

# ALPHA experiment
# setting hash: 3e5ded4e5772d2e9806092557606462c
# date: 2016-12-20 10:03:55
# columns: time, ch1, ch2, ch3, ch4

# -2.000000E-4	-4.015625E-2	-4.031250E-2	-3.125000E-4	1.593750E-1

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


class CustomPowerSupplyWidget(QGroupBox):
    def __init__(self, caen, window, name="Power Supply Control"):

        super().__init__()

        self.main_label = QLabel()
        self.main_label.setPixmap(hc.load_icon("power_supply_controls_label.svg"))
        self.main_label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)

        self.caen_label = QLabel("CAEN CH 6 & 8 Voltage (V): ")

        instr_idx = window.app.get_instrument_idx("Trigger 1")
        self.caen_edit = QLineEdit()
        self.caen_edit.setValidator(QDoubleValidator())
        # if instr_idx != -1:
        # self.caen_edit.editingFinished.connect(
        #     lambda idx=instr_idx: window.app.instruments[idx].remote_update_setting(
        #         "CH2_delay", self.caen_edit.text()
        #     )
        # )
        # self.caen_edit.setText(caen.settings["CH2_delay"])

        self.horiz_spacer = QSpacerItem(
            200, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.power_button = QPushButton()
        self.power_button.setText("All Off")
        self.power_button.setIcon(QIcon(hc.load_icon("voltage_off.svg")))
        self.power_button.setCheckable(False)
        self.power_button.clicked.connect(lambda: trigger_function(window))

        self.vert_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.main_label, 0, 0, 1, 4)
        self.master_layout.addWidget(self.caen_label, 1, 0)
        self.master_layout.addWidget(self.caen_edit, 1, 1)
        self.master_layout.addItem(self.horiz_spacer, 1, 2)
        self.master_layout.addWidget(self.power_button, 1, 3)
        self.master_layout.addItem(self.vert_spacer, 2, 0, 1, 4)
        # self.master_layout.addWidget(self.filament_amp_label, 1, 2)
        # self.master_layout.addWidget(self.filament_amp_edit, 1, 3)
        # self.master_layout.addWidget(self.spark_delay_label, 2, 0)
        # self.master_layout.addWidget(self.spark_delay_edit, 2, 1)
        # self.master_layout.addWidget(self.spark_duration_label, 2, 2)
        # self.master_layout.addWidget(self.spark_duration_edit, 2, 3)

        self.setLayout(self.master_layout)


class CustomControlWidget(QGroupBox):
    def __init__(self, window, filament_dg, arc_dg, name="Timing Control"):

        super().__init__()

        self.filament_dg = filament_dg
        self.arc_dg = arc_dg

        self.plasma_timing_label = QLabel()
        self.plasma_timing_label.setPixmap(
            hc.load_icon("plasma_source_timing_settings_label.svg")
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


class STS50Demo(hc.MainWindow):
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
        self.console_tab = hc.Qtconsole(main_app=app)

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
        # scpi_scope = hc_back.Keysight_4000X("TCPIP0::192.168.0.14::INSTR")
        scpi_scope = hc_back.Keysight_4000X("192.168.0.14")
        self.scope_ctrl = hc.Oscilloscope(scpi_scope, self, "Keysight Scope")
        self.scope_ctrl.load_state("Key4000_init.json")
        self.scope_ctrl.settings_to_UI()
        self.scope_ctrl.set_online_callback(init_osc_when_online)

        # Put instrument(s) in tab
        self.tab1_layout = QGridLayout()
        self.tab1_layout.addWidget(self.scope_ctrl, 0, 0)
        self.tab1.setLayout(self.tab1_layout)

        #####################################################################
        ######## PicoTab

        self.pico = hc_back.ZMQ_Oscilloscope("tcp://192.168.0.30:6000")
        self.pico_ctrl = hc.Oscilloscope(self.pico, self, "PicoScope")
        self.pico_ctrl.load_state("picoscope_init.json")
        self.pico_ctrl.settings_to_UI()
        self.pico_ctrl.set_online_callback(init_with_JSON)

        self.tab1_5_layout = QGridLayout()
        self.tab1_5_layout.addWidget(self.pico_ctrl, 0, 0)
        self.tab1_5.setLayout(self.tab1_5_layout)

        #####################################################################
        ######## Tab 2

        # usb pyvisa address is # "USB0::0x0957::0x2907::MY52500624::INSTR"
        awg = hc_back.Keysight_33500B("TCPIP0::192.168.0.18::INSTR",)
        self.awg_ctrl = hc.FunctionGenerator(awg, self, "RF Generator", 1)

        self.psu = hc_back.TDKL_GenH("TCPIP0::192.168.1.19::INSTR")
        self.psu_ctrl = hc.MultiPowerSupply(self.psu, self, [1], "TDK Lambda (RF Vin)",)

        self.psu_caen = hc_back.Caen_14xxET("192.168.0.1:1470")
        self.psu_caen_wdgt = hc.MultiPowerSupply(
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

        self.flow = hc_back.Alicat_M_Series("192.168.0.15")
        self.flow_ctrl = hc.FlowController(self.flow, self, "Flow Controller")

        # Todo: linux-gpib is a dependency on some systems
        self.trig1 = hc_back.SRS_DG535("GPIB0::10::INSTR")
        self.trig1_ctrl = hc.DelayGenerator(self.trig1, self, "Trigger 1")
        self.trig1_ctrl.load_state("delaygen_filament_init.json")
        self.trig1_ctrl.settings_to_UI()
        self.trig1_ctrl.set_online_callback(init_with_JSON)

        self.trig2 = hc_back.SRS_DG535("GPIB0::15::INSTR")
        self.trig2_ctrl = hc.DelayGenerator(self.trig2, self, "Trigger 2")
        self.trig2_ctrl.load_state("delaygen_arc_init.json")
        self.trig2_ctrl.settings_to_UI()
        self.trig2_ctrl.set_online_callback(init_with_JSON)

        self.iomod_float = hc_back.Ni_9000()
        self.iomod_float_wdgt = hc.IOModule(
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

        self.iomod_usb = hc_back.Ni_9000()
        self.iomod_usb_wdgt = hc.IOModule(
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

        self.zmqtool = hc.ZMQConnectionTool(self, "ZMQ Input Tool", "tcp://*:5555")

        self.scantool = hc.ScanTool(self, "Scan Control", True)
        self.scantool.update_instruments()

        self.logtool = hc.DataWidget(self, "Data Logger")
        self.logtool.update_groups()
        # self.logtool.update_instruments()

        self.statustool = hc.StatusTool(self, "Connection Status")

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
        self.run_tool = hc.MacroRunnerTool(
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
        self.power_off_ind = hc.load_icon("voltage_off.svg")
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
        self.app.data_sets["High Voltage"] = hc.Dataset("High Voltage", self.app)
        self.app.data_sets["High Voltage"].start_asynch(3)
        self.app.data_sets["High Voltage"].add_instrument(self.iomod_usb_wdgt)

        self.app.data_sets["Shots"] = hc.Dataset("Shots", self.app)
        self.app.data_sets["Shots"].data["Timestamp"] = []
        self.app.data_sets["Shots"].data["Picoscope_waveform"] = []
        self.app.data_sets["Shots"].data["Keysight_waveform"] = []

        self.app.data_sets["Demo"] = hc.Dataset("Demo", self.app)
        self.app.data_sets["Demo"].data["time:time"] = [1, 2, 3]
        self.app.data_sets["Demo"].data[":Voltage"] = [10, 11, 12]
        self.app.data_sets["Demo"].data[":Current"] = [0.1, 0.09, 0.13]
        self.app.data_sets["Demo"].data[":Waveforms"] = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ]
        self.app.data_sets["Demo"].data[":On"] = [None, True, False]
        self.app.data_sets["Demo"].channel_names["time:time"] = "Time (s)"
        self.app.data_sets["Demo"].channel_names[":Voltage"] = "Vtest"
        self.app.data_sets["Demo"].channel_names[":Current"] = "Itest"

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

        self.plot_wdgt1 = hc.PlotTool(self, "Floating Rack")
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
            self, self.trig1_ctrl, self.trig2_ctrl, "Timing Control"
        )

        self.custom_wdgt2 = CustomPowerSupplyWidget(
            self.psu_caen_wdgt, self, "Power Supply Control"
        )

        # self.grid_ps_label_spacer = QSpacerItem(
        #     10, 25, QSizePolicy.Minimum, QSizePolicy.Fixed
        # )

        self.grid_ps_label = QLabel()
        self.grid_ps_label.setPixmap(hc.load_icon("grid_power_supplies_label.svg"))
        self.grid_ps_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        self.grid_plot_label = QLabel()
        self.grid_plot_label.setPixmap(hc.load_icon("grid_monitor_label.svg"))
        self.grid_plot_label.setAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
        )

        self.gas_flow_label = QLabel()
        self.gas_flow_label.setPixmap(hc.load_icon("gas_flow_label.svg"))
        self.gas_flow_label.setAlignment(QtCore.Qt.AlignHCenter)

        self.plot_wdgt_custom = hc.PlotTool(self, "Voltage Monitor")
        self.plot_wdgt_custom.set_dataset("High Voltage")
        self.plot_wdgt_custom.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        )
        self.grid_plot_label.setSizePolicy(
            QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        )

        # self.main_bottom_spacer = QSpacerItem(
        #     10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        # )

        self.tab0_layout = QGridLayout()
        self.tab0_layout.addWidget(self.custom_wdgt, 0, 0, 1, 2)
        # self.tab0_layout.addItem(self.grid_ps_label_spacer, 1, 0)

        self.tab0_layout.addWidget(self.grid_ps_label, 2, 0)
        self.tab0_layout.addWidget(self.iomod_float_wdgt, 3, 0, 1, 1)
        self.tab0_layout.addWidget(self.iomod_usb_wdgt, 4, 0, 2, 1)
        self.tab0_layout.addWidget(self.custom_wdgt2, 6, 0)

        self.tab0_layout.addWidget(self.gas_flow_label, 2, 1)
        self.tab0_layout.addWidget(self.flow_ctrl, 3, 1)
        self.tab0_layout.addWidget(self.plot_wdgt_custom, 5, 1, 2, 1)
        self.tab0_layout.addWidget(self.grid_plot_label, 4, 1)

        # self.tab0_layout.addItem(self.main_bottom_spacer, 10, 0, 1, 2)

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
    app = hc.App(dummy=dummy)
    app.print_close_info = True

    app.add_save_format("SHOT", save_shot_format)

    ex = STS50Demo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())


main()
