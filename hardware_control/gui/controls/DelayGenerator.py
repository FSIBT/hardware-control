import logging

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator
from PyQt5.QtWidgets import (
    QGroupBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QWidget,
)

from ..base import Instrument
from ..widgets import load_icon

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

        self.trig_mode_label = QLabel("Trigger Mode:")
        self.trig_mode_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.trig_mode_drop = QComboBox()
        self.trig_mode_drop.addItems(["Internal", "External", "Single", "Burst"])
        self.trig_mode_drop.currentIndexChanged.connect(
            lambda: self.update_setting(
                "TRIGGER_MODE", self.trig_mode_drop.currentText().upper()
            )
        )
        self.trig_mode_drop.setCurrentText(str(self.settings["TRIGGER_MODE"].title()))

        self.trig_edge_label = QLabel("Trigger Edge:")
        self.trig_edge_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.trig_edge_drop = QComboBox()
        self.trig_edge_drop.addItems(["Positive", "Negative"])
        self.trig_edge_drop.currentIndexChanged.connect(
            lambda: self.update_setting(
                "TRIGGER_EDGE", self.trig_edge_drop.currentText().upper()
            )
        )
        self.trig_edge_drop.setCurrentText(str(self.settings["TRIGGER_EDGE"].title()))

        self.trig_z_label = QLabel("Ext. Trigger Zin:")
        self.trig_z_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.trig_z_drop = QComboBox()
        self.trig_z_drop.addItems(["50 Ohms", "Hi-Z"])
        self.trig_z_drop.currentIndexChanged.connect(
            lambda: self.update_setting(
                "EXT_TRIG_ZIN", self.trig_z_drop.currentText().upper()
            )
        )
        self.trig_z_drop.setCurrentText(str(self.settings["EXT_TRIG_ZIN"].title()))

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
        self.single_trig_but.setEnabled(self.trig_mode_drop.currentText() == "Single")

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

        self.write_label = QLabel("Command: ")
        self.write_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.write_edit = QLineEdit()
        self.write_edit.editingFinished.connect(
            lambda: self.update_setting("DIRECT_COMMAND", self.write_edit.text())
        )
        self.write_edit.setText(self.settings["DIRECT_COMMAND"])

        self.write_but = QPushButton()
        self.write_but.setText("Write")
        self.write_but.setCheckable(False)
        self.write_but.clicked.connect(
            lambda: self.command(self.settings["DIRECT_COMMAND"])
        )

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
        self.master_layout.addWidget(self.trig_mode_label, 0, 0)
        self.master_layout.addWidget(self.trig_mode_drop, 0, 1)
        self.master_layout.addWidget(self.trig_z_label, 0, 2)
        self.master_layout.addWidget(self.trig_z_drop, 0, 3)

        self.master_layout.addWidget(self.trig_edge_label, 1, 0)
        self.master_layout.addWidget(self.trig_edge_drop, 1, 1)
        self.master_layout.addWidget(self.trig_lev_label, 1, 2)
        self.master_layout.addWidget(self.trig_lev_edit, 1, 3)

        self.master_layout.addWidget(self.single_trig_but, 2, 3)

        self.master_layout.addWidget(self.pulse_label, 3, 0)
        self.master_layout.addWidget(self.pulse_edit, 3, 1)

        self.master_layout.addWidget(self.period_label, 3, 2)
        self.master_layout.addWidget(self.period_edit, 3, 3)

        self.master_layout.addWidget(self.write_label, 4, 0)
        self.master_layout.addWidget(self.write_edit, 4, 1)

        self.master_layout.addWidget(self.write_but, 4, 3)

        self.master_layout.addWidget(self.channel_box, 5, 0, 1, 4)

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

        self.trig_mode_drop.setCurrentText(str(self.settings["TRIGGER_MODE"]))
        self.trig_edge_drop.setCurrentText(str(self.settings["TRIGGER_EDGE"]))
        self.trig_z_drop.setCurrentText(str(self.settings["EXT_TRIG_ZIN"]))
        self.trig_lev_edit.setValue(float(self.settings["TRIGGER_LEVEL"]))
        self.pulse_edit.setValue(int(self.settings["PULSES_PER_BURST"]))
        self.period_edit.setValue(int(self.settings["TRIGGER_PERIOD"]))
        self.write_edit.setText(self.settings["DIRECT_COMMAND"])

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

        self.time_label = QLabel("t_offset [s]: ")

        self.time_edit = QLineEdit()
        self.time_edit.setValidator(QDoubleValidator())
        self.time_edit.editingFinished.connect(
            lambda: self.delay_changed(self.time_edit.text())
        )
        self.time_edit.setText("0")

        self.rel_label = QLabel("Relative to:")

        self.rel_drop = QComboBox()
        rels = ["Trig", "A", "B", "C", "D", "T0"]
        if channel not in [12, 34]:
            rels.remove(channel_str.title())
        self.rel_drop.addItems(rels)
        self.rel_drop.setCurrentText("Trig")
        self.rel_drop.currentIndexChanged.connect(
            lambda: self.relative_changed(self.rel_drop.currentText().upper())
        )

        self.level_label = QLabel("Output mode: ")

        self.volt_edit_label = QLabel("High Level (V):")
        self.volt_edit = QLineEdit()
        self.volt_edit.setValidator(QDoubleValidator())
        self.volt_edit.setText("5")
        self.volt_edit.editingFinished.connect(
            lambda: self.voltage_changed(self.volt_edit.text())
        )
        self.volt_edit.setEnabled(False)

        self.level_drop = QComboBox()
        self.level_drop.addItems(["TTL", "Voltage", "NIM", "ECL"])
        self.level_drop.setCurrentText("TTL")
        self.level_drop.currentIndexChanged.connect(
            lambda: self.set_output_level(self.level_drop.currentText().upper())
        )

        self.channel_layout = QGridLayout()
        self.channel_layout.addWidget(self.channel_label, 0, 0, 1, 2)
        if self.channel in [12, 34]:
            self.blank_label = QLabel(" ")
            self.channel_layout.addWidget(self.blank_label, 1, 0, 1, 2)
            self.blank_label2 = QLabel(" ")
            self.channel_layout.addWidget(self.blank_label2, 2, 0, 1, 2)
        else:
            self.channel_layout.addWidget(self.time_edit, 1, 1)
            self.channel_layout.addWidget(self.time_label, 1, 0)
            self.channel_layout.addWidget(self.rel_label, 2, 0)
            self.channel_layout.addWidget(self.rel_drop, 2, 1)

        self.channel_layout.addWidget(self.level_label, 3, 0)
        self.channel_layout.addWidget(self.level_drop, 3, 1)
        self.channel_layout.addWidget(self.volt_edit_label, 4, 0)
        self.channel_layout.addWidget(self.volt_edit, 4, 1)
        self.setLayout(self.channel_layout)

        self.settings_to_UI()

    def settings_to_UI(self):
        if self.channel not in [12, 34]:
            self.time_edit.setText(self.main_widget.settings[f"CH{self.channel}_DELAY"])
            self.rel_drop.setCurrentText(
                self.main_widget.settings[f"CH{self.channel}_RELATIVE"]
            )
        mode = self.main_widget.settings[f"CH{self.channel}_OUTPUT_MODE"]
        if mode == "VAR":
            mode = "VOLTAGE"
        self.level_drop.setCurrentText(mode.title())
        self.volt_edit.setText(
            self.main_widget.settings[f"CH{self.channel}_OUTPUT_AMPLITUDE"]
        )

    def set_output_level(self, new_val: str):
        if new_val is None:
            return

        if new_val == "VOLTAGE":
            self.volt_edit.setEnabled(True)
            new_val = "VAR"
        else:
            self.volt_edit.setEnabled(False)

        self.main_widget.update_setting(f"CH{self.channel}_OUTPUT_MODE", new_val)

    def voltage_changed(self, new_val: str):
        self.main_widget.update_setting(f"CH{self.channel}_OUTPUT_OFFSET", "0")
        self.main_widget.update_setting(f"CH{self.channel}_OUTPUT_AMPLITUDE", new_val)

    def relative_changed(self, rel_to: str):
        self.main_widget.update_setting(f"CH{self.channel}_RELATIVE", rel_to)

    def delay_changed(self, t_delay: str):
        self.main_widget.update_setting(f"CH{self.channel}_DELAY", t_delay)
