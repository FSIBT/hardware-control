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


logger = logging.getLogger(__name__)


class FunctionGenerator(Instrument):
    """A GUI for Function/Waveform generators.

    See Also
    --------
    hardware_control.backends.keysight.Keysight_36300.Keysight_36300

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

        self.channel_widgets = []
        self.channel_widgets.append(FunctionGeneratorChannelWidget(1, self))

        self.channel_panel = QGridLayout()
        self.channel_panel.addWidget(self.channel_widgets[0], 0, 0)

        if self.num_channels == 2:
            self.channel_widgets.append(FunctionGeneratorChannelWidget(2, self))
            self.channel_panel.addWidget(self.channel_widgets[-1], 0, 1)

        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.channel_panel, 1, 0, 1, 4)

        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

    def initialize_gui_instrument(self):
        return self.default_state()

    def default_state(self):

        default = {}

        default["CH1_amplitude"] = "1"
        default["CH1_frequency"] = "1e3"
        default["CH1_offset"] = "0"
        default["CH1_waveform"] = "Sine"
        default["CH1_modulate"] = "False"
        default["CH1_burst_en"] = "False"
        default["CH1_impedance"] = "1e6"
        default["CH1_enabled"] = "False"
        default["CH1_num_pulse"] = "300"
        default["CH1_burst_freq"] = "1"

        if self.num_channels > 1:
            default["CH2_amplitude"] = "1"
            default["CH2_frequency"] = "1e3"
            default["CH2_offset"] = "0"
            default["CH2_waveform"] = "Sine"
            default["CH2_modulate"] = "False"
            default["CH2_burst_en"] = "False"
            default["CH2_impedance"] = "1e6"
            default["CH2_enabled"] = "False"
            default["CH2_num_pulse"] = "300"
            default["CH2_burst_freq"] = "1"

        return default

    def settings_to_UI(self):

        for chan in self.channel_widgets:
            chan.settings_to_UI()


class FunctionGeneratorChannelWidget(QWidget):
    """Defines a UI for AWG channels.

    """

    def __init__(self, channel: int, control):
        super().__init__()

        self.channel = channel
        self.control = control

        # ************** DEFINE UI *********************#

        self.channel_label = QLabel()
        if self.channel == 1:
            self.channel_label.setPixmap(load_icon("channel1_yellow.png"))
        else:
            self.channel_label.setPixmap(load_icon("channel2_green.png"))

        # ****** DEFINE TEXT BOXES
        self.amplitude_edit = QLineEdit()
        self.amplitude_edit.setValidator(QDoubleValidator())
        self.amplitude_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_amplitude", (self.amplitude_edit.text())
            )
        )
        self.amplitude_edit.setText(str(control.settings[f"CH{channel}_amplitude"]))

        self.offset_edit = QLineEdit()
        self.offset_edit.setValidator(QDoubleValidator())
        self.offset_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_offset", (self.offset_edit.text())
            )
        )
        self.offset_edit.setText(str(control.settings[f"CH{channel}_offset"]))

        self.frequency_edit = QLineEdit()
        self.frequency_edit.setValidator(QDoubleValidator())
        self.frequency_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_frequency", (self.frequency_edit.text())
            )
        )
        self.frequency_edit.setText(str(control.settings[f"CH{channel}_frequency"]))

        self.form = QFormLayout()
        self.form.addRow("Amplitude (Vpp):", self.amplitude_edit)
        self.form.addRow("Offset (V):", self.offset_edit)
        self.form.addRow("Frequency (Hz):", self.frequency_edit)

        self.lower_grid = QGridLayout()

        # ****** DEFINE 2nd COL TEXT BOXES
        self.num_pulse_edit = QLineEdit()
        self.num_pulse_edit.setValidator(QDoubleValidator())
        self.num_pulse_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_num_pulse", (self.num_pulse_edit.text())
            )
        )
        self.num_pulse_edit.setText(str(control.settings[f"CH{channel}_num_pulse"]))

        self.burst_freq_edit = QLineEdit()
        self.burst_freq_edit.setValidator(QDoubleValidator())
        self.burst_freq_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_burst_freq", (self.burst_freq_edit.text())
            )
        )
        self.burst_freq_edit.setText(str(control.settings[f"CH{channel}_burst_freq"]))

        self.form2 = QFormLayout()
        self.form2.addRow("Num Burst Pulses:", self.num_pulse_edit)
        self.form2.addRow("Burst Freq (Hz):", self.burst_freq_edit)

        # ******* DEFINE BUTTONS + DROPDOWNS
        self.active_but = QPushButton()
        self.active_but.setText("Output On/Off")
        self.active_but.setCheckable(True)
        self.active_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_enabled", str(self.active_but.isChecked())
            )
        )
        setButtonState(self.active_but, control.settings[f"CH{channel}_enabled"])

        self.mod_but = QPushButton()
        self.mod_but.setText("Modulation")
        self.mod_but.setIcon(QIcon(load_icon("modulation.png")))
        self.mod_but.setCheckable(True)
        self.mod_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_modulate", str(self.mod_but.isChecked())
            )
        )
        setButtonState(self.mod_but, control.settings[f"CH{channel}_modulate"])

        self.burst_but = QPushButton()
        self.burst_but.setText("Burst")
        self.burst_but.setCheckable(True)
        self.burst_but.setIcon(QIcon(load_icon("burst.png")))
        self.burst_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_burst_en", str(self.burst_but.isChecked())
            )
        )
        setButtonState(self.burst_but, control.settings[f"CH{channel}_burst_en"])

        self.waveform_label = QLabel("Waveform:")
        self.waveform_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.waveform_drop = QComboBox()
        self.waveform_drop.addItems(
            ["Sine", "Square", "Triangle", "Ramp", "Pulse", "Noise", "DC", "File"]
        )
        self.waveform_drop.currentIndexChanged.connect(
            lambda: control.update_setting(
                f"CH{self.channel}_waveform", self.waveform_drop.currentText()
            )
        )
        self.waveform_drop.setCurrentText(control.settings[f"CH{channel}_waveform"])

        self.impedance_label = QLabel("Impedance:")
        self.impedance_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.impedance_drop = QComboBox()
        self.impedance_drop.addItems(["1e6", "50"])
        self.impedance_drop.currentIndexChanged.connect(
            lambda: control.update_setting(
                f"CH{channel}_impedance", self.impedance_drop.currentText()
            )
        )
        self.impedance_drop.setCurrentText(
            str(control.settings[f"CH{channel}_impedance"])
        )

        # Add widgets to grid layout
        self.lower_grid.addWidget(self.active_but, 0, 0)
        self.lower_grid.addWidget(self.mod_but, 1, 0)
        self.lower_grid.addWidget(self.burst_but, 1, 1)
        self.lower_grid.addWidget(self.waveform_label, 2, 0)
        self.lower_grid.addWidget(self.waveform_drop, 2, 1)
        self.lower_grid.addWidget(self.impedance_label, 3, 0)
        self.lower_grid.addWidget(self.impedance_drop, 3, 1)

        # ******* DEFINE OVERALL LAYOUT
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.channel_label, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.master_layout.addLayout(self.lower_grid, 2, 0)
        self.master_layout.addLayout(self.form2, 2, 1)
        self.setLayout(self.master_layout)

    def settings_to_UI(self):
        ch = self.channel

        self.amplitude_edit.setText(str(self.control.settings[f"CH{ch}_amplitude"]))
        self.offset_edit.setText(str(self.control.settings[f"CH{ch}_offset"]))
        self.frequency_edit.setText(str(self.control.settings[f"CH{ch}_frequency"]))
        self.num_pulse_edit.setText(str(self.control.settings[f"CH{ch}_num_pulse"]))
        self.burst_freq_edit.setText(str(self.control.settings[f"CH{ch}_burst_freq"]))
        setButtonState(self.active_but, self.control.settings[f"CH{ch}_enabled"])
        setButtonState(self.mod_but, self.control.settings[f"CH{ch}_modulate"])
        setButtonState(self.burst_but, self.control.settings[f"CH{ch}_burst_en"])
        self.waveform_drop.setCurrentText(self.control.settings[f"CH{ch}_waveform"])
        self.impedance_drop.setCurrentText(
            str(self.control.settings[f"CH{ch}_impedance"])
        )
