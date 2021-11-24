"""
    .. image:: /images/controls/IOModule.png
      :height: 350
"""
import json
import logging
from typing import Union
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QLabel,
    QGridLayout,
    QSpacerItem,
    QGroupBox,
    QSizePolicy,
)

from ..widgets import load_pixmap, HCLineEdit, HCLabel, HCOnOffButton

logger = logging.getLogger(__name__)

LABEL_MIN_WIDTH = -15
DISP_DECIMAL_PLACES = 1


class IOModule(QGroupBox):
    """A GUI for a generic Input/Output (IO) module.

    See Also
    --------
    hardware_control.instruments.advantech.Adam_6015
    hardware_control.instruments.advantech.Adam_6024
    hardware_control.instruments.ni.Ni_9000

    Parameters
    ----------
    app : hardware_control.App
        The main app instance
    instrument : hardware_control.base.Instrument
        The instrument that will be controlled by the control module
    channel_data : dict or json-file
        A dictionary that contains data for each channel used (see example below)
    num_columns : integer
    show_ID_labels : bool

    Example
    -------
    .. code-block:: python

        channel_data =  {
            "extraction_voltage_out": {
                "DIR": "OUTPUT",
                "TYPE": "ANALOG",
                "ID_STR": "Mod7/ao4",
                "LABEL": "Extraction Voltage (set)",
                "UNITS": "V",
                "OPTIONS": {
                    "CHX_V_MAX": "10",
                    "CHX_V_MIN": "-10"
                }
            },
        }

    """

    def __init__(
        self,
        app,
        instrument_name,
        channel_data: Union[dict, str],
        name: str = "IO Module",
        num_columns: int = 1,
        show_ID_labels=False,
    ):
        super().__init__(name)

        self.app = app
        self.instrument = instrument_name
        self.read_channel_data(channel_data)

        self.channel_panel = QGridLayout()
        self.an_in_channels = []
        self.an_out_channels = []
        self.dig_in_channels = []
        self.dig_out_channels = []
        self.channel_names = []

        for load_idx, c_dict in enumerate(self.channel_data.values()):
            c_dict_key = list(self.channel_data.keys())[load_idx]
            if not isinstance(c_dict, dict):
                logger.error(
                    f"{self.instrument}: Value of key {c_dict_key} is not a dictionary."
                )
                continue

            if self.ensure_all_fields(c_dict, c_dict_key) is False:
                continue

            kwargs = {}
            if c_dict["DIR"] == "OUTPUT":
                if c_dict["TYPE"] == "DIGITAL":
                    create_widget_function = DigitalOutputChannel
                    list_of_widgets = self.dig_out_channels
                elif c_dict["TYPE"] == "ANALOG":
                    create_widget_function = AnalogOutputChannel
                    list_of_widgets = self.an_out_channels
                else:
                    logger.error(
                        f"{self.instrument}: 'TYPE' field in channel data mus be set to DIGITAL or ANALOG."
                    )
            elif c_dict["DIR"] == "INPUT":
                if c_dict["TYPE"] == "DIGITAL":
                    create_widget_function = DigitalInputChannel
                    list_of_widgets = self.dig_in_channels
                elif c_dict["TYPE"] == "ANALOG":
                    create_widget_function = AnalogInputChannel
                    list_of_widgets = self.an_in_channels
                    if "use_prefix" in c_dict:
                        kwargs["use_prefix"] = c_dict["use_prefix"]
                else:
                    logger.error(
                        f"{self.instrument}: 'TYPE' field in channel data mus be set to DIGITAL or ANALOG."
                    )
            else:
                logger.error(
                    f"{self.instrument}: 'DIR' field in channel data mus be set to OUTPUT or INPUT."
                )

            chan_name = c_dict["ID_STR"]
            self.channel_names.append(chan_name)

            last_wdgt = create_widget_function(
                self.app,
                self.instrument,
                chan_name,
                c_dict["LABEL"],
                c_dict["UNITS"],
                show_ID_labels=show_ID_labels,
                **kwargs,
            )
            list_of_widgets.append(last_wdgt)

            self.channel_panel.addWidget(
                last_wdgt,
                int(load_idx / num_columns),
                load_idx % num_columns,
            )

            for opt_name in c_dict["OPTIONS"]:
                if opt_name.startswith("CHX_"):
                    param = f"CH{chan_name}" + opt_name[3:]
                else:
                    param = opt_name

                value = c_dict["OPTIONS"][opt_name]
                self.app.set_instrument_parameter(self.instrument, param, value)

        self.channel_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.channel_panel.addItem(
            self.channel_spacer,
            1 + (int((load_idx - 1) / num_columns)),
            (load_idx - 1) % num_columns,
        )

        self.bottom_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.channel_panel.addItem(self.bottom_spacer, int(load_idx / num_columns), 0)

        self.setLayout(self.channel_panel)

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.app.globalRefreshRate)

    def read_channel_data(self, channel_data):
        """Set the channel parameters from a JSON file or a dictionary."""
        self.channel_data = channel_data
        if isinstance(self.channel_data, (Path, str)):
            with open(self.channel_data) as file:
                self.channel_data = json.load(file)
        else:
            self.channel_data = channel_data

    def ensure_all_fields(self, channel_data_dict: dict, channel_data_key=""):
        """Test for certain fields that need to be present in a channel_data dict item."""
        required_fields = ["DIR", "TYPE", "ID_STR", "UNITS", "LABEL", "OPTIONS"]

        for field_name in required_fields:
            if field_name not in channel_data_dict.keys():
                logger.error(
                    f"{self.instrument}: {field_name} is missing in {channel_data_key} channel data dictionary."
                )

                return False

        return True

    def update_readout(self) -> None:
        """Update parameter readouts with values from the instrument."""
        for channel in self.channel_names:
            if "/ai" in channel:
                self.app.update_instrument_parameter(
                    self.instrument, "CH" + channel + "_ANALOG"
                )
            if "/di" in channel:
                self.app.update_instrument_parameter(
                    self.instrument, "CH" + channel + "_DIGITAL"
                )


