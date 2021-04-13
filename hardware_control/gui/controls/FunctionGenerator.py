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
    QComboBox,
)

from ..base import Instrument, Comm
from ..widgets import setButtonState, load_icon
from ..widgets import QControl, QControlCombo


logger = logging.getLogger(__name__)


class FunctionGenerator(Instrument):
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

        self.settings = self.default_state()
        self.setup_UI()
        self.autolayout_grid(ncols=2)

        # Write state to scope - synch scope with GUI
        self.send_state()

    def setup_UI(self):
        self.frequency = QControl(self, "CH1_FREQUENCY", "Frequency (MHz)")
        self.amplitude = QControl(self, "CH1_AMPLITUDE", "Amplitude (Vpp)")
        self.offset = QControl(self, "CH1_OFFSET", "Offset (V)")
        self.waveform = QControlCombo(
            self,
            "CH1_WAVEFORM",
            "Waveform",
            ["Sine", "Square", "Triangle", "Ramp", "Pulse", "Noise", "DC", "File"],
        )
        self.burst_mode = QControlCombo(
            self, "CH1_BURS_MODE", "Burst Mode", ["TRIG", "GAT"],
        )
        self.burst_enable = QControlCombo(
            self, "CH1_BURS_STAT", "Burst Enable/State", ["1", "0"],
        )
        self.num_pulse = QControl(self, "CH1_BURS_NCYC", "Num Burst Pulses",)
        self.burst_period = QControl(self, "CH1_BURS_PER", "Burst Period (s)",)
        self.enable = QControlCombo(
            self, "CH1_ENABLE", "Enable Output On/Off", ["True", "False"],
        )
        self.trigger = QControlCombo(
            self, "CH1_TRIGGER_CHANNEL", "Trigger Channel", [
                "EXT", "IMM", "TIM", "BUS"],
        )
        self.delay = QControl(self, "CH1_TRIGGER_DELAY", "Trigger Delay (s)")
        self.impedance = QControlCombo(
            self, "CH1_IMPEDANCE", "Impedance", ["HiZ", "50 (OHM)"],
        )
        if self.num_channels >= 2:
            self.frequency2 = QControl(
                self, "CH2_FREQUENCY", "Frequency (MHz)")
            self.amplitude2 = QControl(
                self, "CH2_AMPLITUDE", "Amplitude (Vpp)")
            self.offset2 = QControl(self, "CH2_OFFSET", "Offset (V)")
            self.waveform2 = QControlCombo(
                self,
                "CH2_WAVEFORM",
                "Waveform",
                ["Sine", "Square", "Triangle", "Ramp",
                    "Pulse", "Noise", "DC", "File"],
            )
            self.burst_mode2 = QControlCombo(
                self, "CH2_BURS_MODE", "Burst Mode", ["TRIG", "GAT"],
            )
            self.burst_enable2 = QControlCombo(
                self, "CH2_BURS_STAT", "Burst Enable/State", ["1", "0"],
            )
            self.num_pulse2 = QControl(
                self, "CH2_BURS_NCYC", "Num Burst Pulses",)
            self.burst_period2 = QControl(
                self, "CH2_BURS_PER", "Burst Period (s)",)
            self.enable2 = QControlCombo(
                self, "CH2_ENABLE", "Enable Output On/Off", ["True", "False"],
            )
            self.trigger2 = QControlCombo(
                self, "CH2_TRIGGER_CHANNEL", "Trigger Channel", [
                    "EXT", "IMM", "TIM", "BUS"],
            )
            self.delay2 = QControl(
                self, "CH2_TRIGGER_DELAY", "Trigger Delay (s)")
            self.impedance2 = QControlCombo(
                self, "CH2_IMPEDANCE", "Impedance", ["HiZ", "50 (OHM)"],
            )
            self.track2 = QControlCombo(
                self, "CH2_TRACK", "CH1 Track CH2", ["OFF", "ON", "INV"],
            )
            self.track1 = QControlCombo(
                self, "CH1_TRACK", "CH2 Track CH1", ["OFF", "ON", "INV"],
            )
        self.widgets = [
            self.frequency,
            self.amplitude,
            self.offset,
            self.waveform,
            self.num_pulse,
            self.burst_mode,
            self.burst_period,
            self.enable,
            self.trigger,
            self.delay,
            self.impedance
        ]

        if self.num_channels >= 2:
            self.widgets2 = [
                self.frequency2,
                self.amplitude2,
                self.offset2,
                self.waveform2,
                self.num_pulse2,
                self.burst_mode2,
                self.burst_period2,
                self.enable2,
                self.trigger2,
                self.delay2,
                self.impedance2,
                self.track2,
                self.track1,
            ]

    def initialize_gui_instrument(self):
        return self.default_state()

    def default_state(self):

        default = {}
        for i in range(1, self.num_channels+1):
            default[f"CH{i}_AMPLITUDE"] = "1"
            default[f"CH{i}_FREQUENCY"] = "12"
            default[f"CH{i}_OFFSET"] = "0"
            default[f"CH{i}_WAVEFORM"] = "SINE"
            default[f"CH{i}_MODULATE"] = "FALSE"
            default[f"CH{i}_BURS_MODE"] = "TRIG"
            default[f"CH{i}_BURS_STAT"] = "1"
            default[f"CH{i}_IMPEDANCE"] = "HiZ"
            default[f"CH{i}_ENABLE"] = "TRUE"
            default[f"CH{i}_BURS_NCYC"] = "500"
            default[f"CH{i}_BURS_PER"] = "1"
            default[f"CH{i}_TRIG_SOUR"] = "EXT"
            default[f"CH{i}_TRIGGER_CHANNEL"] = "EXT"
            default[f"CH{i}_TRIGGER_DELAY"] = "10e-6"
            default[f"CH{i}_TRACK"] = "OFF"

        return default

    def settings_to_UI(self):
        for w in self.widgets:
            w.settings_to_UI()
        if self.num_channels >= 2:
            for w in self.widgets2:
                w.settings_to_UI()

        return
