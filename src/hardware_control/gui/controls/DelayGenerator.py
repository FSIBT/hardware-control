"""
.. image:: /images/controls/DelayGenerator.png
"""

import logging

from PyQt6 import QtCore
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import (
    QGroupBox,
    QLabel,
    QGridLayout,
    QWidget,
)

from ...base.gui_control import ValidatedControl
from ..widgets import (
    load_icon,
    HCLineEdit,
    HCComboBox,
    HCDoubleSpinBox,
    HCPushButton,
    HCSpinBox,
)
from ...base.hooks import format_float

logger = logging.getLogger(__name__)


class DelayGenerator(ValidatedControl, QGroupBox):
    """A GUI for delay generators.

    This implements many front panel functions of an SRS DG535 and
    also contains some elements that are unique to this
    instrument.

    See Also
    --------
    hardware_control.instruments.srs.SRS_DG535.SRS_DG535
    """

    # Required instrument parameters (validated automatically in __init__)
    _required_parameters = [
        "TRIGGER_MODE",
        "TRIGGER_EDGE",
        "TRIGGER_LEVEL",
        "PULSES_PER_BURST",
        "TRIGGER_PERIOD",
        "BURST_TRIGGER_RATE",
        "INTERNAL_TRIGGER_RATE",
        # Channel A parameters
        "CHA_DELAY",
        "CHA_RELATIVE_TO",
        "CHA_OUTPUT_MODE",
        "CHA_OUTPUT_AMPLITUDE",
        "CHA_OUTPUT_OFFSET",
        "CHA_TRIGGER_IMPEDANCE",
        # Channel B parameters
        "CHB_DELAY",
        "CHB_RELATIVE_TO",
        "CHB_OUTPUT_MODE",
        "CHB_OUTPUT_AMPLITUDE",
        "CHB_OUTPUT_OFFSET",
        "CHB_TRIGGER_IMPEDANCE",
        # Channel C parameters (4-channel only)
        "CHC_DELAY",
        "CHC_RELATIVE_TO",
        "CHC_OUTPUT_MODE",
        "CHC_OUTPUT_AMPLITUDE",
        "CHC_OUTPUT_OFFSET",
        "CHC_TRIGGER_IMPEDANCE",
        # Channel D parameters (4-channel only)
        "CHD_DELAY",
        "CHD_RELATIVE_TO",
        "CHD_OUTPUT_MODE",
        "CHD_OUTPUT_AMPLITUDE",
        "CHD_OUTPUT_OFFSET",
        "CHD_TRIGGER_IMPEDANCE",
        # Combined channel AB parameters
        "CHAB_OUTPUT_MODE",
        "CHAB_OUTPUT_AMPLITUDE",
        "CHAB_OUTPUT_OFFSET",
        "CHAB_TRIGGER_IMPEDANCE",
        # Combined channel CD parameters (4-channel only)
        "CHCD_OUTPUT_MODE",
        "CHCD_OUTPUT_AMPLITUDE",
        "CHCD_OUTPUT_OFFSET",
        "CHCD_TRIGGER_IMPEDANCE",
    ]
    _required_commands = ["SINGLE_TRIGGER"]

    def __init__(self, app, instrument_name: str, widget_name: str = "Delay Generator"):
        # Validation happens automatically in super().__init__
        super().__init__(app, instrument_name, widget_name)

        self.app = app
        self.instrument = instrument_name
        self.channels = 4

        # Create GUI
        self.trig_mode = HCComboBox(
            self.app,
            self.instrument,
            parameter="TRIGGER_MODE",
            label="Trigger Mode",
            label_align="right",
            items=["Internal", "External", "Single", "Burst"],
        )
        self.app.add_hook(
            self.instrument,
            "TRIGGER_MODE",
            "pre_set_hooks",
            self.enable_disable_hook,
        )

        self.trig_edge = HCComboBox(
            self.app,
            self.instrument,
            parameter="TRIGGER_EDGE",
            label="Trigger Edge",
            label_align="right",
            items=["POS", "NEG"],
        )

        self.trig_level = HCDoubleSpinBox(
            self.app,
            self.instrument,
            "TRIGGER_LEVEL",
            label="Ext Trig Level (V)",
            label_align="right",
        )
        self.trig_level.setDecimals(3)
        self.trig_level.setSingleStep(0.05)

        self.single_trig_but = HCPushButton(
            self.app, self.instrument, "SINGLE_TRIGGER", label="Single Trigger"
        )
        self.single_trig_but.setIcon(QIcon(load_icon("pulse.png")))
        self.single_trig_but.setCheckable(False)

        self.pulse = HCSpinBox(
            self.app,
            self.instrument,
            "PULSES_PER_BURST",
            label="Pulses per Burst",
            label_align="right",
        )
        self.pulse.setVisible(False)
        self.pulse.label.setVisible(False)

        self.period = HCSpinBox(
            self.app,
            self.instrument,
            "TRIGGER_PERIOD",
            label="Triggers per Bursts",
            label_align="right",
        )
        self.period.setSingleStep(1)
        self.period.setMinimum(1)
        self.period.setVisible(False)
        self.period.label.setVisible(False)

        self.burst_rate = HCSpinBox(
            self.app,
            self.instrument,
            "BURST_TRIGGER_RATE",
            label="Trigger Rate",
            label_align="right",
        )
        self.burst_rate.setVisible(False)
        self.burst_rate.label.setVisible(False)

        self.internal_rate = HCSpinBox(
            self.app,
            self.instrument,
            "INTERNAL_TRIGGER_RATE",
            label="Trigger Rate",
            label_align="right",
        )

        widget_col = 0
        self.channel_widgets = []
        self.channel_box = QGroupBox()
        self.channel_box_layout = QGridLayout()
        if self.channels == 4:
            for i in ["A", "B", "C", "D", "AB", "CD"]:
                self.channel_widgets.append(
                    DelayChannelWidget(self.app, self.instrument, i)
                )
                self.channel_box_layout.addWidget(
                    self.channel_widgets[-1], 0, widget_col
                )
                widget_col += 1

        if self.channels == 2:
            for i in ["A", "B", "AB"]:
                self.channel_widgets.append(
                    DelayChannelWidget(self.app, self.instrument, i)
                )
                self.channel_box_layout.addWidget(
                    self.channel_widgets[-1], 0, widget_col
                )
                widget_col += 1

        self.channel_box.setLayout(self.channel_box_layout)

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.trig_mode.label, 0, 0)
        self.master_layout.addWidget(self.trig_mode, 0, 1)
        self.master_layout.addWidget(self.trig_level.label, 0, 2)
        self.master_layout.addWidget(self.trig_level, 0, 3)
        self.master_layout.addWidget(self.single_trig_but, 1, 1)
        self.master_layout.addWidget(self.trig_edge.label, 1, 2)
        self.master_layout.addWidget(self.trig_edge, 1, 3)

        self.master_layout.addWidget(self.burst_rate.label, 2, 0)
        self.master_layout.addWidget(self.burst_rate, 2, 1)
        self.master_layout.addWidget(self.internal_rate.label, 2, 0)
        self.master_layout.addWidget(self.internal_rate, 2, 1)
        self.master_layout.addWidget(self.pulse.label, 2, 2)
        self.master_layout.addWidget(self.pulse, 2, 3)
        self.master_layout.addWidget(self.period.label, 3, 2)
        self.master_layout.addWidget(self.period, 3, 3)

        self.master_layout.addWidget(self.channel_box, 4, 0, 1, 4)

        self.setLayout(self.master_layout)

    def enable_disable_hook(self, value):
        """Enable/Disable and show/hide certain inputs depending on the trigger mode."""
        if value == "Single":
            self.single_trig_but.setEnabled(True)
            self.single_trig_but.setStyleSheet("background-color: white")
        else:
            self.single_trig_but.setEnabled(False)
            self.single_trig_but.setStyleSheet("background-color: grey")

        if value == "Burst":
            self.pulse.setVisible(True)
            self.pulse.label.setVisible(True)
            self.period.setVisible(True)
            self.period.label.setVisible(True)
            self.burst_rate.setVisible(True)
            self.burst_rate.label.setVisible(True)
        else:
            self.pulse.setVisible(False)
            self.pulse.label.setVisible(False)
            self.period.setVisible(False)
            self.period.label.setVisible(False)
            self.burst_rate.setVisible(False)
            self.burst_rate.label.setVisible(False)

        if value == "Internal":
            self.internal_rate.setVisible(True)
            self.internal_rate.label.setVisible(True)
        else:
            self.internal_rate.setVisible(False)
            self.internal_rate.label.setVisible(False)

        return value