class AnalogInputChannel(QGroupBox):
    def __init__(
        self,
        app,
        instrument_name: str,
        channel: str,
        label: str = "",
        units: str = "",
        show_ID_labels=True,
        use_prefix=True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.input = HCLabel(
            app,
            instrument_name,
            f"CH{channel}_ANALOG",
            label,
            units,
            use_prefix=use_prefix,
        )

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.input.label, 0, 0)
        self.main_layout.addWidget(self.input, 0, 1)

        self.setLayout(self.main_layout)


class AnalogOutputChannel(QGroupBox):
    def __init__(
        self,
        app,
        instrument_name: str,
        channel: str,
        label: str = "",
        units: str = "",
        show_ID_labels=True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.edit_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.edit = HCLineEdit(
            app,
            instrument_name,
            f"CH{channel}_ANALOG",
            label,
        )

        self.unit_label = QLabel(f" {units}")

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.edit.label, 0, 0)
        self.main_layout.addWidget(self.edit, 0, 1)
        self.main_layout.addWidget(self.unit_label, 0, 2)
        self.setLayout(self.main_layout)


class DigitalInputChannel(QGroupBox):
    def __init__(
        self,
        app,
        instrument_name: str,
        channel: str,
        label: str = "",
        units: str = "",
        show_ID_labels=True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.app = app
        self.instrument_name = instrument_name
        self.channel = channel

        self.high_indicator = load_pixmap("high_label.svg")
        self.low_indicator = load_pixmap("low_label.svg")
        self.error_indicator = load_pixmap("error_label.svg")
        self.na_indicator = load_pixmap("na_label.svg")

        label += ":"
        self.param_label = QLabel(label)

        self.measurement_label = QLabel()
        self.measurement_label.setPixmap(self.na_indicator)
        self.measurement_label.setFixedWidth(120)

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.param_label, 0, 0)
        self.main_layout.addWidget(self.measurement_label, 0, 1)

        self.setLayout(self.main_layout)

        self.app.add_widget(self.instrument_name, f"CH{self.channel}_DIGITAL", self)

    def hc_update(self):
        """Update parameter readout in the channel widget."""
        try:
            # Query value
            truth_val = self.app.get_instrument_parameter(
                self.instrument_name, f"CH{self.channel}_DIGITAL"
            )

            # Update label
            if truth_val:
                self.measurement_label.setPixmap(self.high_indicator)
            else:
                self.measurement_label.setPixmap(self.low_indicator)

        except Exception:
            logger.debug(
                f"{self.instrument}: Failed to read digital input from IOModule"
            )
            self.measurement_label.setPixmap(self.error_indicator)


class DigitalOutputChannel(QGroupBox):
    def __init__(
        self,
        app,
        instrument_name: str,
        channel: str,
        label: str,
        units: str,
        show_ID_labels: bool = True,
    ):

        if show_ID_labels:
            super().__init__(channel)
        else:
            super().__init__()

        self.togg_but = HCOnOffButton(
            app,
            instrument_name,
            f"CH{channel}_DIGITAL",
            label,
            show_icon=True,
            icon_checked="high_label.svg",
            icon_unchecked="low_label.svg",
        )

        self.edit_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.togg_but, 0, 0)
        self.main_layout.addWidget(self.togg_but.label, 0, 1)

        self.setLayout(self.main_layout)
