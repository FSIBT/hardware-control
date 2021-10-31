import logging

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator
from PyQt5.QtWidgets import (
    QGroupBox,
    QComboBox,
    QLabel,
    QGridLayout,
    QWidget,
)

from ..widgets import (
    load_icon,
    HCLineEdit,
    HCComboBox,
    HCDoubleSpinBox,
    HCPushButton,
    HCSpinBox,
)

logger = logging.getLogger(__name__)


class DelayGenerator(QGroupBox):
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

    def __init__(self, app, instrument_name: str, widget_name: str = "Delay Generator"):

        super().__init__(widget_name)

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

        self.trig_edge = HCComboBox(
            self.app,
            self.instrument,
            parameter="TRIGGER_EDGE",
            label="Trigger Edge",
            label_align="right",
            items=["POS", "NEG"],
        )

        self.trig_impedance = HCComboBox(
            self.app,
            self.instrument,
            parameter="TRIGGER_IMPEDANCE",
            label="Trigger Impedance",
            label_align="right",
            items=["50-Ohms", "Hi-Z"],
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

        self.app.add_hook(
            self.instrument,
            "TRIGGER_MODE",
            "post_read_hooks",
            lambda x: self.enable_disable_hook(x),
        )

        self.pulse = HCSpinBox(
            self.app,
            self.instrument,
            "PULSES_PER_BURST",
            label="Pulses per Burst",
            label_align="right",
        )

        self.period = HCSpinBox(
            self.app,
            self.instrument,
            "TRIGGER_PERIOD",
            label="Triggers per Bursts",
            label_align="right",
        )
        self.period.setSingleStep(1)
        self.period.setMinimum(1)

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
        self.master_layout.addWidget(self.trig_impedance.label, 0, 2)
        self.master_layout.addWidget(self.trig_impedance, 0, 3)

        self.master_layout.addWidget(self.trig_edge.label, 1, 0)
        self.master_layout.addWidget(self.trig_edge, 1, 1)
        self.master_layout.addWidget(self.trig_level.label, 1, 2)
        self.master_layout.addWidget(self.trig_level, 1, 3)

        self.master_layout.addWidget(self.single_trig_but, 2, 3)

        self.master_layout.addWidget(self.pulse.label, 3, 0)
        self.master_layout.addWidget(self.pulse, 3, 1)

        self.master_layout.addWidget(self.period.label, 3, 2)
        self.master_layout.addWidget(self.period, 3, 3)

        self.master_layout.addWidget(self.channel_box, 4, 0, 1, 4)

        self.setLayout(self.master_layout)

        # Create timer to query instrument
        self.config_auto_update()

    def enable_disable_hook(self, value):
        if value == "SINGLE":
            self.single_trig_but.setEnabled(True)
        else:
            self.single_trig_but.setEnabled(False)
        return value

    def config_auto_update(self):
        """Queries the instrument for current readout data."""

        for parameter in [
            "TRIGGER_MODE",
            "TRIGGER_EDGE",
            "TRIGGER_IMPEDANCE",
            "TRIGGER_LEVEL",
            "PULSES_PER_BURST",
            "TRIGGER_PERIOD",
        ]:
            self.app.add_auto_update_instrument_parameter(self.instrument, parameter)

        for ch in self.channel_widgets:
            if getattr(ch, "time_delay", None):
                self.app.add_auto_update_instrument_parameter(
                    self.instrument, ch.time_delay.parameter
                )
            self.app.add_auto_update_instrument_parameter(
                self.instrument, ch.volt.parameter
            )
            self.app.add_auto_update_instrument_parameter(
                self.instrument, ch.level.parameter
            )


class DelayChannelWidget(QWidget):
    """A Qt-widget that implements controls for a single channel of a delay generator.

    Used together with :py:class:`DelayGenerator`.

    .. image:: /images/controls/DelayGenerator-channel.png
      :height: 200


    Parameters
    ----------

    main_widget : DelayGenerator
        The main widget where this is used in
    channel : str
        The channel this widget controls. Normally A, B, C, or D, but AB and CD are also
        allowed for combined channels that, for example, exist in the SRS DG533.

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

        rels = ["TRIG", "T0", "A", "B", "C", "D"]

        if channel not in ["AB", "CD"]:
            self.time_delay = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{self.channel}_DELAY",
                label="t_offset [s]",
                return_set_value=False,
            )
            self.app.add_hook(
                self.instrument,
                f"CH{self.channel}_DELAY",
                when="pre_set_hooks",
                function=lambda delay: self.update_delay(delay),
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
                function=lambda relative_channel: self.update_relative_channel(
                    relative_channel
                ),
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
            function=lambda x: self.set_output_level_hook(x),
        )

        self.volt = HCLineEdit(
            self.app,
            self.instrument,
            f"CH{self.channel}_OUTPUT_AMPLITUDE",
            label="High Level (V)",
        )
        self.volt.setEnabled(False)
        self.volt.setStyleSheet("background-color: grey")

        self.channel_layout = QGridLayout()
        self.channel_layout.addWidget(
            self.channel_label, 0, 0, 1, 2, QtCore.Qt.AlignBottom
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
        self.setLayout(self.channel_layout)

    def update_relative_channel(self, relative_channel):
        """Add a hook to self.relative widget.

        When updating the relative channel, send both the new
        channel which will signify a delay of 0 and the current delay.

        """

        relative_channel = self._CHANNEL_NAMES[relative_channel]
        return f"{relative_channel},{self.time_delay.text()}"

    def update_delay(self, delay):
        """Add a hook to self.time_delay widget.

        When updating a channel's time delay, send both the channel
        which signifies a delay of 0 and the new delay.

        """

        relative_channel = self._CHANNEL_NAMES[self.relative.currentText()]
        return f"{relative_channel},{delay}"

    def set_output_level_hook(self, value):
        if value is None:
            return

        if value == "VAR":
            self.volt.setDisabled(False)
            self.volt.setStyleSheet("background-color: white")
        else:
            self.volt.setDisabled(True)
            self.volt.setStyleSheet("background-color: grey")
        return value
