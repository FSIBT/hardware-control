import logging
import pyqtgraph as pg
import json

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator
from PyQt5.QtWidgets import (
    QGroupBox,
    QComboBox,
    QLabel,
    QGridLayout,
    QWidget,
    QLineEdit,
    QHBoxLayout,
)

from ..widgets import (
    load_icon,
    HCLineEdit,
    HCComboBox,
    HCDoubleSpinBox,
    HCPushButton,
    HCOnOffButton,
    HCSpinBox,
    HCHeader,
    HCDoubleSpinComboBox,
)

logger = logging.getLogger(__name__)


class Oscilloscope(QGroupBox):
    def __init__(
        self,
        app,
        instrument_name: str,
        widget_name: str = "Oscilloscope",
        display_channels=None,
    ):

        super().__init__(widget_name)

        self.app = app
        self.instrument = instrument_name
        self.channels = 4
        self.display_channels = display_channels

        self.disp = OscilloscopeDisplayWidget(
            self.app,
            self.instrument,
            display_channels=self.display_channels,
        )
        self.horiz = OscilloscopeHorizontalWidget(self.app, self.instrument)
        self.trig = OscilloscopeTriggerWidget(self.app, self.instrument, self.disp)

        widget_col = 0
        self.channel_widgets = []
        self.channel_box = QGroupBox()
        self.channel_box_layout = QGridLayout()
        for i in range(self.channels):
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
            f"channel{self.channel+1}_{self.colors[self.channel]}.png"
        )
        self.channel_label.setFont(QFont("Arial", 20))
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
            self.app, self.instrument, f"CH{self.channel}_ON-OFF"
        )

        self.BW_but = HCPushButton(
            self.app, self.instrument, f"CH{self.channel}_BW_LIM", label="BW Limit"
        )
        self.BW_but.setIcon(QIcon(load_icon("BWlim.png")))
        self.BW_but.setCheckable(True)

        self.Inv_but = HCPushButton(
            self.app, self.instrument, f"CH{self.channel}_INVERT", label="Invert"
        )
        self.Inv_but.setIcon(QIcon(load_icon("invert.png")))
        self.Inv_but.setCheckable(True)

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

        self.channel_layout = QGridLayout()
        self.channel_layout.addWidget(self.channel_label, 0, 0, 1, 2)
        self.channel_layout.addWidget(self.volts_div.label, 1, 0)
        self.channel_layout.addWidget(self.volts_div, 1, 1)
        self.channel_layout.addWidget(self.volts_offset.label, 2, 0)
        self.channel_layout.addWidget(self.volts_offset, 2, 1)
        self.channel_layout.addWidget(self.label.label, 3, 0)
        self.channel_layout.addWidget(self.label, 3, 1)
        self.channel_layout.addWidget(self.on_off_but, 4, 1)
        self.channel_layout.addWidget(self.BW_but, 5, 1)
        self.channel_layout.addWidget(self.Inv_but, 5, 2)
        self.channel_layout.addWidget(self.coupling.label, 6, 0)
        self.channel_layout.addWidget(self.coupling, 6, 1)
        self.channel_layout.addWidget(self.impedance.label, 7, 0)
        self.channel_layout.addWidget(self.impedance, 7, 1)
        self.channel_layout.addWidget(self.probe_atten.label, 8, 0)
        self.channel_layout.addWidget(self.probe_atten, 8, 1)
        self.setLayout(self.channel_layout)


