import logging

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
from typing import List

from ...utility import remove_end_carriage_return
from ..widgets import (
    setButtonState,
    load_icon,
    HCLineEdit,
    HCLabel,
    HCOnOffButton,
    HCHeader,
)

logger = logging.getLogger(__name__)

LABEL_MIN_WIDTH = 15
DISP_DECIMAL_PLACES = 1


class MultiPowerSupply(QGroupBox):
    """A GUI for a multi channel power supply.

    Example of a 3 channel power supply:

    .. image:: /images/controls/MultiPowerSupply-3ch.png
      :height: 200

    Note: enable_power_buttons parameter accepts one of three argument –
    "none" (for no enable buttons), "individual" (for one enable button per
    channel), or "both" (for individual channel enable buttons and an enable
    button for all channels)

    See Also
    --------
    hardware_control.instruments.caen.Caen_14xxET
    hardware_control.instruments.rigol.Rigol_DP832
    hardware_control.instruments.tdkl.TDKL_GenH
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        channels: List,
        name: str = "Multi_Channel_PSU",
        show_VI_limits: bool = False,
        show_status_panel: bool = False,
        enable_power_buttons: str = "none",
    ):
        super().__init__(name)

        self.app = app
        self.instrument = instrument_name
        self.channels = channels
        self.show_status_panel = show_status_panel
        self.enable_power_buttons = enable_power_buttons

        # Create a widget for each channel and push them into a row
        self.channel_widgets = []
        self.channel_box = QGroupBox()
        self.channel_box_layout = QGridLayout()
        for idx, channel in enumerate(self.channels):
            self.channel_widgets.append(
                PowerSupplyChannel(
                    self.app,
                    self.instrument,
                    channel,
                    show_VI_limits,
                    self.show_status_panel,
                    self.enable_power_buttons,
                )
            )
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, idx)
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
        """Enables all channels."""
        for channel in self.channels:
            self.app.set_instrument_parameter(
                self.instrument, f"CH{channel}_ENABLE", True
            )

    def disable_all(self):
        """Disables all channels."""
        for channel in self.channels:
            self.app.set_instrument_parameter(
                self.instrument, f"CH{channel}_ENABLE", False
            )

    def update_readout(self):
        """Queries the instrument for current readout data and pushes it to the GUI"""
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
            self.app.update_instrument_parameter(
                self.instrument, f"CH{cw.channel}_V_MAX"
            )
            self.app.update_instrument_parameter(
                self.instrument, f"CH{cw.channel}_I_MAX"
            )

            # Calculate and update the value of the channel's power out
            V_out_value = self.app.get_instrument_parameter(
                self.instrument, f"CH{cw.channel}_V_OUT"
            )
            I_out_value = self.app.get_instrument_parameter(
                self.instrument, f"CH{cw.channel}_I_OUT"
            )
            if None not in [V_out_value, I_out_value]:
                cw.Power_out_value.setText(
                    f"{float(V_out_value) * float(I_out_value)} W"
                )

            # If status panel is enabled, update it
            if self.show_status_panel:
                try:
                    if float(Iout) >= float(Iset) * 0.95:
                        self.CC_indic.setPixmap(self.ccurr_ind)
                    else:
                        self.CC_indic.setPixmap(self.cvolt_ind)
                except:
                    logger.error(f"{self.instrument}: Error updating CC Indicator")

    def set_maxI(self, channel: int, maxI: float):
        """Sets an internal limit for the current from channel 'n'."""
        self.app.set_instrument_parameter(
            self.instrument, f"CH{channel}_I_MAX", str(maxI)
        )

    def set_maxV(self, channel: int, maxV: float):
        """Sets an internal limit for the voltage from channel 'n'."""
        self.app.set_instrument_parameter(
            self.instrument, f"CH{channel}_V_MAX", str(maxV)
        )

    def set_channel_label(self, channel: int, label: str):
        """Sets a channel label to a new custom value"""
        for cw in self.channel_widgets:
            if cw.channel == channel:
                cw.set_label(label)


class PowerSupplyChannel(QWidget):
    """A Qt-widget that implements controls for a single channel of a power supply"""

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

        align_left_center = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        # Create a header for the channel widget
        if self.channel <= 20:
            self.channel_label = HCHeader(f"channel_{self.channel}.png")
        else:
            self.set_label(f"Channel {self.channel}")

        # Create readout and update parameters for the channel widget
        self.Voltage_set = HCLabel(
            self.app,
            self.instrument,
            f"CH{self.channel}_V_SET",
            label="V Set",
            label_align="right",
            unit="V",
        )
        self.Current_set = HCLabel(
            self.app,
            self.instrument,
            f"CH{self.channel}_I_SET",
            label="I Set",
            label_align="right",
            unit="A",
        )
        self.Voltage_out = HCLabel(
            self.app,
            self.instrument,
            f"CH{self.channel}_V_OUT",
            label="V Out",
            label_align="right",
            unit="V",
        )
        self.Current_out = HCLabel(
            self.app,
            self.instrument,
            f"CH{self.channel}_I_OUT",
            label="I Out",
            label_align="right",
            unit="A",
        )

        # Power out is calculated from V_out and I_out. See MultiPowerSupply.update_readout() above.
        self.Power_out_label = QLabel("P Out:")
        self.Power_out_value = QLabel("----")
        self.Power_out_value.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Potentially set limits on how hight to set voltage and current
        if self.show_VI_limits:
            self.Voltage_max = HCLabel(
                self.app,
                self.instrument,
                f"CH{self.channel}_V_MAX",
                label="V Max",
                label_align="right",
                unit="V",
            )
            self.Current_max = HCLabel(
                self.app,
                self.instrument,
                f"CH{self.channel}_I_MAX",
                label="I Max",
                label_align="right",
                unit="A",
            )

        self.Voltage = HCLineEdit(
            self.app,
            self.instrument,
            f"CH{self.channel}_V_SET",
            "Voltage (V)",
            label_align="right",
        )

        self.Current = HCLineEdit(
            self.app,
            self.instrument,
            f"CH{self.channel}_I_SET",
            "Current (A)",
            label_align="right",
        )

        self.enabled_but = HCOnOffButton(
            self.app,
            self.instrument,
            f"CH{self.channel}_ENABLE",
            on_text="Enabled",
            off_text="Disabled",
        )

        # Qt Layout for a readout and update parameters of the channel widget
        self.readout_grid = QGridLayout()
        self.readout_grid.addWidget(self.Voltage_set.label, 0, 0)
        self.readout_grid.addWidget(self.Voltage_set, 0, 1)
        self.readout_grid.addWidget(self.Current_set.label, 1, 0)
        self.readout_grid.addWidget(self.Current_set, 1, 1)

        self.readout_grid.addWidget(self.Voltage_out.label, 0, 2)
        self.readout_grid.addWidget(self.Voltage_out, 0, 3)
        self.readout_grid.addWidget(self.Current_out.label, 1, 2)
        self.readout_grid.addWidget(self.Current_out, 1, 3)

        self.readout_grid.addWidget(self.Power_out_label, 2, 2)
        self.readout_grid.addWidget(self.Power_out_value, 2, 3)

        if self.show_VI_limits:
            self.readout_grid.addWidget(self.Voltage_max.label, 3, 0)
            self.readout_grid.addWidget(self.Voltage_max, 3, 1)
            self.readout_grid.addWidget(self.Current_max.label, 3, 2)
            self.readout_grid.addWidget(self.Current_max, 3, 3)
            added_row = 1
        else:
            added_row = 0

        self.readout_grid.addWidget(self.Voltage.label, 3 + added_row, 0)
        self.readout_grid.addWidget(self.Voltage, 3 + added_row, 1)
        self.readout_grid.addWidget(self.Current.label, 4 + added_row, 0)
        self.readout_grid.addWidget(self.Current, 4 + added_row, 1)
        if self.power_button:
            self.readout_grid.addWidget(self.enabled_but, 5 + added_row, 0)

        # Combine channel header and readout/update parameters in a master channel layout
        self.channel_layout = QGridLayout()
        self.channel_layout.addWidget(self.channel_label, 0, 0)
        self.channel_layout.addLayout(self.readout_grid, 1, 0)

        # Potentially add a status panel to the master channel layout
        if show_status_panel:
            self.ccurr_ind = load_icon("ccurrent_label.svg")
            self.cvolt_ind = load_icon("cvoltage_label.svg")
            self.na_ind = load_icon("na_label.svg")

            self.CC_ind_label = QLabel("CC:")
            self.CC_indic = QLabel()
            self.CC_indic.setPixmap(self.na_ind)

            self.status_panel = QGroupBox()
            self.status_grid = QGridLayout()
            self.status_grid.addWidget(self.CC_ind_label, 0, 1)
            self.status_grid.addWidget(self.CC_indic, 1, 1)
            self.status_panel.setLayout(self.status_grid)

            self.channel_layout.addWidget(self.status_panel, 2, 0)
        self.setLayout(self.channel_layout)

    def set_label(self, label: str):
        """Sets a label header"""
        align_left_center = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        self.channel_label.setText(f"{label}")
        self.channel_label.setFont(QFont("Arial", 20))
        self.channel_label.setAlignment(align_left_center)
