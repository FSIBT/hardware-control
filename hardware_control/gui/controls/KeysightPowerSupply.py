"""
    .. image:: /images/controls/KeysightPowerSupply.png
"""
from typing import List, Optional
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QGridLayout
from ..widgets import HCFixedLabel, HCLineEdit, HCOnOffButton, HCGridLayout


class ChannelDisplay(QVBoxLayout):
    """Widget for individual Keysight Power Supply channels."""

    def __init__(
        self,
        app,
        instrument_name: str,
        channel: int,
        color: str,
        set_voltage_option: bool = False,
        set_current_option: bool = False,
    ):
        super().__init__()

        self.app = app
        self.instrument = instrument_name
        self.color = color
        self.set_voltage_option = set_voltage_option
        self.set_current_option = set_current_option

        if self.set_current_option or self.set_voltage_option:
            init_label = "+000.000000000 xX"
        else:
            init_label = "+000.0000 xX"

        self.on_off = HCOnOffButton(
            self.app,
            self.instrument,
            f"CH{channel}_ENABLE",
            label=None,
            show_icon=True,
        )
        self.addWidget(self.on_off)

        # Channel voltage readout
        self.voltage = HCFixedLabel(
            self.app,
            self.instrument,
            f"CH{channel}_V_OUT",
            init_label=init_label,
            unit="V",
            color=self.color,
            label_align="right",
        )
        self.addWidget(self.voltage)

        # Channel current readout
        self.current = HCFixedLabel(
            self.app,
            self.instrument,
            f"CH{channel}_I_OUT",
            init_label=init_label,
            unit="A",
            color=self.color,
            label_align="right",
        )
        self.addWidget(self.current)

        # OPTIONAL: Channel voltage setter
        if set_voltage_option:
            self.set_voltage = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{channel}_V_SET",
                "Set Voltage",
            )
            self.set_voltage_layout = HCGridLayout([self.set_voltage])
            self.addLayout(self.set_voltage_layout)

        # OPTIONAL: Channel current setter
        if set_current_option:
            self.set_current = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{channel}_I_SET",
                "Set Current",
            )
            self.set_current_layout = HCGridLayout([self.set_current])
            self.addLayout(self.set_current_layout)

        self.addStretch(1)


class KeysightPowerSupply(QGroupBox):
    """Control program for a Keysight Power Supply.

    See Also
    --------
    hardware_control.instruments.keysight.Keysight_36300
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        channels: List,
        channel_colors: List,
        set_voltage_channels: Optional[List] = None,
        set_current_channels: Optional[List] = None,
        widget_name: str = "Keysight Power Supply",
    ):
        super().__init__(widget_name)
        self.app = app
        self.instrument = instrument_name
        self.channels = channels
        self.channel_colors = channel_colors
        self.set_voltage_channels = (
            set_voltage_channels if set_voltage_channels is not None else []
        )
        self.set_current_channels = (
            set_current_channels if set_current_channels is not None else []
        )

        # Create a channel widgets for all channels
        self.channel_widgets = []
        for idx, channel in enumerate(channels):
            self.channel_widgets.append(
                ChannelDisplay(
                    self.app,
                    self.instrument,
                    idx + 1,
                    self.channel_colors[idx],
                    set_voltage_option=channel in self.set_voltage_channels,
                    set_current_option=channel in self.set_current_channels,
                )
            )

        # Create "Enable All" and "Disable All" buttons
        self.all_enable_but = QPushButton("Enable All")
        self.all_enable_but.clicked.connect(self.enable_all)
        self.all_disable_but = QPushButton("Disable All")
        self.all_disable_but.clicked.connect(self.disable_all)

        # Allow negative outputs
        self.app.call_instrument_command(self.instrument, "ALLOW_NEG_OUTPUT")
        # Set protection levels on channels
        self.app.set_instrument_parameter(self.instrument, "CH2_V_PROT", 6)
        self.app.set_instrument_parameter(self.instrument, "CH3_V_PROT", -6)

        self.hbox = QVBoxLayout()
        # Add channel widgets to the control program
        self.channeldisplay = QGridLayout()
        for i, cw in enumerate(self.channel_widgets):
            self.channeldisplay.addLayout(cw, 1, i)
        self.hbox.addLayout(self.channeldisplay)
        # Add "Enable All" and "Disable All" buttons to the control program
        self.hbox.addWidget(self.all_enable_but)
        self.hbox.addWidget(self.all_disable_but)
        self.setLayout(self.hbox)

        self.default_update_readout()

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

    def default_update_readout(self):
        """Register values for automatic updates."""
        for channel in self.channels:
            tmp = [f"CH{channel}_ENABLE", f"CH{channel}_I_OUT", f"CH{channel}_V_OUT"]
            if self.channel_widgets[channel - 1].set_voltage_option:
                tmp.append(f"CH{channel}_V_SET")
            if self.channel_widgets[channel - 1].set_current_option:
                tmp.append(f"CH{channel}_I_SET")

            for parameter in tmp:
                self.app.add_auto_update_instrument_parameter(
                    self.instrument, parameter
                )
