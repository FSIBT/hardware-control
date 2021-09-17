"""
This is the Base class for reading modules
it provides a simple UI.
"""
import json
import logging
from typing import Union

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

from ...utility import remove_end_carriage_return
from ..widgets import load_icon, setButtonState, HCLineEdit, HCLabel


logger = logging.getLogger(__name__)

LABEL_MIN_WIDTH = -15
DISP_DECIMAL_PLACES = 1


def read_channel_file(filename: str):
    """
    Reads channel parameters from a JSON file. Returns a dictionary for
    initializing an hc.IOModule class.
    """

    # Read data from file
    with open(filename) as file:
        data = json.load(file)

    return data


class IOModule(QGroupBox):
    """A GUI for generic Input/Output(IO) module.

    See Also
    --------
    hardware_control.instruments.advantech.Adam_6015.Adam_6015
    hardware_control.instruments.advantech.Adam_6024.Adam_6024
    hardware_control.instruments.ni.Ni_9000.Ni_9000

    """

    def __init__(
        self,
        app,
        instrument,
        channel_data: Union[dict, str],
        name: str = "IO Module",
        lock_until_sync=False,
        num_columns: int = 1,
        show_ID_labels=False,
    ):
        """Initialize the IOModule.

        Parameters
        ----------
        app : hardware_control.App
            The main app instance
        instrument : hardware_control.base.Instrument
            An instrument that will be controlled using this instrument
        channel_data : dict or json-file
            A dictionary that contains that contains data for each channel used (see example below)
        lock_until_sync : bool
        num_columns : integer
        show_ID_labels : bool

        Example
        -------
            channel_data =  {
                    "extraction_voltage_out": {
                        "DIR": "OUTPUT",
                        "TYPE": "Analog",
                        "ID_STR": "Mod7/ao4",
                        "LABEL": "Extraction Voltage (set):",
                        "UNITS": "V",
                        "OPTIONS": {
                             "CHX_V_MAX": "10",
                             "CHX_V_MIN": "-10"
                        }
                     },
                }
        """

        super().__init__(app, name, instrument, lock_until_sync)

        if isinstance(channel_data, str):
            self.channel_data = read_channel_file(channel_data)
        else:
            self.channel_data = channel_data

        self.channel_panel = QGridLayout()
        self.an_in_channels = []
        self.an_out_channels = []
        self.dig_in_channels = []
        self.dig_out_channels = []

        for load_idx, c_dict in enumerate(self.channel_data.values()):

            if not isinstance(c_dict, dict):
                continue

            c_dict = self.ensure_all_fields(c_dict)
            kwargs = {}
            if c_dict["DIR"] == "OUTPUT":
                if c_dict["TYPE"] == "DIGITAL":
                    create_widget_function = DigitalOutputChannel
                    list_of_widgets = self.dig_out_channels
                else:
                    create_widget_function = AnalogOutputChannel
                    list_of_widgets = self.an_out_channels
            else:  # "INPUT"
                if c_dict["TYPE"] == "DIGITAL":
                    create_widget_function = DigitalInputChannel
                    list_of_widgets = self.dig_in_channels
                else:
                    create_widget_function = AnalogInputChannel
                    list_of_widgets = self.an_in_channels
                    if "use_prefix" in c_dict:
                        kwargs["use_prefix"] = c_dict["use_prefix"]

            last_wdgt = create_widget_function(
                self,
                c_dict["ID_STR"],
                c_dict["UNITS"],
                c_dict["LABEL"],
                show_ID_labels=show_ID_labels,
                **kwargs,
            )
            list_of_widgets.append(last_wdgt)

            self.channel_panel.addWidget(
                last_wdgt,
                int(load_idx / num_columns),
                (load_idx) % num_columns,
            )

            if "OPTIONS" in c_dict and c_dict["OPTIONS"] is not None:
                for opt in c_dict["OPTIONS"]:

                    opt_name = opt
                    if opt_name.startswith("CHX_"):
                        chan_name = c_dict["ID_STR"]
                        opt_name = f"CH{chan_name}" + opt_name[3:]
                        valstr = c_dict["OPTIONS"][opt]
                    self.update_setting(opt_name, c_dict["OPTIONS"][opt])

        self.channel_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.channel_panel.addItem(
            self.channel_spacer,
            1 + (int((load_idx - 1) / num_columns)),
            (load_idx - 1) % num_columns,
        )

        self.init_values()
        self.settings = self.default_state()

        self.bottom_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.channel_panel.addItem(self.bottom_spacer, int(load_idx / num_columns), 0)

        self.setLayout(self.channel_panel)

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

    def ensure_all_fields(self, x: dict):
        """Test for certain fields that need to be present in a channel_data dict."""
        required_fields = ["ID_STR", "UNITS", "LABEL", "OPTIONS"]

        for field_name in required_fields:
            if field_name not in x:
                x[field_name] = None

        return x

    def update_readout(self) -> None:
        for ic in self.an_in_channels:
            ic.update_readout()
        for ic in self.dig_in_channels:
            ic.update_readout()

    def settings_to_UI(self) -> None:
        for c in self.an_out_channels:
            c.settings_to_UI()
        for c in self.dig_out_channels:
            c.settings_to_UI()

    def default_state(self):
        default = {}
        for c in self.an_in_channels:
            default[f"CH{c.channel}_ANALOG_READ"] = "0"
            default[f"CH{c.channel}_TERMINAL_CONFIG"] = ""
        for c in self.an_out_channels:
            default[f"CH{c.channel}_ANALOG_WRITE"] = "0"
            default[f"CH{c.channel}_TERMINAL_CONFIG"] = ""
        for c in self.dig_in_channels:
            default[f"CH{c.channel}_DIGITAL_READ"] = "0"
            default[f"CH{c.channel}_TERMINAL_CONFIG"] = ""
        for c in self.dig_out_channels:
            default[f"CH{c.channel}_DIGITAL_READ"] = "0"
            default[f"CH{c.channel}_TERMINAL_CONFIG"] = ""

        return default


