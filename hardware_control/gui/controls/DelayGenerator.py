import logging

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator
from PyQt5.QtWidgets import (
    QGroupBox,
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QWidget,
)

from ..base import Instrument
from ..widgets import load_icon, QControl, QControlCombo

logger = logging.getLogger(__name__)


class DelayGenerator(Instrument):
    """A GUI for delay generators.

    This implements all front panel functions of a SRS DG535 and has
    also has some elements that are probably unique to this
    instrument.

    .. image:: /images/controls/DelayGenerator.png
      :height: 200

    See Also
    --------
    hardware_control.backends.srs.SRS_DG535.SRS_DG535

    """

    def __init__(
        self,
        app,
        backend,
        name: str = "Pulse Generator Control",
        lock_until_sync=False,
        channels: int = 4,
    ):

        super().__init__(app, name, backend, lock_until_sync)

        self.channels = channels
        self.settings = self.default_state()

        self.update_settings_hooks["TRIGGER_MODE"].append(self.enableDisableWidgets)

        # Create GUI
        self.trig_mode = QControlCombo(
            self,
            "TRIGGER_MODE",
            "Trigger Mode",
            ["Internal", "External", "Single", "Burst"],
        )
        self.trig_mode.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.trig_edge = QControlCombo(
            self, "TRIGGER_EDGE", "Trigger Edge", ["Positive", "Negative"]
        )
        self.trig_edge.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.trig_impedance = QControlCombo(
            self, "EXT_TRIG_ZIN", "Ext. Trigger Zin", ["50 Ohms", "Hi-Z"],
        )
        self.trig_impedance.label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.trig_lev_label = QLabel("Ext Trig Level (V):")
        self.trig_lev_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.trig_lev_edit = QDoubleSpinBox()
        self.trig_lev_edit.editingFinished.connect(
            lambda: self.update_setting("TRIGGER_LEVEL", self.trig_lev_edit.text())
        )
        self.trig_lev_edit.setDecimals(3)
        self.trig_lev_edit.setSingleStep(0.05)
        if hasattr(backend, "ExternalTriggerThreshold"):
            self.trig_lev_edit.setRange(
                -backend.ExternalTriggerThreshold, backend.ExternalTriggerThreshold,
            )
        self.trig_lev_edit.setValue(float(self.settings["TRIGGER_LEVEL"]))

        self.single_trig_but = QPushButton()
        self.single_trig_but.setText("Single Trigger")
        self.single_trig_but.setIcon(QIcon(load_icon("pulse.png")))
        self.single_trig_but.setCheckable(False)
        self.single_trig_but.clicked.connect(lambda: self.command("SINGLE_TRIGGER"))
        self.single_trig_but.setEnabled(self.trig_mode.currentText() == "Single")

        self.pulse_label = QLabel("Pulses per Burst:")
        self.pulse_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.pulse_edit = QSpinBox()
        self.pulse_edit.editingFinished.connect(
            lambda: self.update_setting("PULSES_PER_BURST", self.pulse_edit.text())
        )
        if hasattr(backend, "PulsesPerBurst"):
            self.pulse_edit.setRange(2, backend.PulsesPerBurst)
        self.pulse_edit.setValue(int(self.settings["PULSES_PER_BURST"]))

        self.period_label = QLabel("Triggers per Burst:")
        self.period_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.period_edit = QSpinBox()
        self.period_edit.setMinimum(1)
        self.period_edit.editingFinished.connect(
            lambda: self.update_setting("TRIGGER_PERIOD", self.period_edit.text())
        )
        self.period_edit.setSingleStep(1)
        self.period_edit.setValue(int(self.settings["TRIGGER_PERIOD"]))

        widget_col = 0
        self.channel_widgets = []
        self.channel_box = QGroupBox()
        self.channel_box_layout = QGridLayout()
        if channels == 4:
            for i in range(1, 5):
                self.channel_widgets.append(DelayChannelWidget(self, i))
                self.channel_box_layout.addWidget(
                    self.channel_widgets[-1], 0, widget_col
                )
                widget_col += 1

            self.channel_widgets.append(DelayChannelWidget(self, 12))
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, widget_col)
            widget_col += 1

            self.channel_widgets.append(DelayChannelWidget(self, 34))
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, widget_col)
            widget_col += 1
        if channels == 2:
            for i in range(1, 3):
                self.channel_widgets.append(DelayChannelWidget(self, i))
                self.channel_box_layout.addWidget(
                    self.channel_widgets[-1], 0, widget_col
                )
                widget_col += 1

            self.channel_widgets.append(DelayChannelWidget(self, 12))
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, widget_col)
            widget_col += 1

        self.channel_box.setLayout(self.channel_box_layout)

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.trig_mode.label, 0, 0)
        self.master_layout.addWidget(self.trig_mode.value, 0, 1)
        self.master_layout.addWidget(self.trig_impedance.label, 0, 2)
        self.master_layout.addWidget(self.trig_impedance.value, 0, 3)

        self.master_layout.addWidget(self.trig_edge.label, 1, 0)
        self.master_layout.addWidget(self.trig_edge.value, 1, 1)
        self.master_layout.addWidget(self.trig_lev_label, 1, 2)
        self.master_layout.addWidget(self.trig_lev_edit, 1, 3)

        self.master_layout.addWidget(self.single_trig_but, 2, 3)

        self.master_layout.addWidget(self.pulse_label, 3, 0)
        self.master_layout.addWidget(self.pulse_edit, 3, 1)

        self.master_layout.addWidget(self.period_label, 3, 2)
        self.master_layout.addWidget(self.period_edit, 3, 3)

        self.master_layout.addWidget(self.channel_box, 4, 0, 1, 4)

        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

    def enableDisableWidgets(self, setting: str, value: str):

        if value == "SINGLE":
            self.single_trig_but.setEnabled(True)
        else:
            self.single_trig_but.setEnabled(False)
        return value

    def default_state(self):
        """Create the defualt state variable"""

        default = {}

        default["TRIGGER_MODE"] = "INTERNAL"
        default["TRIGGER_EDGE"] = "POS"
        default["EXT_TRIG_ZIN"] = "HI-Z"
        default["BURST_COUNT"] = "2"
        default["BURST_PERIOD"] = "4"
        default["DIRECT_COMMAND"] = ""
        default["PULSES_PER_BURST"] = "2"
        default["TRIGGER_PERIOD"] = "4"
        default["TRIGGER_LEVEL"] = "0"
        for c in range(1, self.channels + 1):
            default[f"CH{c}_DELAY"] = "1"
            default[f"CH{c}_RELATIVE"] = "TRIG"
            default[f"CH{c}_OUTPUT_MODE"] = "TTL"
            default[f"CH{c}_OUTPUT_AMPLITUDE"] = "5"
        if self.channels == 4:
            default["CH12_OUTPUT_MODE"] = "TTL"
            default["CH12_OUTPUT_AMPLITUDE"] = "5"
            default["CH34_OUTPUT_MODE"] = "TTL"
            default["CH34_OUTPUT_AMPLITUDE"] = "5"
        if self.channels == 2:
            default["CH12_OUTPUT_MODE"] = "TTL"
            default["CH12_OUTPUT_AMPLITUDE"] = "5"

        return default

    def settings_to_UI(self):
        self.trig_mode.settings_to_UI()
        self.trig_edge.settings_to_UI()
        self.trig_impedance.settings_to_UI()
        self.trig_lev_edit.setValue(float(self.settings["TRIGGER_LEVEL"]))
        self.pulse_edit.setValue(int(self.settings["PULSES_PER_BURST"]))
        self.period_edit.setValue(int(self.settings["TRIGGER_PERIOD"]))

        for cw in self.channel_widgets:
            cw.settings_to_UI()


