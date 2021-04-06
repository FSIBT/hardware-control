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
            self, "TRIGGER_CHANNEL", "Trigger Channel", ["EXT", "IMM", "TIM", "BUS"],
        )
        self.delay = QControl(self, "TRIGGER_DELAY", "Trigger Delay (s)")
        self.impedance = QControlCombo(
            self, "CH1_IMPEDANCE", "Impedance", ["HiZ", "50 (OHM)"],
        )

    def initialize_gui_instrument(self):
        return self.default_state()

    def default_state(self):

        default = {}

        default["CH1_AMPLITUDE"] = "1"
        default["CH1_FREQUENCY"] = "12"
        default["CH1_OFFSET"] = "0"
        default["CH1_WAVEFORM"] = "SINE"
        default["CH1_MODULATE"] = "FALSE"
        default["CH1_BURS_MODE"] = "TRIG"
        default["CH1_BURS_STAT"] = "1"
        default["CH1_IMPEDANCE"] = "HiZ"
        default["CH1_ENABLE"] = "TRUE"
        default["CH1_BURS_NCYC"] = "500"
        default["CH1_BURS_PER"] = "1"
        default["CH1_TRIG_SOUR"] = "EXT"
        default["TRIGGER_CHANNEL"] = "EXT"
        default["TRIGGER_DELAY"] = "10e-6"

        return default

    def settings_to_UI(self):
        self.frequency.settings_to_UI()
        self.amplitude.settings_to_UI()
        self.offset.settings_to_UI()
        self.waveform.settings_to_UI()
        self.num_pulse.settings_to_UI()
        self.burst_mode.settings_to_UI()
        self.burst_period.settings_to_UI()
        self.enable.settings_to_UI()
        self.trigger.settings_to_UI()
        self.delay.settings_to_UI()
        self.impedance.settings_to_UI()
        return
