"""
This is the Base class for reading modules
it provides a simple UI.
"""
import json
import logging

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QLabel,
    QGridLayout,
    QSpacerItem,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QSizePolicy,
)

from hardware_control.utility import remove_end_carriage_return, apply_to_label
from hardware_control.widgets import load_icon, setButtonState
from hardware_control.base import HC_Instrument


logger = logging.getLogger(__name__)

LABEL_MIN_WIDTH = -15
DISP_DECIMAL_PLACES = 1


def read_channel_file(filename: str, functions_handles: dict = None):
    """
    Reads channel parameters from a JSON file. Returns a dictionary for
    initializing an HC_IOModule class.

    fucntion_handles allows function handles to be specified in the JSON file as
    a string. That string must then be used as a key in functioN_handles with the
    handle as the value or else the hook for that channel will be ignored.
    """

    if functions_handles is None:
        functions_handles = {}

    # Read data from file
    with open(filename) as file:
        data = json.load(file)

    # Replace hook strings with actual function handle from dict
    for chan_key in data:  # For each channel dict...

        # If a hook is not given, skip
        if "HOOK" not in data[chan_key]:
            continue

        # If function listed as hook is listed in functioN_handles, get handle
        if data[chan_key]["HOOK"] in functions_handles:
            data[chan_key]["HOOK"] = functions_handles[data[chan_key]["HOOK"]]
        else:  # else delete hook
            del data[chan_key]["HOOK"]

    return data


class HC_IOModule(HC_Instrument):
    def __init__(
        self,
        backend,
        window,
        channel_data: dict,
        name: str = "IO Module",
        lock_until_sync=False,
        num_columns: int = 1,
        channel_file: str = "",
    ):

        super().__init__(window, name, backend, lock_until_sync)

        self.settings = {}
        self.backend = backend

        if channel_data == None:
            self.channel_data = read_channel_file(channel_file)
        else:
            self.channel_data = channel_data

        backend.dummy = self.window.app.dummy
        self.address = backend.connection_addr

        self.filename = ""

        self.channel_panel = QGridLayout()
        self.an_in_channels = []
        self.an_out_channels = []
        self.dig_in_channels = []
        self.dig_out_channels = []
        load_idx = 0
        for c_name in self.channel_data:

            load_idx += 1

            c_dict = self.channel_data[c_name]
            if not isinstance(c_dict, dict):
                continue

            c_dict = self.ensure_all_fields(c_dict)
            if c_dict["DIR"] == "OUTPUT":
                if c_dict["TYPE"] == "DIGITAL":
                    last_wdgt = DigitalOutputChannel(
                        self,
                        c_dict["ID_STR"],
                        c_dict["HOOK"],
                        c_dict["UNITS"],
                        c_dict["LABEL"],
                    )
                    self.dig_out_channels.append(last_wdgt)
                else:  # "ANALOG"
                    last_wdgt = AnalogOutputChannel(
                        self,
                        c_dict["ID_STR"],
                        c_dict["HOOK"],
                        c_dict["UNITS"],
                        c_dict["LABEL"],
                    )
                    self.an_out_channels.append(last_wdgt)
            else:  # "INPUT"
                if c_dict["TYPE"] == "DIGITAL":
                    last_wdgt = DigitalInputChannel(
                        self,
                        c_dict["ID_STR"],
                        c_dict["HOOK"],
                        c_dict["UNITS"],
                        c_dict["LABEL"],
                    )
                    self.dig_in_channels.append(last_wdgt)
                else:  # "ANALOG"
                    last_wdgt = AnalogInputChannel(
                        self,
                        c_dict["ID_STR"],
                        c_dict["HOOK"],
                        c_dict["UNITS"],
                        c_dict["LABEL"],
                    )
                    self.an_in_channels.append(last_wdgt)

            self.channel_panel.addWidget(
                last_wdgt,
                int((load_idx - 1) / num_columns),
                (load_idx - 1) % num_columns,
            )

            if "OPTIONS" in c_dict and c_dict["OPTIONS"] is not None:
                for opt in c_dict["OPTIONS"]:

                    opt_name = opt
                    if opt_name.startswith("CHX_"):
                        chan_name = c_dict["ID_STR"]
                        opt_name = f"CH{chan_name}" + opt_name[3:]
                        print(f"\tReplacing {opt} with {opt_name}")

                    self.update_setting(opt_name, c_dict["OPTIONS"][opt])

        self.channel_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.channel_panel.addItem(
            self.channel_spacer,
            1 + (int((load_idx - 1) / num_columns)),
            (load_idx - 1) % num_columns,
        )

        # for idx, ic in enumerate(self.in_channels):
        #     if len(ic) != 4:
        #         continue
        #
        #     self.in_channel_widgets.append(
        #         AnalogInputChannel(self, ic[0], ic[1], ic[2], ic[3])
        #     )
        #     self.channel_panel.addWidget(self.in_channel_widgets[-1], idx, 0)
        #     lowest_row = max(lowest_row, idx)
        #
        # for idx, oc in enumerate(self.out_channels):
        #     if len(oc) != 4:
        #         continue
        #
        #     self.out_channel_widgets.append(
        #         AnalogOutputChannel(self, oc[0], oc[1], oc[2], oc[3], set_to_zero_button=True)
        #     )
        #     self.channel_panel.addWidget(self.out_channel_widgets[-1], idx, 1)
        #     lowest_row = max(lowest_row, idx)

        self.init_values()

        self.bottom_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.channel_panel.addItem(self.bottom_spacer, int(load_idx / num_columns), 0)
        self.main_layout = QGridLayout()
        self.main_layout.addLayout(self.channel_panel, 0, 0)

        self.setLayout(self.main_layout)

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

    def ensure_all_fields(self, x: dict):

        required_fields = ["ID_STR", "HOOK", "UNITS", "LABEL", "OPTIONS"]

        for field_name in required_fields:
            if field_name not in x:
                x[field_name] = None

        return x

    def update_readout(self):
        for ic in self.an_in_channels:
            ic.update_readout()
        for ic in self.dig_in_channels:
            ic.update_readout()

    def settings_to_UI(self):

        for c in self.an_out_channels:
            c.settings_to_UI()
        for c in self.dig_out_channels:
            c.settings_to_UI()

    def init_values(self):

        self.values = {}

        for c in self.an_in_channels:
            self.values[f"CH{c.channel}_analog_read"] = ""
        for c in self.dig_in_channels:
            self.values[f"CH{c.channel}_digital_read"] = ""


