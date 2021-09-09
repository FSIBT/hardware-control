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

    def __init__(
        self,
        app,
        instrument: str,
    ):

        super().__init__()

        self.app = app
        self.instrument = instrument

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
            items=["Positive", "Negative"],
        )

        self.trig_impedance = HCComboBox(
            self.app,
            self.instrument,
            parameter="EXT_TRIG_ZIN",
            label="Ext. Trigger Zin",
            label_align="right",
            items=["50-Ohms", "Hi-Z"],
        )

        self.trig_level = HCDoubleSpinBox(
            self.app,
            self.instrument,
            "TRIGGER_LEVEL",
            label="Ext Trig Level (V):",
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
            label="Pulses per Burst:",
            label_align="right",
        )

        self.period = HCSpinBox(
            self.app,
            self.instrument,
            "TRIGGER_PERIOD",
            label="Triggers per Burst:",
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
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.app.globalRefreshRate)

    def enable_disable_hook(self, value):
        if value == "SINGLE":
            self.single_trig_but.setEnabled(True)
        else:
            self.single_trig_but.setEnabled(False)
        return value

    def update_readout(self):
        """Queries the instrument for current readout data."""

        for parameter in [
            "TRIGGER_MODE",
            "TRIGGE_EDGE",
            "EXT_TRIG_ZIN",
            "TRIGGER_LEVEL",
            "PULSES_PER_BURST",
            "TRIGGER_PERIOD",
        ]:
            self.app.update_instrument_parameter(self.instrument, parameter)

        for ch in self.channel_widgets:
            if getattr(ch, "time_delay", None):
                self.app.update_instrument_parameter(
                    self.instrument, ch.time_delay.parameter
                )
            self.app.update_instrument_parameter(self.instrument, ch.volt.parameter)
            self.app.update_instrument_parameter(self.instrument, ch.level.parameter)


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

    def __init__(self, app, instrument, channel: str):

        super().__init__()

        self.channel = channel
        self.app = app
        self.instrument = instrument

        self.channel = channel
        self.channel_label = QLabel(f"Channel {channel}")
        self.channel_label.setFont(QFont("Arial", 20))
        self.channel_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        if channel not in ["AB", "CD"]:
            self.time_delay = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{self.channel}_T0_DELAY",
                label="t_offset [s]",
            )

        rels = ["Trig0", "T0", "A", "B", "C", "D"]
        if channel not in ["AB", "CD"]:
            rels = rels[: rels.index(self.channel)]
            self.relative_label = QLabel("Relative to")
            self.relative = QComboBox()
            self.relative.addItems(rels)
            self.relative.currentIndexChanged.connect(
                lambda: self.update_relative_channel(self.relative)
            )

        self.volt = HCLineEdit(
            self.app,
            self.instrument,
            f"CH{self.channel}_OUTPUT_AMPLITUDE",
            label="High Level (V)",
        )
        self.volt.setEnabled(False)

        self.level = HCComboBox(
            self.app,
            self.instrument,
            f"CH{self.channel}_OUTPUT_MODE",
            label="Output mode",
            items=["TTL", "Voltage", "NIM", "ECL"],
        )
        self.app.add_hook(
            self.instrument,
            f"CH{self.channel}_OUTPUT_MODE",
            when="pre_set_hooks",
            function=lambda x: self.set_output_level_hook(x),
        )

        self.channel_layout = QGridLayout()
        self.channel_layout.addWidget(self.channel_label, 0, 0, 1, 2)
        if self.channel not in ["AB", "CD"]:
            self.channel_layout.addWidget(self.time_delay.label, 1, 0)
            self.channel_layout.addWidget(self.time_delay, 1, 1)
            self.channel_layout.addWidget(self.relative_label, 2, 0)
            self.channel_layout.addWidget(self.relative, 2, 1)

        self.channel_layout.addWidget(self.level.label, 3, 0)
        self.channel_layout.addWidget(self.level, 3, 1)
        self.channel_layout.addWidget(self.volt.label, 4, 0)
        self.channel_layout.addWidget(self.volt, 4, 1)
        self.setLayout(self.channel_layout)

    def update_relative_channel(self, widget):
        value = widget.currentText()
        self.time_delay.parameter = f"CH{self.channel}_{value}_DELAY"
        logger.debug(f"updating delay CH{self.channel}->{value}")

    def set_output_level_hook(self, value, widget):
        if value is None:
            return

        if value == "VOLTAGE":
            self.volt.setEnabled(True)
            value = "VAR"
        else:
            self.volt.setEnabled(False)
        return value