class OscilloscopeTriggerWidget(QGroupBox):
    def __init__(self, app, instrument_name, display_widget=None):
        super().__init__()

        self.app = app
        self.instrument = instrument_name
        self.display_widget = display_widget

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
            lookuptable={"1": "0", "2": "1", "3": "2", "4": "3"},
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
        if self.display_widget != None:
            self.trig_single.clicked.connect(self.display_widget.query_waveforms)
        self.trig_run = HCPushButton(self.app, self.instrument, "RUN", label="Run")
        self.trig_stop = HCPushButton(self.app, self.instrument, "STOP", label="Stop")

        # Add widgets to grid layout
        self.trig_grid = QGridLayout()
        self.trig_grid.addWidget(self.trig_header, 0, 0, 1, 2, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_level.label, 1, 0, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_level, 1, 1, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_chan.label, 2, 0, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_chan, 2, 1, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_coupling.label, 3, 0, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_coupling, 3, 1, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_edge.label, 4, 0, QtCore.Qt.AlignTop)
        self.trig_grid.addWidget(self.trig_edge, 4, 1, QtCore.Qt.AlignTop)
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
            units={"s": 1, "ms": 1e3, "us": 1e6, "ns": 1e9},
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
            units={"s": 1, "ms": 1e3, "us": 1e6, "ns": 1e9},
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
        self.horiz_layout = QGridLayout()
        self.horiz_layout.addWidget(self.horiz_header, 0, 0, 1, 3, QtCore.Qt.AlignTop)
        self.horiz_layout.addWidget(self.timebase.label, 1, 0, QtCore.Qt.AlignTop)
        self.horiz_layout.addWidget(self.timebase.spin, 1, 1, QtCore.Qt.AlignTop)
        self.horiz_layout.addWidget(self.timebase.combo, 1, 2, QtCore.Qt.AlignTop)
        self.horiz_layout.addWidget(self.time_offset.label, 2, 0, QtCore.Qt.AlignTop)
        self.horiz_layout.addWidget(self.time_offset.spin, 2, 1, QtCore.Qt.AlignTop)
        self.horiz_layout.addWidget(self.time_offset.combo, 2, 2, QtCore.Qt.AlignTop)
        self.horiz_layout.addWidget(self.num_points.label, 3, 0, QtCore.Qt.AlignTop)
        self.horiz_layout.addWidget(self.num_points, 3, 1, QtCore.Qt.AlignTop)
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
    display_channels : list or None
        channels to display (starting with CH0)
    show_controls : bool
        Allows user to show or hide display refresh controls
    refresh : float
        Refresh period in seconds
    """

    def __init__(
        self,
        app,
        instrument_name: str = "",
        display_name: str = "Oscilloscope Display",
        display_channels=None,
    ):

        super().__init__(display_name)

        self.app = app
        self.instrument = instrument_name
        self.display_channels = display_channels

        # ************** DEFINE UI *********************#
        self.display = pg.PlotWidget()
        self.display.show()

        self.p1 = self.display.plotItem
        self.p1.showGrid(x=True, y=True)
        self.p1.setMenuEnabled(enableMenu=True)

        # set up second axis
        if self.display_channels:
            self.p2 = pg.ViewBox()
            self.p1.showAxis("right")
            self.p1.scene().addItem(self.p2)
            self.p1.getAxis("right").linkToView(self.p2)
            self.p2.setXLink(self.p1)
            right_label_items = [f"channel {i}" for i in self.display_channels]
            left_label_items = [
                f"channel {i+1}" for i in range(4) if i not in self.display_channels
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

        self.lineCH0 = pg.mkPen(color=channel_colors[0], style=QtCore.Qt.SolidLine)
        self.lineCH1 = pg.mkPen(color=channel_colors[1], style=QtCore.Qt.SolidLine)
        self.lineCH2 = pg.mkPen(color=channel_colors[2], style=QtCore.Qt.SolidLine)
        self.lineCH3 = pg.mkPen(color=channel_colors[3], style=QtCore.Qt.SolidLine)
        self.CH0 = pg.PlotCurveItem(pen=self.lineCH0, symbol=None)
        self.CH1 = pg.PlotCurveItem(pen=self.lineCH1, symbol=None)
        self.CH2 = pg.PlotCurveItem(pen=self.lineCH2, symbol=None)
        self.CH3 = pg.PlotCurveItem(pen=self.lineCH3, symbol=None)

        for i, ch in enumerate([self.CH0, self.CH1, self.CH2, self.CH3]):
            if self.display_channels and i + 1 in self.display_channels:
                self.p2.addItem(ch)
            else:
                self.p1.addItem(ch)

        if self.display_channels:
            self.updateViews()
            self.p1.vb.sigResized.connect(self.updateViews)

        self.CH0_data = ([], [])
        self.CH1_data = ([], [])
        self.CH2_data = ([], [])
        self.CH3_data = ([], [])

        # Method of updating display plot data
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.timeout.connect(self.query_waveforms)
        # Default refresh period is set to 5 seconds
        self.update_timer.start(1000 * 5)

        self.refresh_mode_label = QLabel("Refresh Mode: ")
        self.refresh_mode_drop = QComboBox()
        self.refresh_mode_drop.addItems(["Timer", "Single Trig"])
        self.refresh_mode_drop.currentIndexChanged.connect(
            lambda: self.set_refresh_mode(self.refresh_mode_drop.currentText())
        )
        self.refresh_mode_drop.setCurrentText("Single Trig")

        self.refresh_rate_label = QLabel("Refresh Period (s): ")
        self.refresh_rate_edit = QLineEdit()
        self.refresh_rate_edit.setValidator(QDoubleValidator())
        self.refresh_rate_edit.editingFinished.connect(
            lambda: self.refresh_period(float(self.refresh_rate_edit.text()))
        )
        # Default refresh period is set to 5 seconds
        self.refresh_rate_edit.setText(str(5))

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.display, 0, 0, 1, 20)
        self.master_layout.addWidget(self.refresh_mode_label, 1, 0)
        self.master_layout.addWidget(self.refresh_mode_drop, 1, 1)
        self.master_layout.addWidget(self.refresh_rate_label, 1, 2)
        self.master_layout.addWidget(self.refresh_rate_edit, 1, 3, 1, 1)
        self.setLayout(self.master_layout)

    def updateViews(self):
        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
        self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)

    # Set refresh rate (in ms)
    def refresh_period(self, period: float):
        self.update_timer.setInterval(period * 1e3)

    def set_refresh_mode(self, mode: str):
        if mode == "Timer":
            if not self.update_timer.isActive():
                self.update_timer.start()
        elif mode == "Single Trig":
            if self.update_timer.isActive():
                self.update_timer.stop()

    def query_waveforms(self):
        for channel in self.display_channels:
            if self.app.call_instrument_command(self.instrument, f"CH{channel}_ON-OFF"):
                self.app.update_instrument_parameter(
                    self.instrument, f"CH{channel}_WAVEFORM"
                )
                trace_string = self.app.get_instrument_parameter(
                    self.instrument, f"CH{channel}_WAVEFORM"
                )
                t, wave = json.loads(trace_string)

                if channel == 0:
                    self.CH0.setData(t, wave)
                    self.CH0_data = (t, wave)
                elif channel == 1:
                    self.CH1.setData(t, wave)
                    self.CH1_data = (t, wave)
                elif channel == 2:
                    self.CH2.setData(t, wave)
                    self.CH2_data = (t, wave)
                elif channel == 3:
                    self.CH3.setData(t, wave)
                    self.CH3_data = (t, wave)
