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

from ..widgets import (
    load_icon,
    HCLineEdit,
    HCComboBox,
    HCDoubleSpinBox,
    HCPushButton,
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
        self, app, instrument: str,
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
            items=["50 Ohms", "Hi-Z"],
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
            "post_read_hook",
            hook=lambda x: self.enable_disable_hook(x),
        )

        self.pulse = HCSpinBox(
            self.app,
            self.instrument,
            "PULSES_PER_BURST",
            label="Pulses per Burst:",
            label_align="right",
        )

        self.period.HCSpinBox(
            self.app,
            self.instrment,
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
            for i in range(1, 5):
                self.channel_widgets.append(
                    DelayChannelWidget(self.app, self.instrument, i)
                )
                self.channel_box_layout.addWidget(
                    self.channel_widgets[-1], 0, widget_col
                )
                widget_col += 1

            self.channel_widgets.append(
                DelayChannelWidget(self.app, self.instrument, 12)
            )
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, widget_col)
            widget_col += 1

            self.channel_widgets.append(
                DelayChannelWidget(self.app, self.instrument, 34)
            )
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, widget_col)
            widget_col += 1
        if self.channels == 2:
            for i in range(1, 3):
                self.channel_widgets.append(
                    DelayChannelWidget(self.app, self.instrument, i)
                )
                self.channel_box_layout.addWidget(
                    self.channel_widgets[-1], 0, widget_col
                )
                widget_col += 1

            self.channel_widgets.append(
                DelayChannelWidget(self.app, self.instrument, 12)
            )
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, widget_col)
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

    def enable_disable_hook(self, value):
        if value == "SINGLE":
            self.single_trig_but.setEnabled(True)
        else:
            self.single_trig_but.setEnabled(False)
        return value


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

    def __init__(self, app, instrument, channel: int, use_alpha: bool = True):

        super().__init__()

        self.channel = channel
        self.app = app
        self.instrument = instrument

        if use_alpha:
            channel_str = DelayChannelWidget.num_to_alpha.get(channel, "?")
        else:
            channel_str = str(self.channel)

        self.channel_label = QLabel()
        self.channel_label.setText(f"Channel {channel_str}")
        self.channel_label.setFont(QFont("Arial", 20))
        self.channel_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        if channel not in [12, 34]:
            self.time_delay = HCLineEdit(
                self.app,
                self.instrument,
                f"CH{self.channel}_DELAY",
                label="t_offset [s]",
            )

        rels = ["Trig", "A", "B", "C", "D", "T0"]
        if channel not in [12, 34]:
            rels.remove(channel_str.title())
            self.relative = HCComboBox(
                self.app,
                self.instrument,
                f"CH{self.channel}_RELATIVE",
                label="Relative to",
                items=rels,
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
        if self.channel not in [12, 34]:
            self.channel_layout.addWidget(self.time_delay.label, 1, 0)
            self.channel_layout.addWidget(self.time_delay, 1, 1)
            self.channel_layout.addWidget(self.relative.label, 2, 0)
            self.channel_layout.addWidget(self.relative, 2, 1)

        self.channel_layout.addWidget(self.level.label, 3, 0)
        self.channel_layout.addWidget(self.level, 3, 1)
        self.channel_layout.addWidget(self.volt.label, 4, 0)
        self.channel_layout.addWidget(self.volt, 4, 1)
        self.setLayout(self.channel_layout)

    def set_output_level_hook(self, value, widget):
        if value is None:
            return

        if value == "VOLTAGE":
            self.volt.setEnabled(True)
            value = "VAR"
        else:
            self.volt.setEnabled(False)
        return value
