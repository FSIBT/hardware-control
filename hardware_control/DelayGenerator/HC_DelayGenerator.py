import pkg_resources
from PyQt5 import QtCore
from PyQt5.QtGui import QIntValidator, QPixmap, QIcon, QFont, QDoubleValidator
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
import logging

logger = logging.getLogger(__name__)

from hardware_control.base import HC_Instrument, HC_Comm


class HC_DelayGenerator(HC_Instrument):
    def __init__(
        self,
        backend,
        window,
        name: str = "Pulse Generator Control",
        lock_until_sync=False,
        channels: int = 4,
    ):

        super().__init__(window, name, backend, lock_until_sync)

        self.settings = {}
        self.name = name
        self.address = backend.connection_addr
        self.channels = channels

        self.settings = self.default_state()

        backend.dummy = self.window.app.dummy

        self.filename = ""

        # Create GUI

        self.trig_mode_label = QLabel("Trigger Mode:")
        self.trig_mode_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_mode_drop = QComboBox()
        self.trig_mode_drop.addItems(["Internal", "External", "Single", "Burst"])
        self.trig_mode_drop.currentIndexChanged.connect(
            lambda: self.update_setting(
                f"trigger_mode", self.trig_mode_drop.currentText()
            )
        )
        self.trig_mode_drop.setCurrentText(str(self.settings[f"trigger_mode"]))
        #
        self.trig_edge_label = QLabel("Trigger Edge:")
        self.trig_edge_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_edge_drop = QComboBox()
        self.trig_edge_drop.addItems(["Positive", "Negative"])
        self.trig_edge_drop.currentIndexChanged.connect(
            lambda: self.update_setting(
                f"trigger_edge", self.trig_edge_drop.currentText()
            )
        )
        self.trig_edge_drop.setCurrentText(str(self.settings[f"trigger_edge"]))
        #
        self.trig_z_label = QLabel("Ext. Trigger Zin:")
        self.trig_z_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_z_drop = QComboBox()
        self.trig_z_drop.addItems(["50 Ohms", "Hi-Z"])
        self.trig_z_drop.currentIndexChanged.connect(
            lambda: self.update_setting(f"ext_trig_Zin", self.trig_z_drop.currentText())
        )
        self.trig_z_drop.setCurrentText(str(self.settings[f"ext_trig_Zin"]))
        #
        self.trig_lev_label = QLabel("Ext Trig Level (V):")
        self.trig_lev_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_lev_edit = QDoubleSpinBox()
        self.trig_lev_edit.editingFinished.connect(
            lambda: self.update_setting("trigger_level", self.trig_lev_edit.text())
        )
        self.trig_lev_edit.setDecimals(3)
        self.trig_lev_edit.setSingleStep(0.05)
        if hasattr(backend, "ExternalTriggerThreshold"):
            self.trig_lev_edit.setRange(
                -backend.ExternalTriggerThreshold, backend.ExternalTriggerThreshold,
            )
        self.trig_lev_edit.setValue(float(self.settings["trigger_level"]))
        #
        self.single_trig_but = QPushButton()
        self.single_trig_but.setText("Single Trigger")
        self.single_trig_but.setIcon(
            QIcon(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "/icons/pulse.png"
                    )
                )
            )
        )
        self.single_trig_but.setCheckable(False)
        self.single_trig_but.clicked.connect(lambda: self.command("single_trigger"))
        self.single_trig_but.setEnabled(self.trig_mode_drop.currentText() == "Single")
        #
        self.pulse_label = QLabel("Pulses per Burst:")
        self.pulse_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.pulse_edit = QSpinBox()
        self.pulse_edit.editingFinished.connect(
            lambda: self.update_setting("pulses_per_burst", self.pulse_edit.text())
        )
        if hasattr(backend, "PulsesPerBurst"):
            self.pulse_edit.setRange(2, backend.PulsesPerBurst)
        self.pulse_edit.setValue(int(self.settings["pulses_per_burst"]))
        #
        self.period_label = QLabel("Triggers per Burst:")
        self.period_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.period_edit = QSpinBox()
        self.period_edit.setMinimum(1)
        self.period_edit.editingFinished.connect(
            lambda: self.update_setting("trigger_period", self.period_edit.text())
        )
        self.period_edit.setSingleStep(1)
        self.period_edit.setValue(int(self.settings["trigger_period"]))
        #
        self.write_label = QLabel("Command: ")
        self.write_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.write_edit = QLineEdit()
        self.write_edit.editingFinished.connect(
            lambda: self.update_setting("direct_command", self.write_edit.text())
        )
        self.write_edit.setText(self.settings["direct_command"])
        #
        self.write_but = QPushButton()
        self.write_but.setText("Write")
        self.write_but.setCheckable(False)
        self.write_but.clicked.connect(
            lambda: self.command(self.settings["direct_command"])
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

            self.channel_widgets.append(DelayChannelWidget(self, 1, 2))
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, widget_col)
            widget_col += 1

            self.channel_widgets.append(DelayChannelWidget(self, 3, 4))
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, widget_col)
            widget_col += 1
        if channels == 2:
            for i in range(1, 3):
                self.channel_widgets.append(DelayChannelWidget(self, i))
                self.channel_box_layout.addWidget(
                    self.channel_widgets[-1], 0, widget_col
                )
                widget_col += 1

            self.channel_widgets.append(DelayChannelWidget(self, 1, 2))
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
        #
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

    def enableDisableWidgets(self, setting: str, value: str):

        if setting == "trigger_mode":
            if value == "Single":
                self.single_trig_but.setEnabled(True)
            else:
                self.single_trig_but.setEnabled(False)

    def default_state(self):
        """Create the defualt state variable"""

        dflt = {}

        dflt["trigger_mode"] = "INT"
        dflt["trigger_edge"] = "POS"
        dflt["ext_trig_Zin"] = "HiZ"
        dflt["burst_count"] = "2"
        dflt["burst_period"] = "4"
        dflt["direct_command"] = ""
        dflt["pulses_per_burst"] = "2"
        dflt["trigger_period"] = "4"
        dflt["trigger_level"] = "0"
        for c in range(1, self.channels + 1):
            dflt[f"CH{c}_delay"] = "1"
            dflt[f"CH{c}_relative"] = "Trig"
            dflt[f"CH{c}_output_mode"] = "TTL"
            dflt[f"CH{c}_output_amplitude"] = "5"
        if self.channels == 4:
            dflt[f"CH12_output_mode"] = "TTL"
            dflt[f"CH12_output_amplitude"] = "5"
            dflt[f"CH34_output_mode"] = "TTL"
            dflt[f"CH34_output_amplitude"] = "5"
        if self.channels == 2:
            dflt[f"CH12_output_mode"] = "TTL"
            dflt[f"CH12_output_amplitude"] = "5"
        return dflt

    def settings_to_UI(self):

        self.trig_mode_drop.setCurrentText(str(self.settings[f"trigger_mode"]))
        self.trig_edge_drop.setCurrentText(str(self.settings[f"trigger_edge"]))
        self.trig_z_drop.setCurrentText(str(self.settings[f"ext_trig_Zin"]))
        self.trig_lev_edit.setValue(float(self.settings["trigger_level"]))
        self.pulse_edit.setValue(int(self.settings["pulses_per_burst"]))
        self.period_edit.setValue(int(self.settings["trigger_period"]))
        self.write_edit.setText(self.settings["direct_command"])

        for cw in self.channel_widgets:
            cw.settings_to_UI()


