import logging

from PyQt5 import QtCore
from PyQt5.QtGui import QDoubleValidator, QIcon
from PyQt5.QtWidgets import (
    QLineEdit,
    QPushButton,
    QLabel,
    QWidget,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QComboBox,
)

from ..widgets import setButtonState, load_icon
from ..widgets.hc_widgets import HCLineEdit, HCComboBox


logger = logging.getLogger(__name__)


class FunctionGenerator(QGroupBox):
    """A GUI for Function/Waveform generators.

    Example of a two channel function generator:

    .. image:: /images/controls/FunctionGenerator-2ch.png
      :height: 200

    Note
    ----
    Not all settings and command of the instrument below are supported.

    See Also
    --------
    hardware_control.backends.keysight.Keysight_36300.Keysight_36300
    hardware_control.backends.siglent.Siglent_SDG.Siglent_SDG

    """

    def __init__(
        self,
        app,
        backend,
        name: str = "AWG Control",
        num_channels: int = 2,
        lock_until_sync=False,
    ):

        super().__init__(app, name, backend, lock_until_sync)

        self.num_channels = num_channels

        self.setup_UI()
        self.autolayout_grid(ncols=2)

    def setup_UI(self):
        self.frequency = HCLineEdit(self, "CH1_FREQUENCY", "CH1 Frequency (MHz)")
        self.amplitude = HCLineEdit(self, "CH1_AMPLITUDE", "CH1 Amplitude (Vpp)")
        self.offset = HCLineEdit(self, "CH1_OFFSET", "CH1 Offset (V)")
        self.waveform = HCComboBox(
            self,
            "CH1_WAVEFORM",
            "CH1 Waveform",
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
        self.burst_mode = HCComboBox(
            self,
            "CH1_BURS_MODE",
            "CH1 Burst Mode",
            ["TRIG", "GAT"],
        )
        self.burst_enable = HCComboBox(
            self,
            "CH1_BURS_STAT",
            "CH1 Burst Enable/State",
            ["1", "0"],
        )
        self.num_pulse = HCLineEdit(
            self,
            "CH1_BURS_NCYC",
            "CH1 Num Burst Pulses",
        )
        self.burst_period = HCLineEdit(
            self,
            "CH1_BURS_PER",
            "CH1 Burst Period (s)",
        )
        self.enable = HCComboBox(
            self,
            "CH1_ENABLE",
            "CH1 Enable Output On/Off",
            ["True", "False"],
        )
        self.trigger = HCComboBox(
            self,
            "CH1_TRIGGER_CHANNEL",
            "CH1 Trigger Channel",
            ["EXT", "IMM", "TIM", "BUS"],
        )
        self.delay = HCLineEdit(self, "CH1_TRIGGER_DELAY", "CH1 Trigger Delay (s)")
        self.impedance = HCComboBox(
            self,
            "CH1_IMPEDANCE",
            "CH1 Impedance",
            ["HiZ", "50 (OHM)"],
        )
        self.polarity = HCComboBox(
            self,
            "CH1_POLARITY",
            "CH1 Polarity",
            ["NORM", "INV"],
        )
        if self.num_channels >= 2:
            self.frequency2 = HCLineEdit(self, "CH2_FREQUENCY", "CH2 Frequency (MHz)")
            self.amplitude2 = HCLineEdit(self, "CH2_AMPLITUDE", "CH2 Amplitude (Vpp)")
            self.offset2 = HCLineEdit(self, "CH2_OFFSET", "CH2 Offset (V)")
            self.waveform2 = HCComboBox(
                self,
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
            self.burst_mode2 = HCComboBox(
                self,
                "CH2_BURS_MODE",
                "CH2 Burst Mode",
                ["TRIG", "GAT"],
            )
            self.burst_enable2 = HCComboBox(
                self,
                "CH2_BURS_STAT",
                "CH2 Burst Enable/State",
                ["1", "0"],
            )
            self.num_pulse2 = HCLineEdit(
                self,
                "CH2_BURS_NCYC",
                "CH2 Num Burst Pulses",
            )
            self.burst_period2 = HCLineEdit(
                self,
                "CH2_BURS_PER",
                "CH2 Burst Period (s)",
            )
            self.enable2 = HCComboBox(
                self,
                "CH2_ENABLE",
                "CH2 Enable Output On/Off",
                ["True", "False"],
            )
            self.trigger2 = HCComboBox(
                self,
                "CH2_TRIGGER_CHANNEL",
                "CH2 Trigger Channel",
                ["EXT", "IMM", "TIM", "BUS"],
            )
            self.delay2 = HCLineEdit(self, "CH2_TRIGGER_DELAY", "CH2 Trigger Delay (s)")
            self.impedance2 = HCComboBox(
                self,
                "CH2_IMPEDANCE",
                "CH2 Impedance",
                ["HiZ", "50 (OHM)"],
            )
            self.polarity2 = HCComboBox(
                self,
                "CH2_POLARITY",
                "CH2 Polarity",
                ["NORM", "INV"],
            )
            self.track2 = HCComboBox(
                self,
                "CH2_TRACK",
                "CH1 Track CH2",
                ["OFF", "ON", "INV"],
            )
            self.track2.pre_update_hook.append(self.set_tracking_hook)
            self.track1 = HCComboBox(
                self,
                "CH1_TRACK",
                "CH2 Track CH1",
                ["OFF", "ON", "INV"],
            )
            self.track1.pre_update_hook.append(self.set_tracking_hook)

        self.widgets = [
            self.frequency,
            self.amplitude,
            self.offset,
            self.waveform,
            self.num_pulse,
            self.burst_mode,
            self.burst_enable,
            self.burst_period,
            self.enable,
            self.trigger,
            self.delay,
            self.impedance,
            self.polarity,
        ]

        if self.num_channels >= 2:
            self.widgets2 = [
                self.frequency2,
                self.amplitude2,
                self.offset2,
                self.waveform2,
                self.num_pulse2,
                self.burst_mode2,
                self.burst_enable2,
                self.burst_period2,
                self.enable2,
                self.trigger2,
                self.delay2,
                self.impedance2,
                self.polarity2,
                self.track2,
                self.track1,
            ]

    def set_tracking_hook(self, setting, value):
        if value is None:
            return
        if setting == "CH2_TRACK":
            settings_list = self.widgets
        elif setting == "CH1_TRACK":
            settings_list = self.widgets2
            # Don't want to remove tracking buttons
            if self.track2 in settings_list:
                settings_list.remove(self.track2)
                settings_list.remove(self.track1)
        else:
            print("Unknown setting being called", flush=True)

        for w in settings_list:
            if value == "OFF":
                w.setEnabled(True)
            else:
                w.setEnabled(False)
            w.settings_to_UI()

        return setting, value
