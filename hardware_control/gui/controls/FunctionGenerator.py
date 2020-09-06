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

        default["CH1_AMPLITUDE"] = "1"
        default["CH1_FREQUENCY"] = "1e3"
        default["CH1_OFFSET"] = "0"
        default["CH1_WAVEFORM"] = "Sine"
        default["CH1_MODULATE"] = "False"
        default["CH1_BURST_EN"] = "False"
        default["CH1_IMPEDANCE"] = "1e6"
        default["CH1_ENABLED"] = "False"
        default["CH1_NUM_PULSE"] = "300"
        default["CH1_BURST_FREQ"] = "1"

        if self.num_channels > 1:
            default["CH2_AMPLITUDE"] = "1"
            default["CH2_FREQUENCY"] = "1e3"
            default["CH2_OFFSET"] = "0"
            default["CH2_WAVEFORM"] = "Sine"
            default["CH2_MODULATE"] = "False"
            default["CH2_BURST_EN"] = "False"
            default["CH2_IMPEDANCE"] = "1e6"
            default["CH2_ENABLED"] = "False"
            default["CH2_NUM_PULSE"] = "300"
            default["CH2_BURST_FREQ"] = "1"

        return default

    def settings_to_UI(self):

        for chan in self.channel_widgets:
            chan.settings_to_UI()


class FunctionGeneratorChannelWidget(QWidget):
    """Defines a UI for AWG channels.

    .. image:: /images/controls/FunctionGenerator-single-channel.png
      :height: 200

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
                f"CH{channel}_AMPLITUDE", (self.amplitude_edit.text())
            )
        )
        self.amplitude_edit.setText(str(control.settings[f"CH{channel}_AMPLITUDE"]))

        self.offset_edit = QLineEdit()
        self.offset_edit.setValidator(QDoubleValidator())
        self.offset_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_OFFSET", (self.offset_edit.text())
            )
        )
        self.offset_edit.setText(str(control.settings[f"CH{channel}_OFFSET"]))

        self.frequency_edit = QLineEdit()
        self.frequency_edit.setValidator(QDoubleValidator())
        self.frequency_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_FREQUENCY", (self.frequency_edit.text())
            )
        )
        self.frequency_edit.setText(str(control.settings[f"CH{channel}_FREQUENCY"]))

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
                f"CH{channel}_NUM_PULSE", (self.num_pulse_edit.text())
            )
        )
        self.num_pulse_edit.setText(str(control.settings[f"CH{channel}_NUM_PULSE"]))

        self.burst_freq_edit = QLineEdit()
        self.burst_freq_edit.setValidator(QDoubleValidator())
        self.burst_freq_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_BURST_FREQ", (self.burst_freq_edit.text())
            )
        )
        self.burst_freq_edit.setText(str(control.settings[f"CH{channel}_BURST_FREQ"]))

        self.form2 = QFormLayout()
        self.form2.addRow("Num Burst Pulses:", self.num_pulse_edit)
        self.form2.addRow("Burst Freq (Hz):", self.burst_freq_edit)

        # ******* DEFINE BUTTONS + DROPDOWNS
        self.active_but = QPushButton()
        self.active_but.setText("Output On/Off")
        self.active_but.setCheckable(True)
        self.active_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_ENABLED", str(self.active_but.isChecked())
            )
        )
        setButtonState(self.active_but, control.settings[f"CH{channel}_ENABLED"])

        self.mod_but = QPushButton()
        self.mod_but.setText("Modulation")
        self.mod_but.setIcon(QIcon(load_icon("modulation.png")))
        self.mod_but.setCheckable(True)
        self.mod_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_MODULATE", str(self.mod_but.isChecked())
            )
        )
        setButtonState(self.mod_but, control.settings[f"CH{channel}_MODULATE"])

        self.burst_but = QPushButton()
        self.burst_but.setText("Burst")
        self.burst_but.setCheckable(True)
        self.burst_but.setIcon(QIcon(load_icon("burst.png")))
        self.burst_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_BURST_EN", str(self.burst_but.isChecked())
            )
        )
        setButtonState(self.burst_but, control.settings[f"CH{channel}_BURST_EN"])

        self.waveform_label = QLabel("Waveform:")
        self.waveform_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.waveform_drop = QComboBox()
        self.waveform_drop.addItems(
            ["Sine", "Square", "Triangle", "Ramp", "Pulse", "Noise", "DC", "File"]
        )
        self.waveform_drop.currentIndexChanged.connect(
            lambda: control.update_setting(
                f"CH{self.channel}_WAVEFORM", self.waveform_drop.currentText().upper()
            )
        )
        self.waveform_drop.setCurrentText(control.settings[f"CH{channel}_WAVEFORM"])

        self.impedance_label = QLabel("Impedance:")
        self.impedance_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.impedance_drop = QComboBox()
        self.impedance_drop.addItems(["1e6", "50"])
        self.impedance_drop.currentIndexChanged.connect(
            lambda: control.update_setting(
                f"CH{channel}_IMPEDANCE", self.impedance_drop.currentText()
            )
        )
        self.impedance_drop.setCurrentText(
            str(control.settings[f"CH{channel}_IMPEDANCE"])
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

        self.amplitude_edit.setText(str(self.control.settings[f"CH{ch}_AMPLITUDE"]))
        self.offset_edit.setText(str(self.control.settings[f"CH{ch}_OFFSET"]))
        self.frequency_edit.setText(str(self.control.settings[f"CH{ch}_FREQUENCY"]))
        self.num_pulse_edit.setText(str(self.control.settings[f"CH{ch}_NUM_PULSE"]))
        self.burst_freq_edit.setText(str(self.control.settings[f"CH{ch}_BURST_FREQ"]))
        setButtonState(self.active_but, self.control.settings[f"CH{ch}_ENABLED"])
        setButtonState(self.mod_but, self.control.settings[f"CH{ch}_MODULATE"])
        setButtonState(self.burst_but, self.control.settings[f"CH{ch}_BURST_EN"])
        self.waveform_drop.setCurrentText(
            self.control.settings[f"CH{ch}_WAVEFORM"].title()
        )
        self.impedance_drop.setCurrentText(
            str(self.control.settings[f"CH{ch}_IMPEDANCE"])
        )