class DelayChannelWidget(QWidget):
    def __init__(self, main_widget, channel, combine_with: int = -1, use_alpha=True):

        super().__init__()

        self.channel = channel
        self.main_widget = main_widget
        self.combine_with = combine_with
        self.combined_channel_num = channel
        if combine_with != -1:
            self.combined_channel_num = channel * 10 + combine_with

        def num_to_alpha(x: int):
            if x == 1:
                return "A"
            if x == 2:
                return "B"
            if x == 3:
                return "C"
            if x == 4:
                return "D"
            else:
                return "?"

        if use_alpha:
            channel_str = num_to_alpha(channel)
            combine_with_str = num_to_alpha(combine_with)

        self.channel_label = QLabel()
        if combine_with == -1:
            self.channel_label.setText(f"Channel {channel_str}")
        else:
            self.channel_label.setText(f"Channel {channel_str}+{combine_with_str}")
        self.channel_label.setFont(QFont("Arial", 20))
        self.channel_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.time_label = QLabel("t_offset: ")

        self.time_edit = QLineEdit()
        self.time_edit.setValidator(QDoubleValidator())
        self.time_edit.editingFinished.connect(
            lambda: self.delay_changed(self.time_edit.text())
        )
        self.time_edit.setText("0")

        self.rel_label = QLabel("Relative to:")

        self.rel_drop = QComboBox()
        rels = ["Trig", "A", "B", "C", "D", "T0"]
        rels.remove(channel_str)
        self.rel_drop.addItems(rels)
        self.rel_drop.setCurrentText("Trig")
        self.rel_drop.currentIndexChanged.connect(
            lambda: self.relative_changed(self.rel_drop.currentText())
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
            lambda: self.set_output_level(self.level_drop.currentText())
        )

        self.channel_layout = QGridLayout()
        self.channel_layout.addWidget(self.channel_label, 0, 0, 1, 2)
        if combine_with == -1:
            self.channel_layout.addWidget(self.time_edit, 1, 1)
            self.channel_layout.addWidget(self.time_label, 1, 0)
            self.channel_layout.addWidget(self.rel_label, 2, 0)
            self.channel_layout.addWidget(self.rel_drop, 2, 1)
        else:
            self.blank_label = QLabel(" ")
            self.channel_layout.addWidget(self.blank_label, 1, 0, 1, 2)
            self.blank_label2 = QLabel(" ")
            self.channel_layout.addWidget(self.blank_label2, 2, 0, 1, 2)
        self.channel_layout.addWidget(self.level_label, 3, 0)
        self.channel_layout.addWidget(self.level_drop, 3, 1)
        self.channel_layout.addWidget(self.volt_edit_label, 4, 0)
        self.channel_layout.addWidget(self.volt_edit, 4, 1)
        self.setLayout(self.channel_layout)

        self.settings_to_UI()

    def settings_to_UI(self):

        if self.combine_with == -1:
            self.time_edit.setText(
                self.main_widget.settings[f"CH{self.combined_channel_num}_delay"]
            )
            self.rel_drop.setCurrentText(
                self.main_widget.settings[f"CH{self.combined_channel_num}_relative"]
            )
        mode = self.main_widget.settings[f"CH{self.combined_channel_num}_output_mode"]
        if mode == "VAR":
            mode = "Voltage"
        self.level_drop.setCurrentText(mode)
        self.volt_edit.setText(
            self.main_widget.settings[f"CH{self.combined_channel_num}_output_amplitude"]
        )

    def set_output_level(self, new_val: str):
        """
        Sets the output mode for the channel
        """
        if new_val is None:
            return

        if new_val == "Voltage":
            self.volt_edit.setEnabled(True)
            new_val = "VAR"
        else:
            self.volt_edit.setEnabled(False)

        self.main_widget.update_setting(
            f"CH{self.combined_channel_num}_output_mode", new_val
        )

    def voltage_changed(self, new_val: str):
        """
        Sets a new output amplitude
        """

        self.main_widget.update_setting(
            f"CH{self.combined_channel_num}_output_offset", "0"
        )
        self.main_widget.update_setting(
            f"CH{self.combined_channel_num}_output_amplitude", new_val
        )

    def relative_changed(self, rel_to: str):

        self.main_widget.update_setting(
            f"CH{self.combined_channel_num}_relative", rel_to
        )

    def delay_changed(self, t_delay: str):

        self.main_widget.update_setting(f"CH{self.combined_channel_num}_delay", t_delay)
