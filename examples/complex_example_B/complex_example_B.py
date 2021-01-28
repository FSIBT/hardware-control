#!/usr/bin/env python3
"""oscilloscope_example to control the hardware_control test stand

Usage:
  sts50_example [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""

import hashlib
import logging
import sys
from time import localtime, strftime
import warnings
import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QStyleFactory,
    QTabWidget,
    QGridLayout,
    QWidget,
    QSpacerItem,
    QSizePolicy,
    QGroupBox,
    QPushButton,
    QApplication,
)
from PyQt5.QtGui import QIcon, QDoubleValidator
from docopt import docopt
from PyQt5.QtCore import QTimer

import hardware_control.backends as hc_back
import hardware_control.gui as hc


commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging(logger, commands, "hardware_control.log")

logger.info("STS50 Example Starting")

# where should we save the data
OUTPUT_DIR = Path.home() / "Desktop" / "STS50-data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_output_dir():
    """Adds the current date to the output dir"""
    loc_time = localtime()
    YYYYMMDD = strftime("%Y-%m-%d", loc_time)
    output_dir = OUTPUT_DIR / YYYYMMDD
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def init_with_JSON(instrument):
    """Send the current state (after a the state has been read from a json file)."""

    instrument.send_state()
    instrument.online_callback = None


def init_with_instrument(instrument):
    """Load all settings from the instrument."""

    instrument.read_state_from_backend()
    instrument.settings_to_UI()
    instrument.online_callback = None


def init_osc_when_online(instrument):
    """First set the state as configured by an already read json file,
    update so that waveforms are read correctly.

    """

    init_with_JSON(instrument)

    instrument.command("CONFIG_READ_WAVE")
    instrument.online_callback = None


def power_off(window):

    # Disable CAEN
    window.psu_caen_wdgt.remote_update_setting("CH3_ENABLE", "False")
    window.psu_caen_wdgt.remote_update_setting("CH8_ENABLE", "False")

    # Disable RF Generator
    window.awg_ctrl.remote_update_setting("CH1_ENABLED", "False")

    # Disable TDK Lambda
    window.psu_ctrl.remote_update_setting("CH1_ENABLED", "False")

    # Shut off gas
    window.flow_ctrl.remote_update_setting("RATE", "0")

    # Shut off NI-DAQ Power Supplies
    window.iomod_usb_wdgt.remote_update_setting("CHMod1/ao0_ANALOG_WRITE", "0")
    window.iomod_usb_wdgt.remote_update_setting("CHMod1/ao1_ANALOG_WRITE", "0")
    window.iomod_float_wdgt.remote_update_setting("CHMod7/ao4_ANALOG_WRITE", "0")


def save_continuous_data(dataset: hc.Dataset, filename: str) -> None:

    loc_time = localtime()
    header_datestamp = strftime("%Y-%m-%d %H:%M:%S", loc_time)

    # Add extension if not specified
    ext = os.path.splitext(filename)[-1].lower()
    if ext == "":
        filename = filename + ".txt"

    # Write header if file doesn't exist
    if not os.path.exists(filename):
        with open(filename, "w") as outfile:

            outfile.write(
                f"# ALPHA experiment\n"
                f"# Continuous data\n"
                f"# date: {header_datestamp}\n"
            )

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
            outfile.write(f'{" ".join(col_titles)} \n')

    # Write file data
    with open(filename, "a") as outfile:

        length = dataset.len_min()
        while dataset.autosave_next_row < length:

            # Write line
            line = " ".join(
                [
                    str(dataset.data[key][dataset.autosave_next_row])
                    for key in dataset.data
                ]
            )
            outfile.write(line + "\n")

            # Move pointer to next line
            dataset.autosave_next_row += 1


def trigger_function(app):
    """
    This function is used by the app to describe the beam triggering sequence. It
    is called when the beam trigger button is pressed or the trigger macro is run.
    """

    # Update shot number and shot number widget
    lt = localtime()
    timestamp = strftime("%H%M%S", lt)

    # Check all time delay fields from trigger 1, get max delay time
    max_t = 0
    for cw in app.main_window.trig1_ctrl.channel_widgets:

        # Get text from field, not all channels have a delay though
        try:
            delay_text = cw.time_delay.text()
        except:
            continue

        # Convert text to float
        try:
            t_delay = float(delay_text)
        except:
            t_delay = 0

        # Compare maxima
        max_t = max(t_delay, max_t)

    # Disable trigger button
    app.main_window.run_tool.run_button.setEnabled(False)

    # Set Keysight oscilloscope to single trigger
    app.main_window.scope_ctrl.command("SINGLE_TRIGGER")

    # Set Picoscope to single trigger
    app.main_window.pico_ctrl.command("SINGLE_TRIGGER")

    # Trigger the delay generator
    app.main_window.trig1_ctrl.command("SINGLE_TRIGGER")

    # Add timestamp to dataset
    app.data_sets["Shots"].data["Timestamp"].append(timestamp)

    QTimer.singleShot(int((max_t + 1) * 1000), lambda: refresh_waveforms(app))
    QTimer.singleShot(int((max_t + 2.5) * 1000), lambda: save_waveforms_to_set(app))


def refresh_waveforms(app):

    pico = app.get_instrument_by_name("PicoScope")
    key = app.get_instrument_by_name("Keysight Scope")

    pico.disp.query_waveforms()
    key.disp.query_waveforms()


def save_waveforms_to_set(app):

    pico = app.get_instrument_by_name("PicoScope")
    key = app.get_instrument_by_name("Keysight Scope")

    picoscope_data = pico.get_last_waveform()
    keysight_data = key.get_last_waveform()

    app.data_sets["Shots"].data["Picoscope_waveform"].append(picoscope_data)
    app.data_sets["Shots"].data["Keysight_waveform"].append(keysight_data)

    app.data_sets["Shots"].save("beam_data.txt", "SHOT")


def countdown_end_fn(app):
    """
    This function is called at the end of the trigger button countdown timer. It
    re-enables the trigger button (which is disabled during countdown).
    """

    # Re-enable trigger button
    app.main_window.run_tool.run_button.setEnabled(True)


def save_shot_format(dataset: hc.Dataset, filename: str) -> None:
    """
    Saves data in the format expected by STS-50 data processing scripts.
    """

    loc_time = localtime()
    header_datestamp = strftime("%Y-%m-%d %H:%M:%S", loc_time)
    datestamp = strftime("%Y-%m-%d-%H%M%S", loc_time)

    # Get settings hash and save settings file
    set_str = dataset.app.save_all_states(None)
    hash_str = hashlib.sha256(set_str.encode("utf-8")).hexdigest()
    dataset.app.save_all_states(get_output_dir() / f"settings-{hash_str}.txt")

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
            outfile.write(f"# setting hash: {hash_str}\n")
            outfile.write(f"# date: {header_datestamp}\n")
            outfile.write("# columns:")

            T = dataset.data[scope_key][-1][0][0]
            ch1 = dataset.data[scope_key][-1][0][1]
            ch2 = dataset.data[scope_key][-1][1][1]
            ch3 = dataset.data[scope_key][-1][2][1]
            ch4 = dataset.data[scope_key][-1][3][1]

            # Determine which channels to write
            wr_lengths = []
            write_ch1 = False
            write_ch2 = False
            write_ch3 = False
            write_ch4 = False
            if len(ch1) > 0:
                write_ch1 = True
                wr_lengths.append(len(ch1))
                outfile.write(f" ch1")
            if len(ch2) > 0:
                write_ch2 = True
                wr_lengths.append(len(ch2))
                outfile.write(f" ch2")
            if len(ch3) > 0:
                write_ch3 = True
                wr_lengths.append(len(ch3))
                outfile.write(f" ch3")
            if len(ch4) > 0:
                write_ch4 = True
                wr_lengths.append(len(ch4))
                outfile.write(f" ch4")
            outfile.write(f"\n")

            # Make sure a list has values
            if len(wr_lengths) == 0:
                logger.warning(
                    "Failed to write oscilloscope data. No channels have data"
                )
                return False

            # make sure all lists to write have same length
            if wr_lengths[1:] != wr_lengths[:-1]:
                logger.warning(
                    "Failed to write oscilloscope data. Not all channels have same number of data points"
                )
                return False

            # Get time array
            if write_ch1:
                T = dataset.data[scope_key][-1][0][0]
            elif write_ch2:
                T = dataset.data[scope_key][-1][1][0]
            elif write_ch3:
                T = dataset.data[scope_key][-1][2][0]
            else:
                T = dataset.data[scope_key][-1][3][0]

            for idx in range(wr_lengths[0]):
                t = T[idx]
                outfile.write(f"{t}")
                if write_ch1:
                    a = ch1[idx]
                    outfile.write(f" {a}")
                if write_ch2:
                    a = ch2[idx]
                    outfile.write(f" {a}")
                if write_ch3:
                    a = ch3[idx]
                    outfile.write(f" {a}")
                if write_ch4:
                    a = ch4[idx]
                    outfile.write(f" {a}")
                outfile.write("\n")

            return True

    save_scope_file(
        "Keysight_waveform", get_output_dir() / f"scope-data-{datestamp}.txt"
    )
    save_scope_file(
        "Picoscope_waveform", get_output_dir() / f"picoscope-data-{datestamp}.txt"
    )

    misc_fn = get_output_dir() / f"misc-data-{datestamp}.txt"

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
            dataset.app.get_instrument_value("Power Supplies", "CHMod2/ai0_ANALOG_READ")
        )
        col_vals.append(
            dataset.app.get_instrument_value("Power Supplies", "CHMod2/ai1_ANALOG_READ")
        )
        col_vals.append(
            dataset.app.get_instrument_value("Power Supplies", "CHMod2/ai2_ANALOG_READ")
        )
        col_vals.append(
            dataset.app.get_instrument_value("Power Supplies", "CHMod2/ai3_ANALOG_READ")
        )
        col_vals.append(
            dataset.app.get_instrument_value("Power Supplies", "CHMod2/ai4_ANALOG_READ")
        )
        col_vals.append(
            dataset.app.get_instrument_value(
                "Power Supplies (floating rack)", "CHMod6/ai6_ANALOG_READ"
            )
        )
        col_vals.append(
            dataset.app.get_instrument_value(
                "Power Supplies (floating rack)", "CHMod6/ai7_ANALOG_READ"
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


class CustomPowerSupplyWidget(hc.Instrument):
    def __init__(self, app, caen, name="Power Supply Control"):

        super().__init__(app, name)

        self.ignore = True
        self.ignore_control = False
        self.settings = self.default_state()

        self.caen = caen

        self.main_header = hc.QHeader("power_supply_controls_label.svg")

        self.caen_input = hc.QControl(
            self,
            "CAEN_V_SET",
            "CAEN CH 3 & 8 Voltage (V)",
            update_function=self.update_caen,
            remote=False,
        )

        self.horiz_spacer = QSpacerItem(
            200, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.power_button = QPushButton()
        self.power_button.setText("All Off")
        self.power_button.setIcon(QIcon(hc.load_icon("voltage_off.svg")))
        self.power_button.setCheckable(False)
        self.power_button.clicked.connect(lambda: power_off(app.main_window))

        self.vert_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.ch3 = hc.QIndicator(self, "CAEN CH3 Vout", unit="V")
        self.ch8 = hc.QIndicator(self, "CAEN CH8 Vout", unit="V")

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.main_header, 0, 0, 1, 4)
        self.master_layout.addWidget(self.caen_input.label, 1, 0)
        self.master_layout.addWidget(self.caen_input.value, 1, 1)
        self.master_layout.addItem(self.horiz_spacer, 1, 2)
        self.master_layout.addWidget(self.power_button, 1, 3)
        self.master_layout.addWidget(self.ch3.label, 2, 0)
        self.master_layout.addWidget(self.ch3.value, 2, 1)
        self.master_layout.addWidget(self.ch8.label, 2, 2)
        self.master_layout.addWidget(self.ch8.value, 2, 3)
        self.master_layout.addItem(self.vert_spacer, 3, 0, 1, 4)

        self.setLayout(self.master_layout)

        self.service_timer = QTimer(self)
        self.service_timer.timeout.connect(self.update_from_caen)
        self.service_timer.start(1000)

    def settings_to_UI(self):
        self.caen_input.settings_to_UI()
        self.update_caen()

    def update_from_caen(self):
        volt_set3 = self.app.get_instrument_value(
            "CAEN High Voltage Power Supply", "CH3_V_SET"
        )
        volt_set8 = self.app.get_instrument_value(
            "CAEN High Voltage Power Supply", "CH8_V_SET"
        )
        volt_read3 = self.app.get_instrument_value(
            "CAEN High Voltage Power Supply", "CH3_V_OUT"
        )
        volt_read8 = self.app.get_instrument_value(
            "CAEN High Voltage Power Supply", "CH8_V_OUT"
        )

        if volt_set3 is not None and volt_set8 is not None:
            if QApplication.focusWidget() is not self.caen_input.value:
                if volt_set3 == volt_set8 and volt_set3 != self.settings["CAEN_V_SET"]:
                    self.caen_input.setText(volt_set3)
                else:
                    self.caen_input.setText("")

        if volt_read3 is not None:
            self.ch3.setText(volt_read3)

        if volt_read8 is not None:
            self.ch8.setText(volt_read8)

    def default_state(self):
        return {"CAEN_V_SET": ""}

    def update_caen(self, settings="", value=""):
        if not value:
            value = self.settings["CAEN_V_SET"]
        self.caen.remote_update_setting("CH3_V_SET", value)
        self.caen.remote_update_setting("CH8_V_SET", value)


class CustomControlWidget(hc.Instrument):
    def __init__(self, app, filament_dg, arc_dg, name="Timing Control"):

        super().__init__(app, name)

        self.filament = filament_dg
        self.arc = arc_dg
        self.app = app

        self.plasma_timing_header = hc.QHeader(
            "plasma_source_timing_settings_label.svg"
        )

        self.filament_duration = hc.QControl(
            self,
            "FIL_DURATION",
            "Filament duration (sec)",
            remote=[self.filament, "CH2_DELAY"],
        )

        self.filament_amp = hc.QControl(
            self,
            "FIL_AMP",
            "Filament amplitude (a.u.)",
            remote=[self.filament, "CH12_OUTPUT_AMPLITUDE",],
        )

        self.arc_delay = hc.QControl(
            self, "ARC_DELAY", "Arc delay (sec)", remote=[self.filament, "CH3_DELAY",]
        )

        self.arc_duration = hc.QControl(
            self, "ARC_DURATION", "Arc duration (sec)", remote=[self.arc, "CH4_DELAY",],
        )

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.plasma_timing_header, 0, 0, 1, 4)
        self.autolayout_grid(self.master_layout, ncols=2, row_offset=1)
        self.settings = self.default_state()
        self.update_from_remote()

    def update_from_remote(self):
        for ui in self.UIs:
            if isinstance(ui, hc.QControl):
                ui.update_from_remote()

    def settings_to_UI(self):
        for ui in self.UIs:
            ui.settings_to_UI()

    def default_state(self):
        return {"FIL_DURATION": "", "FIL_AMP": "", "ARC_DELAY": "", "ARC_DURATION": ""}


class STS50Demo(hc.MainWindow):
    def __init__(self, app):
        super().__init__(app)

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
        self.console_tab = hc.Qtconsole(app)

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
        self.scope_ctrl = hc.Oscilloscope(
            app, scpi_scope, "Keysight Scope", right_axis=[3]
        )
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
        self.pico_ctrl = hc.Oscilloscope(app, self.pico, "PicoScope", right_axis=[1])
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
        self.awg_ctrl = hc.FunctionGenerator(app, awg, "RF Generator", 1)

        self.psu = hc_back.TDKL_GenH("TCPIP0::192.168.1.19::INSTR")
        self.psu_ctrl = hc.MultiPowerSupply(app, self.psu, [1], "TDK Lambda (RF Vin)",)

        self.psu_caen = hc_back.Caen_14xxET("192.168.0.1:1470")
        self.psu_caen_wdgt = hc.MultiPowerSupply(
            app, self.psu_caen, [3, 8], "CAEN High Voltage Power Supply"
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
        self.flow_ctrl = hc.FlowController(app, self.flow, "Flow Controller")

        self.trig1 = hc_back.SRS_DG535("GPIB0::10::INSTR")
        self.trig1_ctrl = hc.DelayGenerator(app, self.trig1, "Trigger 1")
        self.trig1_ctrl.load_state("delaygen_filament_init.json")
        self.trig1_ctrl.settings_to_UI()
        self.trig1_ctrl.set_online_callback(init_with_JSON)

        self.trig2 = hc_back.SRS_DG535("GPIB0::15::INSTR")
        self.trig2_ctrl = hc.DelayGenerator(app, self.trig2, "Trigger 2")
        self.trig2_ctrl.load_state("delaygen_arc_init.json")
        self.trig2_ctrl.settings_to_UI()
        self.trig2_ctrl.set_online_callback(init_with_JSON)

        self.iomod_float = hc_back.Ni_9000("cDAQ9188-1AEF742")
        self.iomod_float_wdgt = hc.IOModule(
            app,
            self.iomod_float,
            channel_data="nidaq_extraction_conf.json",
            name="Power Supplies (floating rack)",
            num_columns=2,
        )
        self.iomod_float_wdgt.update_settings_hooks["CHMod7/ao4_ANALOG_WRITE"].append(
            lambda s, v: str(-float(v) / 1000)
        )
        self.iomod_float_wdgt.update_values_hooks["CHMod6/ai6_ANALOG_READ"].append(
            lambda s, v: str(float(v) * 1e-3)
        )
        self.iomod_float_wdgt.update_values_hooks["CHMod6/ai7_ANALOG_READ"].append(
            lambda s, v: str(float(v) * 1000)
        )

        self.iomod_usb = hc_back.Ni_9000("cDAQ1")
        self.iomod_usb_wdgt = hc.IOModule(
            app,
            self.iomod_usb,
            channel_data="nidaq_grid_conf.json",
            name="Power Supplies",
            num_columns=2,
        )
        self.iomod_usb_wdgt.update_settings_hooks["CHMod1/ao0_ANALOG_WRITE"].append(
            lambda s, v: str(float(v) / 3000)
        )
        self.iomod_usb_wdgt.update_settings_hooks["CHMod1/ao1_ANALOG_WRITE"].append(
            lambda s, v: str(float(v) / 3000)
        )
        self.iomod_usb_wdgt.update_values_hooks["CHMod2/ai0_ANALOG_READ"].append(
            lambda s, v: str(float(v) * 3000)
        )
        self.iomod_usb_wdgt.update_values_hooks["CHMod2/ai1_ANALOG_READ"].append(
            lambda s, v: str(float(v) * 1e-3)
        )
        self.iomod_usb_wdgt.update_values_hooks["CHMod2/ai2_ANALOG_READ"].append(
            lambda s, v: str(float(v) * 1e-3)
        )
        self.iomod_usb_wdgt.update_values_hooks["CHMod2/ai3_ANALOG_READ"].append(
            lambda s, v: str(float(v) * 3000)
        )
        self.iomod_usb_wdgt.update_values_hooks["CHMod2/ai4_ANALOG_READ"].append(
            lambda s, v: str(10 ** (float(v) - 11))
        )

        self.iomod_usb_wdgt.command("DISPLAY_CONFIGURATION")

        self.zmqtool = hc.ZMQConnectionTool(app, "ZMQ Input Tool", "tcp://*:5555")

        self.logtool = hc.DataWidget(app, "Data Logger")
        self.logtool.update_groups()
        # self.logtool.update_instruments()

        self.statustool = hc.StatusTool(app, "Connection Status")

        self.run_tool = hc.FunctionRunnerTool(
            app,
            name="Operations",
            button_label="Trigger beam",
            call_function=trigger_function,
            countdown=10,
            countdown_callback=countdown_end_fn,
        )

        self.scan_widget = hc.ScanWidget(
            app, "Scan Control", {"Trigger": self.run_tool.run_function}
        )

        # Create Datasets
        self.app.data_sets["High Voltage"] = hc.Dataset("High Voltage", self.app)
        self.app.data_sets["High Voltage"].add_instrument(self.iomod_usb_wdgt)
        self.app.data_sets["High Voltage"].start_asynch(3)

        self.app.data_sets["Shots"] = hc.Dataset("Shots", self.app)
        self.app.data_sets["Shots"].data["Timestamp"] = []
        self.app.data_sets["Shots"].data["Picoscope_waveform"] = []
        self.app.data_sets["Shots"].data["Keysight_waveform"] = []

        self.app.data_sets["Continuous"] = hc.Dataset("Continuous", self.app)
        self.app.data_sets["Continuous"].add_instrument(self.iomod_usb_wdgt)
        self.app.data_sets["Continuous"].add_instrument(self.iomod_float_wdgt)
        self.app.data_sets["Continuous"].start_autosave(
            10, "STS50", get_output_dir() / "continuous.txt"
        )
        self.app.data_sets["Continuous"].start_asynch(3)

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

        self.app.data_sets["High Voltage"].name_channel(
            "Power Supplies:CHMod2/ai0_ANALOG_READ", "V float"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "Power Supplies:CHMod2/ai1_ANALOG_READ", "I float"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "Power Supplies:CHMod2/ai2_ANALOG_READ", "I grid"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "Power Supplies:CHMod2/ai3_ANALOG_READ", "V grid"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "Power Supplies:CHMod2/ai4_ANALOG_READ", "Pressure"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "Power Supplies:CHMod6/ai7_ANALOG_READ", "V extract"
        )
        self.app.data_sets["High Voltage"].name_channel(
            "Power Supplies:CHMod6/ai6_ANALOG_READ", "I extract"
        )

        self.logtool.update_groups()
        self.logtool.set_group("High Voltage")

        # ######## Custom Tab

        self.tab_sts_layout = QGridLayout()

        self.tab_sts_layout.addWidget(self.trig1_ctrl, 0, 0)
        self.tab_sts_layout.addWidget(self.trig2_ctrl, 1, 0)
        self.tab4.setLayout(self.tab_sts_layout)

        # ########## Tab 5 - Experimental

        self.plot_wdgt1 = hc.PlotTool(app, "Floating Rack")
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
            app, self.trig1_ctrl, self.trig2_ctrl, "Timing Control"
        )

        self.custom_wdgt2 = CustomPowerSupplyWidget(
            app, self.psu_caen_wdgt, "Main Tab PS Widget"
        )

        self.grid_ps_header = hc.QHeader("grid_power_supplies_label.svg")

        self.grid_plot_header = hc.QHeader("grid_monitor_label.svg")
        self.grid_plot_header.setSizePolicy(
            QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        )

        self.gas_flow_header = hc.QHeader("gas_flow_label.svg")

        self.plot_wdgt_custom = hc.PlotTool(app, "Voltage Monitor")
        self.plot_wdgt_custom.set_dataset("High Voltage")
        self.plot_wdgt_custom.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        )

        self.tab0_layout = QGridLayout()
        self.tab0_layout.addWidget(self.custom_wdgt, 0, 0, 1, 2)

        self.tab0_layout.addWidget(self.grid_ps_header, 2, 0)
        self.tab0_layout.addWidget(self.iomod_float_wdgt, 3, 0, 1, 1)
        self.tab0_layout.addWidget(self.iomod_usb_wdgt, 4, 0, 2, 1)
        self.tab0_layout.addWidget(self.custom_wdgt2, 6, 0)

        self.tab0_layout.addWidget(self.gas_flow_header, 2, 1)
        self.tab0_layout.addWidget(self.flow_ctrl, 3, 1)
        self.tab0_layout.addWidget(self.plot_wdgt_custom, 5, 1, 2, 1)
        self.tab0_layout.addWidget(self.grid_plot_header, 4, 1)

        self.tab0.setLayout(self.tab0_layout)

        #####################################################################
        ######## Set master window layout

        self.statustool.update_instruments()
        self.scan_widget.update_instruments()

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.tabs, 0, 0, 3, 1)
        self.master_layout.addWidget(self.run_tool, 0, 1)
        self.master_layout.addWidget(self.scan_widget, 1, 1)
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


if __name__ == "__main__":
    warnings.filterwarnings(
        action="ignore", message="unclosed", category=ResourceWarning
    )
    app = hc.App(dummy=dummy)
    app.print_close_info = True

    app.add_save_format("SHOT", save_shot_format)
    app.add_save_format("STS50", save_continuous_data)

    ex = STS50Demo(app)
    app.aboutToQuit.connect(ex.close)
    sys.exit(app.exec_())