class AnalogInputChannel(QGroupBox):
    def __init__(
        self,
        control,
        channel,
        function=None,
        units="V",
        label="Voltage: ",
        show_ID_labels=True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.control = control
        self.channel = channel

        self.conversion_function = function
        if units is None:
            units = ""
        if label is None:
            label = ""
        self.units = units

        self.label_str = label
        self.param_label = QLabel(self.label_str)
        if not self.label_str.endswith(": "):
            self.label_str = self.label_str + ": "
            self.param_label.setText(self.label_str)

        self.measurement_label = QLabel(f"---- {self.units}")
        self.measurement_label.setFixedWidth(120)

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.param_label, 0, 0)
        self.main_layout.addWidget(self.measurement_label, 0, 1)

        self.setLayout(self.main_layout)

    def update_readout(self):
        # Query value
        self.control.comm.command(f"CH{self.channel}_analog_read?")

        try:

            # Read return value
            V_meas = remove_end_carriage_return(
                self.control.read_values(f"CH{self.channel}_analog_read")
            )

            # Convert to float. Run through conversion function if provided
            if callable(self.conversion_function):
                V_meas = self.conversion_function(float(V_meas))

            # Update label
            apply_to_label(
                self.measurement_label,
                V_meas,
                self.units,
                DISP_DECIMAL_PLACES,
                LABEL_MIN_WIDTH,
            )

        except Exception:
            self.measurement_label.setText(f"---- {self.units}")


