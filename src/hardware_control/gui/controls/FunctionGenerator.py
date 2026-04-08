"""
.. image:: /images/controls/FunctionGenerator.png
  :height: 350
"""

import logging

from PyQt6.QtWidgets import QGridLayout, QGroupBox, QPushButton

from ...base.gui_control import ValidatedControl
from ..widgets.hc_widgets import HCLineEdit, HCComboBox, HCOnOffButton


logger = logging.getLogger(__name__)


class FunctionGenerator(ValidatedControl, QGroupBox):
    """A GUI for two-channel Function/Waveform generators.

    Note
    ----
    Not all settings and commands of the instruments listed below are supported.

    See Also
    --------
    hardware_control.instruments.keysight.Keysight_33500B
    hardware_control.instruments.siglent.Siglent_SDG
    """

    # Required instrument parameters (validated automatically in __init__)
    _required_parameters = [
        "CH1_ENABLE",
        "CH1_FREQUENCY",
        "CH1_AMPLITUDE",
        "CH1_OFFSET",
        "CH1_WAVEFORM",
        "CH1_ENABLE_BURST",
        "CH1_BURST_MODE",
        "CH1_BURST_CYCLES",
        "CH1_BURST_PER",
        "CH1_TRIGGER_CHANNEL",
        "CH1_TRIGGER_LEVEL",
        "CH1_TRIGGER_EDGE",
        "CH1_TRIGGER_DELAY",
        "CH1_IMPEDANCE",
        "CH1_POLARITY",
        "CH2_ENABLE",
        "CH2_FREQUENCY",
        "CH2_AMPLITUDE",
        "CH2_OFFSET",
        "CH2_WAVEFORM",
        "CH2_ENABLE_BURST",
        "CH2_BURST_MODE",
        "CH2_BURST_CYCLES",
        "CH2_BURST_PER",
        "CH2_TRIGGER_CHANNEL",
        "CH2_TRIGGER_LEVEL",
        "CH2_TRIGGER_EDGE",
        "CH2_TRIGGER_DELAY",
        "CH2_IMPEDANCE",
        "CH2_POLARITY",
        "CH2_TRACK",
        "CH1_TRACK",
    ]

    def __init__(
        self,
        app,
        instrument_name: str,
        num_channels: int = 2,
        freq_unit: str = "MHz",
        widget_name: str = "",
        set_default_fxn=None,
    ):
        # Validation happens automatically in super().__init__
        # Pass widget_name to QGroupBox parent
        super().__init__(
            app, instrument_name, widget_name if widget_name else "Function Generator"
        )
        self.app = app
        self.instrument = instrument_name
        self.num_channels = num_channels
        self.freq_unit = freq_unit
        self.widget_name = widget_name
        self.set_default_fxn = set_default_fxn
        self.widgets = {}
        self.channels = range(1, self.num_channels + 1)

        for i in self.channels:
            enable = HCOnOffButton(
                self.app,
                self.instrument,
                f"CH{i}_ENABLE",
                label=f"CH{i} Enable Output",
                show_icon=True,
                text_checked="Turn Off",
                text_unchecked="Turn On",
            )
            frequency = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{i}_FREQUENCY",
                label=f"CH{i} Frequency ({self.freq_unit})",
            )
            amplitude = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{i}_AMPLITUDE",
                label=f"CH{i} Amplitude (Vpp)",
            )
            offset = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{i}_OFFSET",
                label=f"CH{i} Offset (V)",
            )
            waveform = HCComboBox(
                self.app,
                self.instrument,
                f"CH{i}_WAVEFORM",
                label=f"CH{i} Waveform",
                items=[
                    "Square",
                    "Sine",
                    "Triangle",
                    "Ramp",
                    "Pulse",
                    "Noise",
                    "PRBS",
                    "Arbitrary",
                    "DC",
                ],
            )
            burst_enable = HCComboBox(
                self.app,
                self.instrument,
                f"CH{i}_ENABLE_BURST",
                f"CH{i} Burst Enable",
                ["ON", "OFF"],
            )
            burst_mode = HCComboBox(
                self.app,
                self.instrument,
                f"CH{i}_BURST_MODE",
                f"CH{i} Burst Mode",
                ["TRIG", "GAT"],
            )
            num_cycles = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{i}_BURST_CYCLES",
                f"CH{i} Burst # of Cycles",
            )
            burst_period = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{i}_BURST_PER",
                f"CH{i} Burst Period (s)",
            )
            trigger = HCComboBox(
                self.app,
                self.instrument,
                f"CH{i}_TRIGGER_CHANNEL",
                f"CH{i} Trigger Channel",
                ["EXT", "IMM", "TIM", "MAN"],
            )
            level = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{i}_TRIGGER_LEVEL",
                f"CH{i} Trigger Level",
            )
            edge = HCComboBox(
                self.app,
                self.instrument,
                f"CH{i}_TRIGGER_EDGE",
                f"CH{i} Trigger Edge",
                ["POS", "NEG"],
            )
            delay = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{i}_TRIGGER_DELAY",
                f"CH{i} Trigger Delay (s)",
            )
            impedance = HCComboBox(
                self.app,
                self.instrument,
                f"CH{i}_IMPEDANCE",
                f"CH{i} Impedance",
                ["Hi-Z", "50-OHM"],
            )
            polarity = HCComboBox(
                self.app,
                self.instrument,
                f"CH{i}_POLARITY",
                f"CH{i} Polarity",
                ["NORM", "INV"],
            )

            self.widgets[i] = [
                enable,
                frequency,
                amplitude,
                offset,
                waveform,
                burst_enable,
                burst_mode,
                num_cycles,
                burst_period,
                trigger,
                level,
                edge,
                delay,
                impedance,
                polarity,
            ]

            if i == 2:
                self.track2 = HCComboBox(
                    self.app,
                    self.instrument,
                    "CH2_TRACK",
                    "CH1 Track CH2",
                    ["OFF", "ON", "INV"],
                )
                self.app.add_hook(
                    self.instrument,
                    "CH2_TRACK",
                    "pre_set_hooks",
                    lambda x: self.set_tracking_hook("CH2_TRACK", x),
                )
                self.track1 = HCComboBox(
                    self.app,
                    self.instrument,
                    "CH1_TRACK",
                    "CH2 Track CH1",
                    ["OFF", "ON", "INV"],
                )
                self.app.add_hook(
                    self.instrument,
                    "CH1_TRACK",
                    "pre_set_hooks",
                    lambda x: self.set_tracking_hook("CH1_TRACK", x),
                )

                self.widgets[i].append(self.track2)
                self.widgets[i].append(self.track1)

        # All parameters auto-registered through HC widgets
        # No commands or parameters used directly

        if self.set_default_fxn is not None:
            default_btn = QPushButton("Set Defaults")
            default_btn.clicked.connect(self.set_default_fxn)

        self.grid = QGridLayout()
        for channel in self.channels:
            for i, w in enumerate(self.widgets[channel]):
                label_col = 2 * (channel - 1)
                widget_col = 2 * channel - 1
                self.grid.addWidget(w.label, i, label_col)
                self.grid.addWidget(w, i, widget_col)
        if self.set_default_fxn is not None:
            self.grid.addWidget(
                default_btn,
                len(self.widgets[self.channels[-1]]),
                2 * self.channels[-1] - 1,
            )
        self.setLayout(self.grid)

        # Register parameters for automatic updates
        self.default_update_readout()

    def default_update_readout(self):
        """Register parameters for automatic updates."""
        for channel in self.channels:
            self.app.add_auto_update_instrument_parameter(
                self.instrument, f"CH{channel}_ENABLE"
            )

    def set_tracking_hook(self, setting, value):
        """Allow one channel to mirror the parameter values of another channel."""
        if setting == "CH2_TRACK":
            settings_list = self.widgets[1]
        elif setting == "CH1_TRACK":
            settings_list = self.widgets[2]
            # Don't want to remove tracking buttons
            if self.track2 in settings_list:
                settings_list.remove(self.track2)
                settings_list.remove(self.track1)

        for w in settings_list:
            if value == "OFF":
                w.setEnabled(True)
            elif value in ("ON", "INV"):
                w.setEnabled(False)
            else:
                logger.warning(
                    f"'{self.instrument}': Unrecognized value in parameter '{setting}'."
                )

        return value
