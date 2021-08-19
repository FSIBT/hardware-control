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
    QControl,
    QControlCombo,
    QControlDoubleSpinBox,
    QControlPushButton,
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
        self.trig_mode = QControlCombo(
            self.app,
            self.instrument,
            parameter="TRIGGER_MODE",
            label="Trigger Mode",
            label_align="right",
            items=["Internal", "External", "Single", "Burst"],
        )

        self.trig_edge = QControlCombo(
            self.app,
            self.instrument,
            parameter="TRIGGER_EDGE",
            label="Trigger Edge",
            label_align="right",
            items=["Positive", "Negative"],
        )

        self.trig_impedance = QControlCombo(
            self.app,
            self.instrument,
            parameter="EXT_TRIG_ZIN",
            label="Ext. Trigger Zin",
            label_align="right",
            items=["50 Ohms", "Hi-Z"],
        )

        self.trig_level = QControlDoubleSpinBox(
            self.app,
            self.instrument,
            "TRIGGER_LEVEL",
            label="Ext Trig Level (V):",
            label_align="right",
        )
        self.trig_level.setDecimals(3)
        self.trig_level.setSingleStep(0.05)

        self.single_trig_but = QControlPushButton(
            self.app, self.instrument, "SINGLE_TRIGGER", label="Single Trigger"
        )
        self.single_trig_but.setIcon(QIcon(load_icon("pulse.png")))
        self.single_trig_but.setCheckable(False)

        self.app.add_hook(
            "post_read_hook",
            self.instrument,
            "TRIGGER_MODE",
            hook=self.enable_disable_hook,
            args=[self],
        )

        self.pulse_label = QLabel("Pulses per Burst:")
        self.pulse_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        #        self.pulse_edit = QSpinBox()
        #        self.pulse_edit.editingFinished.connect(
        #            lambda: self.update_setting("PULSES_PER_BURST", self.pulse_edit.text())
        #        )
        #        if hasattr(backend, "PulsesPerBurst"):
        #            self.pulse_edit.setRange(2, backend.PulsesPerBurst)
        #        self.pulse_edit.setValue(int(self.settings["PULSES_PER_BURST"]))
        #
        self.period_label = QLabel("Triggers per Burst:")
        self.period_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        #        self.period_edit = QSpinBox()
        #        self.period_edit.setMinimum(1)
        #        self.period_edit.editingFinished.connect(
        #            lambda: self.update_setting("TRIGGER_PERIOD", self.period_edit.text())
        #        )
        #        self.period_edit.setSingleStep(1)
        #        self.period_edit.setValue(int(self.settings["TRIGGER_PERIOD"]))
        #
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

        self.master_layout.addWidget(self.pulse_label, 3, 0)
        # self.master_layout.addWidget(self.pulse_edit, 3, 1)
        #
        self.master_layout.addWidget(self.period_label, 3, 2)
        # self.master_layout.addWidget(self.period_edit, 3, 3)
        #
        # self.master_layout.addWidget(self.channel_box, 4, 0, 1, 4)

        self.setLayout(self.master_layout)

    def enable_disable_hook(self, value, widget):
        if value == "SINGLE":
            widget.single_trig_but.setEnabled(True)
        else:
            widget.single_trig_but.setEnabled(False)
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
            self.time_delay = QControl(
                self.app,
                self.instrument,
                f"CH{self.channel}_DELAY",
                label="t_offset [s]",
            )

        rels = ["Trig", "A", "B", "C", "D", "T0"]
        if channel not in [12, 34]:
            rels.remove(channel_str.title())
            self.relative = QControlCombo(
                self.app,
                self.instrument,
                f"CH{self.channel}_RELATIVE",
                label="Relative to",
                items=rels,
            )

        self.volt = QControl(
            self.app,
            self.instrument,
            f"CH{self.channel}_OUTPUT_AMPLITUDE",
            label="High Level (V)",
        )
        self.volt.setEnabled(False)

        self.level = QControlCombo(
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
            function=self.set_output_level_hook,
            args=[self],
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
            widget.volt.setEnabled(True)
            value = "VAR"
        else:
            widget.volt.setEnabled(False)
        return value