class AnalogInputChannel(QGroupBox):
    def __init__(
        self,
        control,
        channel,
        units="V",
        label="Voltage",
        show_ID_labels=True,
        use_prefix=True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.control = control
        self.channel = channel

        if units is None:
            units = ""
        if label is None:
            label = ""
        self.units = units

        self.input = HCLabel(self.control, label, units, use_prefix=use_prefix)

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.input.label, 0, 0)
        self.main_layout.addWidget(self.input.value, 0, 1)

        self.setLayout(self.main_layout)

    def update_readout(self):
        self.control.command(f"CH{self.channel}_ANALOG_READ?")

        try:
            V_meas = remove_end_carriage_return(
                self.control.values.get(f"CH{self.channel}_ANALOG_READ")
            )
        except Exception:
            V_meas = "----"
        self.input.setText(V_meas)


class AnalogOutputChannel(QGroupBox):
    def __init__(
        self,
        control,
        channel,
        units="V",
        label="Voltage (set)",
        set_to_zero_button=False,
        show_ID_labels=True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.control = control
        self.channel = channel

        if units is None:
            units = ""
        if label is None:
            label = ""
        self.units = units

        self.set_to_zero_button = set_to_zero_button

        self.edit_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.edit = HCLineEdit(
            self.control,
            f"CH{self.channel}_ANALOG_WRITE",
            label,
        )

        self.unit_label = QLabel(f" {self.units}")

        if self.set_to_zero_button:
            self.to_zero_but = QPushButton(f"Set to 0 {self.units}")
            self.to_zero_but.setCheckable(False)
            self.to_zero_but.clicked.connect(lambda: self.set_to_zero())

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.edit.label, 0, 0)
        self.main_layout.addWidget(self.edit.value, 0, 1)
        self.main_layout.addWidget(self.unit_label, 0, 2)
        if self.set_to_zero_button:
            self.main_layout.addWidget(self.to_zero_but, 1, 1, 1, 2)

        self.setLayout(self.main_layout)

    def set_to_zero(self):
        self.edit.setText("0")
        self.control.update_setting(f"CH{self.channel}_ANALOG_WRITE", "0")

    def settings_to_UI(self):
        self.edit.settings_to_UI()


class DigitalInputChannel(QGroupBox):
    def __init__(
        self,
        control,
        channel,
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
        self.control.command(f"CH{self.channel}_DIGITAL_READ?")

        try:

            # Read return value
            V_meas = remove_end_carriage_return(
                self.control.values.get(f"CH{self.channel}_DIGITAL_READ")
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
            self.ctrl_but, self.control.settings[f"CH{self.channel}_DIGITAL_WRITE"]
        )

        if self.ctrl_but.isChecked():
            self.ind_label.setPixmap(self.high_indicator)
        else:
            self.ind_label.setPixmap(self.low_indicator)