class AnalogOutputChannel(QGroupBox):
    def __init__(
        self,
        control,
        channel,
        function=None,
        units="V",
        label="Set voltage: ",
        set_to_zero_button=False,
        show_ID_labels=True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.control = control
        self.channel = channel

        self.conversion_function = function
        if units is None:
            units = ""
        if label is None:
            label = ""
        self.units = units

        self.set_to_zero_button = set_to_zero_button

        self.edit_label = QLabel(label)

        self.edit_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.editbox = QLineEdit()
        self.editbox.setValidator(QDoubleValidator())
        self.editbox.setFixedWidth(100)
        self.editbox.editingFinished.connect(self.set_voltage)
        self.editbox.setText("0")

        self.unit_label = QLabel(f" {self.units}")

        if self.set_to_zero_button:
            self.to_zero_but = QPushButton(f"Set to 0 {self.units}")
            self.to_zero_but.setCheckable(False)
            self.to_zero_but.clicked.connect(lambda: self.set_to_zero())

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.edit_label, 0, 0)
        self.main_layout.addWidget(self.editbox, 0, 1)
        self.main_layout.addWidget(self.unit_label, 0, 2)
        if self.set_to_zero_button:
            self.main_layout.addWidget(self.to_zero_but, 1, 1, 1, 2)

        self.setLayout(self.main_layout)

    def set_voltage(self):
        voltage = float(self.editbox.text())

        if callable(self.conversion_function):
            voltage = self.conversion_function(voltage)

        self.control.update_setting(f"CH{self.channel}_analog_write", str(voltage))

    def set_to_zero(self):

        if callable(self.conversion_function):
            voltage = self.conversion_function(0)
        else:
            voltage = 0

        self.editbox.setText("0")
        self.control.update_setting(f"CH{self.channel}_analog_write", str(voltage))

    def settings_to_UI(self):

        self.editbox.setText(self.control.settings[f"CH{self.channel}_analog_write"])


class DigitalInputChannel(QGroupBox):
    def __init__(
        self,
        control,
        channel,
        function=None,
        units="",
        label="Digital: ",
        show_ID_labels=True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.high_indicator = load_icon("high_label.svg")
        self.low_indicator = load_icon("low_label.svg")
        self.error_indicator = load_icon("error_label.svg")
        self.na_indicator = load_icon("na_label.svg")

        self.control = control
        self.channel = channel

        self.conversion_function = function
        if units is None:
            units = ""
        if label is None:
            label = ""
        self.units = units

        self.label_str = label
        self.param_label = QLabel(self.label_str)
        if not self.label_str.endswith(": "):
            self.label_str = self.label_str + ": "
            self.param_label.setText(self.label_str)

        self.measurement_label = QLabel()
        self.measurement_label.setPixmap(self.na_indicator)
        self.measurement_label.setFixedWidth(120)

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.param_label, 0, 0)
        self.main_layout.addWidget(self.measurement_label, 0, 1)

        self.setLayout(self.main_layout)

    def update_readout(self):
        # Query value
        self.control.comm.command(f"CH{self.channel}_digital_read?")

        try:

            # Read return value
            V_meas = remove_end_carriage_return(
                self.control.read_values(f"CH{self.channel}_digital_read")
            )

            # Update label
            if V_meas:
                self.measurement_label.setPixmap(self.high_indicator)
            else:
                self.measurement_label.setPixmap(self.low_indicator)

        except Exception:
            logger.debug("Failed to read digital input from IOModule")
            self.measurement_label.setPixmap(self.error_indicator)
            # self.measurement_label.setText(f"---- {self.units}")


class DigitalOutputChannel(QGroupBox):
    def __init__(
        self,
        control,
        channel,
        function=None,
        units="V",
        label="Set voltage: ",
        show_ID_labels=True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.high_indicator = load_icon("high_label.svg")
        self.low_indicator = load_icon("low_label.svg")

        self.control = control
        self.channel = channel

        self.conversion_function = function
        if units is None:
            units = ""
        if label is None:
            label = ""
        self.units = units

        self.edit_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.ctrl_but = QPushButton("On/Off")
        self.ctrl_but.setCheckable(True)
        self.ctrl_but.clicked.connect(lambda: self.ctrl())

        self.edit_label = QLabel(label)
        self.ind_label = QLabel()
        if self.ctrl_but.isChecked():
            self.ind_label.setPixmap(self.high_indicator)
        else:
            self.ind_label.setPixmap(self.low_indicator)

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.edit_label, 0, 0)
        self.main_layout.addWidget(self.ind_label, 0, 1)
        self.main_layout.addWidget(self.ctrl_but, 0, 2)

        self.setLayout(self.main_layout)

    def ctrl(self):

        if self.ctrl_but.isChecked():
            self.ind_label.setPixmap(self.high_indicator)
        else:
            self.ind_label.setPixmap(self.low_indicator)

        self.control.update_setting(
            f"CH{self.channel}_digital_write", str(self.ctrl_but.isChecked())
        )

    def settings_to_UI(self):
        setButtonState(
            self.ctrl_but, self.control.settings[f"CH{self.channel}_digital_write"]
        )

        if self.ctrl_but.isChecked():
            self.ind_label.setPixmap(self.high_indicator)
        else:
            self.ind_label.setPixmap(self.low_indicator)
