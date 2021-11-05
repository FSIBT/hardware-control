import json
import logging
import pyqtgraph as pg
from typing import Optional, List

from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QGroupBox,
    QGridLayout,
    QWidget,
)

from ..widgets import (
    HCGridLayout,
    HCLineEdit,
    HCComboBox,
    HCDoubleSpinBox,
    HCPushButton,
    HCOnOffButton,
    HCHeader,
    HCDoubleSpinComboBox,
)

logger = logging.getLogger(__name__)


class Oscilloscope(QGroupBox):
    """A GUI for an Oscilloscope,

    Can be configured to only show certain channels and their controls.

    Parameters
    ----------
    app
       The main App instance
    instrument_name
       The name used to address the oscilloscope
    widget_name
       Name used in QGroupBox, defaults to Oscilloscope
    channels
       A list of channel number
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        widget_name: str = "Oscilloscope",
        channels: Optional[List] = None,
    ):

        super().__init__(widget_name)

        self.app = app
        self.instrument = instrument_name

        if channels is not None:
            self.channels = channels
        else:
            self.channels = [1, 2, 3, 4]

        self.disp = OscilloscopeDisplayWidget(
            self.app, self.instrument, channels=self.channels
        )
        self.horiz = OscilloscopeHorizontalWidget(self.app, self.instrument)
        self.trig = OscilloscopeTriggerWidget(self.app, self.instrument)

        widget_col = 0
        self.channel_widgets = []
        self.channel_box = QGroupBox()
        self.channel_box_layout = QGridLayout()
        for i in self.channels:
            self.channel_widgets.append(
                OscilloscopeChannelWidget(self.app, self.instrument, i)
            )
            self.channel_box_layout.addWidget(self.channel_widgets[-1], 0, widget_col)
            widget_col += 1
        self.channel_box.setLayout(self.channel_box_layout)

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.disp, 0, 0, 4, 2)
        self.master_layout.addWidget(self.horiz, 0, 2, 1, 1)
        self.master_layout.addWidget(self.trig, 0, 3, 2, 1)
        self.master_layout.addWidget(self.channel_box, 10, 0, 1, 4)
        self.setLayout(self.master_layout)

        self.default_update_readout()

    def default_update_readout(self) -> None:
        """Register certain parameterts to be automatically udpated every second."""

        update = [
            "TIMEBASE",
            "TIME_OFFSET",
            "NUM_POINTS",
            "LABELS_ENABLED",
            "TRIGGER_LEVEL",
            "TRIGGER_COUPLING",
            "TRIGGER_EDGE",
            "TRIGGER_CHANNEL",
        ]

        for ch in self.channel_widgets:
            update.append(f"CH{ch.channel}_VOLTS_DIV")
            update.append(f"CH{ch.channel}_OFFSET")
            update.append(f"CH{ch.channel}_LABEL")
            update.append(f"CH{ch.channel}_COUPLING")
            update.append(f"CH{ch.channel}_IMPEDANCE")
            update.append(f"CH{ch.channel}_PROBE_ATTEN")
            update.append(f"CH{ch.channel}_WAVEFORM")
            update.append(f"CH{ch.channel}_ON-OFF")
            update.append(f"CH{ch.channel}_BW_LIM")
            update.append(f"CH{ch.channel}_INVERT")

        for parameter in update:
            self.app.add_auto_update_instrument_parameter(self.instrument, parameter)


class OscilloscopeChannelWidget(QWidget):
    def __init__(
        self,
        app,
        instrument_name: str,
        channel: int,
    ):

        super().__init__()

        self.app = app
        self.instrument = instrument_name
        self.channel = channel
        self.colors = {0: "yellow", 1: "green", 2: "blue", 3: "red"}

        self.channel_label = HCHeader(
            f"channel{self.channel}_{self.colors[self.channel-1]}.png"
        )
        self.channel_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.volts_div = HCDoubleSpinBox(
            self.app,
            self.instrument,
            f"CH{self.channel}_VOLTS_DIV",
            label="Volts/Div (V)",
            label_align="right",
        )

        self.volts_offset = HCDoubleSpinBox(
            self.app,
            self.instrument,
            f"CH{self.channel}_OFFSET",
            label="Vert. Offset (V)",
            label_align="right",
        )

        self.label = HCLineEdit(
            self.app,
            self.instrument,
            f"CH{self.channel}_LABEL",
            label="Label",
            label_align="right",
        )

        self.on_off_but = HCOnOffButton(
            self.app,
            self.instrument,
            f"CH{self.channel}_ON-OFF",
            label="On/Off",
            label_align="right",
            text_checked=" On",
            text_unchecked="Off",
        )

        self.BW_but = HCOnOffButton(
            self.app,
            self.instrument,
            f"CH{self.channel}_BW_LIM",
            label="BW Limit",
            label_align="right",
            text_checked="BW_limit  on",
            text_unchecked="BW_limit off",
        )

        self.Inv_but = HCOnOffButton(
            self.app,
            self.instrument,
            f"CH{self.channel}_INVERT",
            label="Invert",
            label_align="right",
            text_checked="  Inverted  ",
            text_unchecked="Not Inverted",
        )

        self.coupling = HCComboBox(
            self.app,
            self.instrument,
            parameter=f"CH{channel}_COUPLING",
            label="Coupling",
            label_align="right",
            items=["AC", "DC"],
        )

        self.impedance = HCComboBox(
            self.app,
            self.instrument,
            parameter=f"CH{channel}_IMPEDANCE",
            label="Impedance",
            label_align="right",
            items=["1e6", "50"],
        )

        self.probe_atten = HCComboBox(
            self.app,
            self.instrument,
            parameter=f"CH{channel}_PROBE_ATTEN",
            label="Probe Attenuation",
            label_align="right",
            items=[".001", ".01", ".1", "1", "10", "100", "1000"],
        )

        self.channel_layout = HCGridLayout(
            [
                self.volts_div,
                self.volts_offset,
                self.label,
                self.on_off_but,
                self.BW_but,
                self.Inv_but,
                self.coupling,
                self.impedance,
                self.probe_atten,
            ],
            offset=1,
        )
        self.channel_layout.addWidget(self.channel_label, 0, 0, 1, 2)
        self.setLayout(self.channel_layout)


class OscilloscopeTriggerWidget(QGroupBox):
    def __init__(self, app, instrument_name):
        super().__init__()

        self.app = app
        self.instrument = instrument_name

        self.trig_header = HCHeader("trigger_label.png")

        self.trig_level = HCDoubleSpinBox(
            self.app,
            self.instrument,
            "TRIGGER_LEVEL",
            label="Trigger Level (V)",
            label_align="right",
        )
        self.trig_level.setSingleStep(0.01)
        self.trig_level.setDecimals(2)
        self.trig_level.setMinimum(-50.0)

        self.trig_chan = HCComboBox(
            self.app,
            self.instrument,
            parameter="TRIGGER_CHANNEL",
            label="Channel",
            label_align="right",
            items=["1", "2", "3", "4"],
        )

        self.trig_coupling = HCComboBox(
            self.app,
            self.instrument,
            parameter="TRIGGER_COUPLING",
            label="Coupling",
            label_align="right",
            items=["AC", "DC"],
        )

        self.trig_edge = HCComboBox(
            self.app,
            self.instrument,
            parameter="TRIGGER_EDGE",
            label="Edge",
            label_align="right",
            items=["BOTH", "NEG", "POS", "ALT"],
        )

        self.trig_single = HCPushButton(
            self.app, self.instrument, "SINGLE_TRIGGER", label="Trigger"
        )
        self.trig_run = HCPushButton(self.app, self.instrument, "RUN", label="Run")
        self.trig_stop = HCPushButton(self.app, self.instrument, "STOP", label="Stop")

        # Add widgets to grid layout
        self.trig_grid = HCGridLayout(
            [self.trig_level, self.trig_chan, self.trig_coupling, self.trig_edge],
            offset=1,
        )
        self.trig_grid.addWidget(self.trig_header, 0, 0, 1, 2, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_single, 5, 0, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_run, 5, 1, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_stop, 6, 1, QtCore.Qt.AlignTop)
        self.setLayout(self.trig_grid)


class OscilloscopeHorizontalWidget(QGroupBox):
    def __init__(self, app, instrument_name):
        super().__init__()

        self.app = app
        self.instrument = instrument_name

        self.horiz_header = HCHeader("horizontal_label.png")

        self.timebase = HCDoubleSpinComboBox(
            self.app,
            self.instrument,
            "TIMEBASE",
            "Time/Div",
            units={"s": 1, "ms": 1e-3, "us": 1e-6, "ns": 1e-9},
            label_align="right",
        )
        self.timebase.spin.setSingleStep(1)
        self.timebase.spin.setDecimals(3)
        self.timebase.spin.setMaximum(1e9)
        self.timebase.combo.setCurrentText("ms")

        self.time_offset = HCDoubleSpinComboBox(
            self.app,
            self.instrument,
            "TIME_OFFSET",
            "Offset",
            units={"s": 1, "ms": 1e-3, "us": 1e-6, "ns": 1e-9},
            label_align="right",
        )
        self.time_offset.spin.setSingleStep(1)
        self.time_offset.spin.setDecimals(3)
        self.time_offset.spin.setMaximum(1e9)
        self.time_offset.combo.setCurrentText("ms")

        self.num_points = HCDoubleSpinBox(
            self.app,
            self.instrument,
            "NUM_POINTS",
            label="Number of Points",
            label_align="right",
        )
        self.num_points.setSingleStep(1)
        self.num_points.setDecimals(0)
        self.num_points.setMaximum(4e6)

        # ******* DEFINE LAYOUT
        self.horiz_layout = HCGridLayout(
            [self.timebase, self.time_offset, self.num_points],
            offset=1,
        )
        self.horiz_layout.addWidget(self.horiz_header, 0, 0, 1, 3, QtCore.Qt.AlignTop)
        self.setLayout(self.horiz_layout)


class OscilloscopeDisplayWidget(QGroupBox):
    """Creates a widget that displays a plot that can automatically refresh
    from oscilloscope data.

    Has three display refresh modes: Timer, Manual, and Single Trigger. Timer mode
    automatically refreshes every few seconds (specified in refresh rate text edit).
    Single Trigger mode refreshes every time a single trigger is sent to the
    oscilloscope (to make this work, the OscilloscopeDisplayWidget instance must
    be passed to the OscilloscopeTriggerWidget instance it should be connected to).
    Manual mode never refreshes automatically, it depends on the refresh button
    to update. The refresh button will immediately refresh the display, regardless
    of display mode.

    Parameters
    ----------
    instrument
        hc.base.instrument instance to connect display to.
    display_name
        Oscilloscope Display Widget name
    channels : list
        channels to display (starting with 0)
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        channels,
        display_name: str = "Oscilloscope Display",
    ):

        super().__init__(display_name)

        self.app = app
        self.instrument = instrument_name
        self.channels = channels

        # ************** DEFINE UI *********************#
        self.display = pg.PlotWidget()
        self.display.show()

        self.p1 = self.display.plotItem
        self.p1.showGrid(x=True, y=True)
        self.p1.setMenuEnabled(enableMenu=True)

        # set up second axis
        if self.channels:
            self.p2 = pg.ViewBox()
            self.p1.showAxis("right")
            self.p1.scene().addItem(self.p2)
            self.p1.getAxis("right").linkToView(self.p2)
            self.p2.setXLink(self.p1)
            right_label_items = [f"channel {i}" for i in self.channels]
            left_label_items = [
                f"channel {i}"
                for i in range(max(self.channels) + 1)
                if i not in self.channels
            ]
            right_label = ", ".join(right_label_items)
            left_label = ", ".join(left_label_items)
            self.p1.getAxis("right").setLabel(right_label, **{"font-size": "20pt"})
            self.p1.getAxis("left").setLabel(left_label, **{"font-size": "20pt"})

        else:
            self.p2 = self.p1

        channel_colors = {
            0: (255, 255, 13),
            1: (31, 255, 9),
            2: (0, 0, 254),
            3: (252, 0, 8),
        }

        self.lineCH = []
        self.CH = []
        self.CH_data = []
        for i, ch in enumerate(self.channels):
            self.lineCH.append(
                pg.mkPen(color=channel_colors[i], style=QtCore.Qt.SolidLine)
            )
            self.CH.append(pg.PlotCurveItem(pen=self.lineCH[i], symbol=None))
            self.CH_data.append(([], []))

        for i, curve in enumerate(self.CH):
            if i in self.channels:
                self.p2.addItem(curve)
            else:
                self.p1.addItem(curve)

        if self.channels:
            self.updateViews()
            self.p1.vb.sigResized.connect(self.updateViews)

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.display, 0, 0, 1, 20)
        self.setLayout(self.master_layout)

        for ch in self.channels:
            self.app.add_hook(
                self.instrument,
                f"CH{ch}_WAVEFORM",
                "post_read_hooks",
                self.make_update_waveform_func(ch),
            )

    def updateViews(self):
        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
        self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)

    def make_update_waveform_func(self, channel):
        return lambda x: self.update_waveform(channel, x)

    def update_waveform(self, channel, trace_string):
        if trace_string is None:
            logger.warning(
                f"Scope {self.instrument}: no trace data available for channel {channel}"
            )
            return
        t, wave = json.loads(trace_string)

        self.CH[channel - 1].setData(t, wave)
        self.CH_data[channel - 1] = (t, wave)

        self.updateViews()