class DelayChannelWidget(QWidget):
    """A Qt-widget that implements controls for a single channel of a delay generator.

    Used together with :py:class:`DelayGenerator`.

    Parameters
    ----------

    main_widget : DelayGenerator
        The main widget in which the objects is used
    channel : str
        The channel the object controls. Normally A, B, C, or D, but AB and CD are also
        allowed for combined channels that, for example, exist in the SRS DG533 instrument.
    """

    _CHANNEL_NAMES = {
        "TRIG": 0,
        "T0": 1,
        "A": 2,
        "B": 3,
        "AB": 4,
        "C": 5,
        "D": 6,
        "CD": 7,
    }

    def __init__(self, app, instrument_name: str, channel: str):
        super().__init__()

        self.channel = channel
        self.app = app
        self.instrument = instrument_name

        self.channel = channel
        self.channel_label = QLabel(f"Channel {channel}")
        self.channel_label.setFont(QFont("Arial", 20))

        rels = ["T0", "A", "B", "C", "D"]

        if channel not in ["AB", "CD"]:
            self.time_delay = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{self.channel}_DELAY",
                label="t_offset [s]",
                default_txt="0.0",
            )
            self.app.add_hook(
                self.instrument,
                f"CH{self.channel}_DELAY",
                when="pre_set_hooks",
                function=self.update_delay,
            )

            rels.remove(self.channel)
            self.relative = HCComboBox(
                self.app,
                self.instrument,
                f"CH{self.channel}_RELATIVE_TO",
                label="Relative to",
                items=rels,
            )
            self.app.add_hook(
                self.instrument,
                f"CH{self.channel}_RELATIVE_TO",
                when="pre_set_hooks",
                function=self.update_relative_channel,
            )

        self.level = HCComboBox(
            self.app,
            self.instrument,
            f"CH{self.channel}_OUTPUT_MODE",
            label="Output mode",
            items=["TTL", "VAR", "NIM", "ECL"],
        )
        self.app.add_hook(
            self.instrument,
            f"CH{self.channel}_OUTPUT_MODE",
            when="pre_set_hooks",
            function=self.set_output_level_hook,
        )

        self.volt = HCLineEdit(
            self.app,
            self.instrument,
            f"CH{self.channel}_OUTPUT_AMPLITUDE",
            label="High Level (V)",
        )
        self.volt.setEnabled(False)
        self.volt.setStyleSheet("background-color: grey")

        self.offset = HCLineEdit(
            self.app,
            self.instrument,
            f"CH{self.channel}_OUTPUT_OFFSET",
            label="Output Offset (V)",
        )
        self.offset.setEnabled(False)
        self.offset.setStyleSheet("background-color: grey")

        self.trig_impedance = HCComboBox(
            self.app,
            self.instrument,
            f"CH{self.channel}_TRIGGER_IMPEDANCE",
            label="Trigger Impedance",
            items=["50-OHMS", "HI-Z"],
        )

        self.channel_layout = QGridLayout()
        self.channel_layout.addWidget(
            self.channel_label, 0, 0, 1, 2, QtCore.Qt.AlignmentFlag.AlignBottom
        )
        if self.channel not in ["AB", "CD"]:
            self.channel_layout.addWidget(self.time_delay.label, 1, 0)
            self.channel_layout.addWidget(self.time_delay, 1, 1)
            self.channel_layout.addWidget(self.relative.label, 2, 0)
            self.channel_layout.addWidget(self.relative, 2, 1)

        self.channel_layout.addWidget(self.level.label, 3, 0)
        self.channel_layout.addWidget(self.level, 3, 1)
        self.channel_layout.addWidget(self.volt.label, 4, 0)
        self.channel_layout.addWidget(self.volt, 4, 1)
        self.channel_layout.addWidget(self.offset.label, 5, 0)
        self.channel_layout.addWidget(self.offset, 5, 1)
        self.channel_layout.addWidget(self.trig_impedance.label, 6, 0)
        self.channel_layout.addWidget(self.trig_impedance, 6, 1)
        self.setLayout(self.channel_layout)

    def update_relative_channel(self, relative_channel):
        """When updating the relative channel, send both the relative channel and the delay."""
        self.relative.setCurrentText(relative_channel)
        relative_channel = self._CHANNEL_NAMES[relative_channel]
        return f"{relative_channel},{self.time_delay.text()}"

    def update_delay(self, delay):
        """When updating a channel's time delay, send both the relative channel and the delay."""
        self.time_delay.setText(delay)
        relative_channel = self._CHANNEL_NAMES[self.relative.currentText()]
        return f"{relative_channel},{delay}"

    def set_output_level_hook(self, value):
        """Only allow input for 'High Level' and 'Output Offset' when in 'Var' output mode."""
        if value is None:
            return

        if value == "VAR":
            self.volt.setDisabled(False)
            self.volt.setStyleSheet("background-color: white")
            self.offset.setDisabled(False)
            self.offset.setStyleSheet("background-color: white")
        else:
            self.volt.setDisabled(True)
            self.volt.setStyleSheet("background-color: grey")
            self.offset.setDisabled(True)
            self.offset.setStyleSheet("background-color: grey")
        return value
