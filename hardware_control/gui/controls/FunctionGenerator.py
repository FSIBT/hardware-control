"""
    .. image:: /images/controls/FunctionGenerator.png
      :height: 350
"""
import logging

from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
)

from ..widgets.hc_widgets import HCLineEdit, HCComboBox


logger = logging.getLogger(__name__)


class FunctionGenerator(QGroupBox):
    """A GUI for two-channel Function/Waveform generators.

    Note
    ----
    Not all settings and commands of the instruments listed below are supported.

    See Also
    --------
    hardware_control.instruments.keysight.Keysight_33500B
    hardware_control.instruments.siglent.Siglent_SDG
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        name: str = "AWG Control",
        num_channels: int = 2,
    ):
        super().__init__(name)
        self.app = app
        self.instrument = instrument_name
        self.name = name
        self.num_channels = num_channels

        self.frequency = HCLineEdit(
            self.app, self.instrument, "CH1_FREQUENCY", label="CH1 Frequency (MHz)"
        )
        self.amplitude = HCLineEdit(
            self.app, self.instrument, "CH1_AMPLITUDE", label="CH1 Amplitude (Vpp)"
        )
        self.offset = HCLineEdit(
            self.app, self.instrument, "CH1_OFFSET", label="CH1 Offset (V)"
        )
        self.waveform = HCComboBox(
            self.app,
            self.instrument,
            "CH1_WAVEFORM",
            label="CH1 Waveform",
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
        self.burst_enable = HCComboBox(
            self.app,
            self.instrument,
            "CH1_ENABLE_BURST",
            "CH1 Burst Enable",
            ["ON", "OFF"],
        )
        self.burst_mode = HCComboBox(
            self.app,
            self.instrument,
            "CH1_BURST_MODE",
            "CH1 Burst Mode",
            ["TRIG", "GAT"],
        )
        self.num_cycles = HCLineEdit(
            self.app,
            self.instrument,
            "CH1_BURST_CYCLES",
            "CH1 Burst # of Cycles",
        )
        self.burst_period = HCLineEdit(
            self.app,
            self.instrument,
            "CH1_BURST_PER",
            "CH1 Burst Period (s)",
        )
        self.enable = HCComboBox(
            self.app,
            self.instrument,
            "CH1_ENABLE",
            "CH1 Enable Output",
            ["True", "False"],
        )
        self.trigger = HCComboBox(
            self.app,
            self.instrument,
            "CH1_TRIGGER_CHANNEL",
            "CH1 Trigger Channel",
            ["EXT", "IMM", "TIM", "MAN"],
        )
        self.level = HCLineEdit(
            self.app,
            self.instrument,
            "CH1_TRIGGER_LEVEL",
            "CH1 Trigger Level",
        )
        self.edge = HCComboBox(
            self.app,
            self.instrument,
            "CH1_TRIGGER_EDGE",
            "CH1 Trigger Edge",
            ["POS", "NEG"],
        )
        self.delay = HCLineEdit(
            self.app,
            self.instrument,
            "CH1_TRIGGER_DELAY",
            "CH1 Trigger Delay (s)",
        )
        self.impedance = HCComboBox(
            self.app,
            self.instrument,
            "CH1_IMPEDANCE",
            "CH1 Impedance",
            ["Hi-Z", "50-OHM"],
        )
        self.polarity = HCComboBox(
            self.app,
            self.instrument,
            "CH1_POLARITY",
            "CH1 Polarity",
            ["NORM", "INV"],
        )
        if self.num_channels >= 2:
            self.frequency2 = HCLineEdit(
                self.app, self.instrument, "CH2_FREQUENCY", "CH2 Frequency (MHz)"
            )
            self.amplitude2 = HCLineEdit(
                self.app, self.instrument, "CH2_AMPLITUDE", "CH2 Amplitude (Vpp)"
            )
            self.offset2 = HCLineEdit(
                self.app, self.instrument, "CH2_OFFSET", "CH2 Offset (V)"
            )
            self.waveform2 = HCComboBox(
                self.app,
                self.instrument,
                "CH2_WAVEFORM",
                "CH2 Waveform",
                [
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
            self.burst_enable2 = HCComboBox(
                self.app,
                self.instrument,
                "CH2_ENABLE_BURST",
                "CH2 Burst Enable",
                ["ON", "OFF"],
            )
            self.burst_mode2 = HCComboBox(
                self.app,
                self.instrument,
                "CH2_BURST_MODE",
                "CH2 Burst Mode",
                ["TRIG", "GAT"],
            )
            self.num_cycles2 = HCLineEdit(
                self.app,
                self.instrument,
                "CH2_BURST_CYCLES",
                "CH2 Burst # of Cycles",
            )
            self.burst_period2 = HCLineEdit(
                self.app,
                self.instrument,
                "CH2_BURST_PER",
                "CH2 Burst Period (s)",
            )
            self.enable2 = HCComboBox(
                self.app,
                self.instrument,
                "CH2_ENABLE",
                "CH2 Enable Output On/Off",
                ["True", "False"],
            )
            self.trigger2 = HCComboBox(
                self.app,
                self.instrument,
                "CH2_TRIGGER_CHANNEL",
                "CH2 Trigger Channel",
                ["EXT", "IMM", "TIM", "MAN"],
            )
            self.level2 = HCLineEdit(
                self.app,
                self.instrument,
                "CH2_TRIGGER_LEVEL",
                "CH2 Trigger Level",
            )
            self.edge2 = HCComboBox(
                self.app,
                self.instrument,
                "CH2_TRIGGER_EDGE",
                "CH2 Trigger Edge",
                ["POS", "NEG"],
            )
            self.delay2 = HCLineEdit(
                self.app,
                self.instrument,
                "CH2_TRIGGER_DELAY",
                "CH2 Trigger Delay (s)",
            )
            self.impedance2 = HCComboBox(
                self.app,
                self.instrument,
                "CH2_IMPEDANCE",
                "CH2 Impedance",
                ["Hi-Z", "50-OHM"],
            )
            self.polarity2 = HCComboBox(
                self.app,
                self.instrument,
                "CH2_POLARITY",
                "CH2 Polarity",
                ["NORM", "INV"],
            )
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

        self.grid = QGridLayout()

        self.widgets = [
            self.frequency,
            self.amplitude,
            self.offset,
            self.waveform,
            self.burst_enable,
            self.burst_mode,
            self.num_cycles,
            self.burst_period,
            self.enable,
            self.trigger,
            self.level,
            self.edge,
            self.delay,
            self.impedance,
            self.polarity,
        ]
        for i, w in enumerate(self.widgets):
            self.grid.addWidget(w.label, i, 0)
            self.grid.addWidget(w, i, 1)

        if self.num_channels >= 2:
            self.widgets2 = [
                self.frequency2,
                self.amplitude2,
                self.offset2,
                self.waveform2,
                self.burst_enable2,
                self.burst_mode2,
                self.num_cycles2,
                self.burst_period2,
                self.enable2,
                self.trigger2,
                self.level2,
                self.edge2,
                self.delay2,
                self.impedance2,
                self.polarity2,
                self.track2,
                self.track1,
            ]
            for i, w in enumerate(self.widgets2):
                self.grid.addWidget(w.label, i, 2)
                self.grid.addWidget(w, i, 3)

        self.setLayout(self.grid)

    def set_tracking_hook(self, setting, value):
        """Allow one channel to mirror the parameter values of another channel."""
        if setting == "CH2_TRACK":
            settings_list = self.widgets
        elif setting == "CH1_TRACK":
            settings_list = self.widgets2
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
                    f"'{self.instrument}': Unrecognized value in '{self.name}' parameter '{setting}'."
                )

        return value