class DelayChannelWidget(QWidget):
    """A Qt-widget that implements controls for a single channel of a delay generator.

    Used together with :py:class:`DelayGenerator`.

    .. image:: /images/controls/DelayGenerator-channel.png
      :height: 200


    Parameters
    ----------

    main_widget : DelayGenerator
        The main widget where this is used in
    channel : int
        The channel this widget controls. Normally 1, 2, 3, or 4, but 12 and 34 are also
        allowed for combined channels that, for example, exist in the SRS DG533.
    use_alpha : bool
        Replace the numbers in the labels with A, B, C, D (or AB, CD).

    """

    num_to_alpha = {1: "A", 2: "B", 3: "C", 4: "D", 12: "AB", 34: "CD"}

    def __init__(self, main_widget, channel: int, use_alpha: bool = True):

        super().__init__()

        self.channel = channel
        self.main_widget = main_widget

        if use_alpha:
            channel_str = DelayChannelWidget.num_to_alpha.get(channel, "?")
        else:
            channel_str = str(self.channel)

        self.channel_label = QLabel()
        self.channel_label.setText(f"Channel {channel_str}")
        self.channel_label.setFont(QFont("Arial", 20))
        self.channel_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        if channel not in [12, 34]:
            self.time_delay = QControl(
                self.main_widget, f"CH{self.channel}_DELAY", "t_offset [s]",
            )

        rels = ["Trig", "A", "B", "C", "D", "T0"]
        if channel not in [12, 34]:
            rels.remove(channel_str.title())
            self.relative = QControlCombo(
                self.main_widget, f"CH{self.channel}_RELATIVE", "Relative to", rels,
            )

        self.volt = QControl(
            self.main_widget, f"CH{self.channel}_OUTPUT_AMPLITUDE", "High Level (V)",
        )
        self.volt.setEnabled(False)

        self.level = QControlCombo(
            self.main_widget,
            f"CH{self.channel}_OUTPUT_MODE",
            "Output mode",
            ["TTL", "Voltage", "NIM", "ECL"],
        )
        self.level.pre_update_hook.append(self.set_output_level_hook)

        self.channel_layout = QGridLayout()
        self.channel_layout.addWidget(self.channel_label, 0, 0, 1, 2)
        if self.channel not in [12, 34]:
            self.channel_layout.addWidget(self.time_delay.label, 1, 0)
            self.channel_layout.addWidget(self.time_delay.value, 1, 1)
            self.channel_layout.addWidget(self.relative.label, 2, 0)
            self.channel_layout.addWidget(self.relative.value, 2, 1)

        self.channel_layout.addWidget(self.level.label, 3, 0)
        self.channel_layout.addWidget(self.level.value, 3, 1)
        self.channel_layout.addWidget(self.volt.label, 4, 0)
        self.channel_layout.addWidget(self.volt.value, 4, 1)
        self.setLayout(self.channel_layout)

        self.settings_to_UI()

    def settings_to_UI(self):
        if self.channel not in [12, 34]:
            self.time_delay.settings_to_UI()
            self.relative.settings_to_UI()
        mode = self.main_widget.settings[f"CH{self.channel}_OUTPUT_MODE"]
        if mode == "VAR":
            mode = "VOLTAGE"
        self.level.setCurrentText(mode.title())
        self.volt.settings_to_UI()

    def set_output_level_hook(self, setting, value):
        if value is None:
            return

        if value == "VOLTAGE":
            self.volt.setEnabled(True)
            value = "VAR"
        else:
            self.volt.setEnabled(False)
        return setting, value
