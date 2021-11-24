"""
    .. image:: /images/controls/MultiPowerSupply.png
"""
import logging
from typing import Optional, List

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QPushButton,
    QLabel,
    QWidget,
    QGridLayout,
    QGroupBox,
    QSpacerItem,
    QSizePolicy,
)

from ..widgets import (
    HCLineEdit,
    HCLabel,
    HCOnOffButton,
    HCHeader,
    HCOnOffIndicator,
)

from ...base.hooks import format_float

logger = logging.getLogger(__name__)

LABEL_MIN_WIDTH = 15
DISP_DECIMAL_PLACES = 1

status_labels = {
    "RAMPING_UP": "Ramping Up",
    "RAMPING_DOWN": "Ramping Down",
    "OVER_CURRENT": "Over Current",
    "OVER_VOLTAGE": "Over Voltage",
    "UNDER_VOLTAGE": "Under Voltage",
    "MAX_VOLTAGE": "Max Voltage",
    "TRIPPED": "Tripped",
    "OVER_POWER": "Over Power",
    "OVER_TEMPERATURE": "Over Temperature",
    "DISABLED": "Disabled",
    "KILL": "Kill",
    "INTERLOCKED": "Interlocked",
    "CALIBRATION_ERROR": "Calibration Error",
}


class MultiPowerSupply(QGroupBox):
    """A generic control program for a multi-channel power supply.

    Parameters
    ----------
    app : hardware_control.App
        The main app instance
    instrument_name: str
        The name of the power supply instrument
    channels : list
        A list of channels to be shown in the control program
    widget_name : str
        Name shown on the control program; default is 'Multi_Channel_PSU'
    channel_names : list
        An optional list of strings to be used as the channel names; if no
        list is given the channels are named according to their numbers
    show_VI_limits : bool
        Option to show the maximum allowed voltage and current for each channel
    show_status_panel : bool
        Option to show the status panel; this option only works with Caen
        power supply units
    enable_power_buttons : str
        Power buttons option; 'individual' creates one enable button per
        channel), 'both' creates individual channel enable buttons
        and an enable button for all channels, and 'none' will not create any
    num_columns : int
        Number of columns to place the power supply channel widgets in

    See Also
    --------
    hardware_control.instruments.caen.Caen_RSeries
    hardware_control.instruments.rigol.Rigol_DP832
    hardware_control.instruments.tdkl.TDKL_GenH
    hardware_control.instruments.keysight.Keysight_36300
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        channels: List,
        widget_name: str = "Multi_Channel_PSU",
        channel_names: Optional[List] = None,
        show_VI_limits: bool = False,
        show_status_panel: bool = False,
        enable_power_buttons: str = "none",
        num_columns: int = -1,
    ):
        super().__init__(widget_name)

        self.app = app
        self.instrument = instrument_name
        self.channels = channels
        self.channel_names = channel_names
        self.show_VI_limits = show_VI_limits
        self.show_status_panel = show_status_panel
        self.enable_power_buttons = enable_power_buttons
        # Default number of columns is number of channels
        if num_columns == -1:
            num_columns = len(channels)

        # Create a widget for each channel and push them into a row
        self.channel_widgets = []
        self.channel_box = QGroupBox()
        self.channel_box_layout = QGridLayout()
        for idx, channel in enumerate(self.channels):
            channel_widget = PowerSupplyChannel(
                self.app,
                self.instrument,
                channel,
                self.show_VI_limits,
                self.show_status_panel,
                self.enable_power_buttons,
            )
            if self.channel_names is not None:
                channel_widget.set_label(self.channel_names[idx])
            self.channel_widgets.append(channel_widget)
            self.channel_box_layout.addWidget(
                self.channel_widgets[-1],
                int(idx / num_columns),
                idx % num_columns,
            )
        self.channel_box.setLayout(self.channel_box_layout)

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.channel_box, 0, 0, 1, 3)

        # Potentially add buttons that can enable/disable all channels
        # These buttons are placed below the row of channel widgets
        if self.enable_power_buttons == "both":
            self.all_enable_but = QPushButton("Enable All")
            self.all_enable_but.clicked.connect(self.enable_all)
            self.all_disable_but = QPushButton("Disable All")
            self.all_disable_but.clicked.connect(self.disable_all)

            self.all_spacer = QSpacerItem(
                10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
            )
            self.master_layout.addItem(self.all_spacer, 1, 0, 1, 1)
            self.master_layout.addWidget(self.all_enable_but, 1, 1)
            self.master_layout.addWidget(self.all_disable_but, 1, 2)

        self.setLayout(self.master_layout)

        # Create timer to query instrument
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.app.globalRefreshRate)

    def enable_all(self):
        """Enable all channels."""
        for channel in self.channels:
            self.app.set_instrument_parameter(
                self.instrument, f"CH{channel}_ENABLE", True
            )

    def disable_all(self):
        """Disable all channels."""
        for channel in self.channels:
            self.app.set_instrument_parameter(
                self.instrument, f"CH{channel}_ENABLE", False
            )

    def update_readout(self):
        """Query the instrument for current readout data and push it to the GUI."""
        # Update readout data for each parameter
        for cw in self.channel_widgets:
            self.app.update_instrument_parameter(
                self.instrument, f"CH{cw.channel}_ENABLE"
            )
            self.app.update_instrument_parameter(
                self.instrument, f"CH{cw.channel}_I_SET"
            )
            self.app.update_instrument_parameter(
                self.instrument, f"CH{cw.channel}_V_SET"
            )
            self.app.update_instrument_parameter(
                self.instrument, f"CH{cw.channel}_V_OUT"
            )
            self.app.update_instrument_parameter(
                self.instrument, f"CH{cw.channel}_I_OUT"
            )
            if self.show_VI_limits:
                self.app.update_instrument_parameter(
                    self.instrument, f"CH{cw.channel}_V_MAX"
                )
                self.app.update_instrument_parameter(
                    self.instrument, f"CH{cw.channel}_I_MAX"
                )

            # Calculate and update the value of the channel's power out
            cw.V_out_value = self.app.get_instrument_parameter(
                self.instrument, f"CH{cw.channel}_V_OUT"
            )
            cw.I_out_value = self.app.get_instrument_parameter(
                self.instrument, f"CH{cw.channel}_I_OUT"
            )
            if None not in [cw.V_out_value, cw.I_out_value]:
                cw.Power_out_value.setText(
                    f"{round(float(cw.V_out_value) * float(cw.I_out_value), 3)} W"
                )

            # Status parameters
            if self.show_status_panel:
                for bit_name in status_labels:
                    self.app.update_instrument_parameter(
                        self.instrument,
                        f"CH{cw.channel}_{bit_name}",
                    )

    def set_maxI(self, channel: int, maxI: float):
        """Set an internal limit for the current from channel 'X'."""
        self.app.set_instrument_parameter(
            self.instrument, f"CH{channel}_I_MAX", str(maxI)
        )

    def set_maxV(self, channel: int, maxV: float):
        """Set an internal limit for the voltage from channel 'X'."""
        self.app.set_instrument_parameter(
            self.instrument, f"CH{channel}_V_MAX", str(maxV)
        )

    def set_channel_label(self, channel: int, label: str):
        """Set a channel label to a new custom label."""
        for cw in self.channel_widgets:
            if cw.channel == channel:
                cw.set_label(label)


class PowerSupplyChannel(QWidget):
    """A Qt-widget that implements controls for a single channel of a power supply."""

    def __init__(
        self,
        app,
        instrument_name: str,
        channel: int,
        show_VI_limits: bool = False,
        show_status_panel: bool = False,
        power_button: bool = False,
    ) -> None:

        super().__init__()

        self.app = app
        self.instrument = instrument_name
        self.channel = channel

        # Style options
        self.show_VI_limits = show_VI_limits

        if power_button in ["individual", "both"]:
            self.power_button = True
        elif power_button != "none":
            logger.error(
                f"{self.instrument}: Received the following invalid value for MultiPowerSupply power_button attribute: {power_button}."
            )
        else:
            self.power_button = False

        # Create a header for the channel widget
        if self.channel <= 20:
            self.channel_label = HCHeader(f"channel_{self.channel+1}.png")
        else:
            self.set_label(f"Channel {self.channel}")

        # Create readout and update parameters for the channel widget

        self.Voltage_out = HCLabel(
            self.app,
            self.instrument,
            f"CH{self.channel}_V_OUT",
            label="V Out",
            unit="V",
        )
        self.Current_out = HCLabel(
            self.app,
            self.instrument,
            f"CH{self.channel}_I_OUT",
            label="I Out",
            unit="A",
        )

        # Power out is calculated from V_out and I_out. See MultiPowerSupply.update_readout() above.
        self.Power_out_label = QLabel("P Out:")
        self.Power_out_value = QLabel("----")
        self.Power_out_value.setAlignment(QtCore.Qt.AlignLeft)

        # Potentially set limits on how hight to set voltage and current
        if self.show_VI_limits:
            self.Voltage_max = HCLabel(
                self.app,
                self.instrument,
                f"CH{self.channel}_V_MAX",
                label="V Max",
                unit="V",
            )
            self.Current_max = HCLabel(
                self.app,
                self.instrument,
                f"CH{self.channel}_I_MAX",
                label="I Max",
                unit="A",
            )

        self.Voltage = HCLineEdit(
            self.app,
            self.instrument,
            f"CH{self.channel}_V_SET",
            "Voltage (V)",
        )

        self.Current = HCLineEdit(
            self.app,
            self.instrument,
            f"CH{self.channel}_I_SET",
            "Current (A)",
        )
        self.app.add_hook(
            self.instrument,
            f"CH{self.channel}_I_SET",
            "post_read_hooks",
            format_float(".3e"),
        )

        self.enabled_but = HCOnOffButton(
            self.app,
            self.instrument,
            f"CH{self.channel}_ENABLE",
            label_align="right",
            text_checked="Disable",
            text_unchecked="Enable",
        )
        self.enabled_but.setCheckable(False)

        self.enabled_ind = HCOnOffIndicator(
            self.app,
            self.instrument,
            f"CH{self.channel}_ENABLE",
            label_align="right",
            show_icon=True,
            icon_checked="green_ind.svg",
            icon_unchecked="red_ind.svg",
        )

        # Qt Layout for a readout and update parameters of the channel widget
        self.readout_grid = QGridLayout()

        self.readout_grid.addWidget(self.Voltage.label, 0, 0)
        self.readout_grid.addWidget(self.Voltage, 0, 1)
        self.readout_grid.addWidget(self.Voltage_out.label, 1, 0)
        self.readout_grid.addWidget(self.Voltage_out, 1, 1)

        self.readout_grid.addWidget(self.Current.label, 0, 2)
        self.readout_grid.addWidget(self.Current, 0, 3)
        self.readout_grid.addWidget(self.Current_out.label, 1, 2)
        self.readout_grid.addWidget(self.Current_out, 1, 3)

        if self.show_VI_limits:
            self.readout_grid.addWidget(self.Voltage_max.label, 3, 0)
            self.readout_grid.addWidget(self.Voltage_max, 3, 1)
            self.readout_grid.addWidget(self.Current_max.label, 3, 2)
            self.readout_grid.addWidget(self.Current_max, 3, 3)
            added_row = 1
        else:
            added_row = 0

        self.readout_grid.addWidget(self.Power_out_label, 3 + added_row, 2)
        self.readout_grid.addWidget(self.Power_out_value, 3 + added_row, 3)

        if self.power_button:
            self.readout_grid.addWidget(self.enabled_but, 3 + added_row, 0)
            self.readout_grid.addWidget(self.enabled_ind, 3 + added_row, 1)

        # Combine channel header and readout/update parameters in a master channel layout
        self.channel_layout = QGridLayout()
        self.channel_layout.addWidget(self.channel_label, 0, 0)
        self.channel_layout.addLayout(self.readout_grid, 1, 0)

        # Potentially add a status panel to the master channel layout
        if show_status_panel:
            self.status_panel = QGroupBox()
            self.status_grid = QGridLayout()
            row_num = 0
            col_num = 0
            for parameter, status_label in status_labels.items():
                indicator = HCOnOffIndicator(
                    self.app,
                    self.instrument,
                    f"CH{self.channel}_{parameter}",
                    status_label,
                    label_align="right",
                    show_icon=True,
                    icon_checked="green_ind.svg",
                    icon_unchecked="red_ind.svg",
                    tooltip=status_label,
                )
                indicator.setToolTip(status_label)
                self.status_grid.addWidget(indicator, row_num % 2, col_num)
                row_num += 1
                if row_num != 0 and row_num % 2 == 0:
                    col_num += 1
            self.status_panel.setLayout(self.status_grid)

            self.channel_layout.addWidget(self.status_panel, 2, 0)

        self.channel_layout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.setLayout(self.channel_layout)

    def set_label(self, label: str):
        """Set a label header for the channel."""
        align_left_center = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        self.channel_label.setText(f"{label}")
        self.channel_label.setFont(QFont("Arial", 20))
        self.channel_label.setAlignment(align_left_center)
