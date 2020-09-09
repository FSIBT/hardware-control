import logging

import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QDoubleValidator, QIcon
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from ...utility import get_channel_from_command
from ..widgets import setButtonState, load_icon, QOnOffButton
from ..base import Instrument, Comm


logger = logging.getLogger(__name__)


class Oscilloscope(Instrument):
    """This is GUI for a 4-channel oscilloscope.

    This is a very general GUI that allows common controls for the
    different channels, timing, and the trigger setup. It can display
    the measured waveforms.

    .. image:: /images/controls/Oscilloscope.png
      :height: 200


    Parameters
    ----------

    right_axis : list
        list of channels to display on the right axis. `None` only use one axis

    See Also
    --------
    hardware_control.backends.keysight.Keysight_4000X.Keysight_4000X
    hardware_control.backends.picotech.Picotech_6000.Picotech_6000
    hardware_control.backends.rigol.Rigol_DS1000Z.Rigol_DS1000Z

    """

    def __init__(
        self,
        app,
        backend,
        name: str = "Oscilloscope Control",
        lock_until_sync=False,
        right_axis=None,
    ):

        super().__init__(app, name, backend, lock_until_sync)

        self.channels = 4
        self.right_axis = right_axis

        self.settings = self.default_state()
        self.values = self.default_state()

        # Create GUI
        self.disp = OscilloscopeDisplayWidget(self, True, right_axis=self.right_axis)

        self.horiz = OscilloscopeHorizontalWidget(self)

        self.meas = OscilloscopeMeasurementWidget(self)

        self.top_panel = QGridLayout()
        self.trig = OscilloscopeTriggerWidget(self, self.disp)
        self.top_panel.addWidget(self.trig, 0, 0)

        self.ch1 = OscillscopeChannelWidget(1, self)
        self.ch2 = OscillscopeChannelWidget(2, self)
        self.ch3 = OscillscopeChannelWidget(3, self)
        self.ch4 = OscillscopeChannelWidget(4, self)
        self.channel_panel = QGridLayout()
        self.channel_panel.addWidget(self.ch1, 0, 0)
        self.channel_panel.addWidget(self.ch2, 0, 1)
        self.channel_panel.addWidget(self.ch3, 0, 2)
        self.channel_panel.addWidget(self.ch4, 0, 3)

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.disp, 0, 0, 2, 2)
        self.master_layout.addWidget(self.horiz, 0, 2, 1, 1)
        self.master_layout.addWidget(self.meas, 1, 2, 1, 1)
        self.master_layout.addLayout(self.top_panel, 0, 3, 2, 1)
        self.master_layout.addLayout(self.channel_panel, 2, 0, 1, 4)

        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

    def get_last_waveform(self):

        return (
            self.disp.CH1_data,
            self.disp.CH2_data,
            self.disp.CH3_data,
            self.disp.CH4_data,
        )

    def backend_return_listdata(self, descr: str, data1: list, data2: list):

        channel, cmd_X = get_channel_from_command(descr)

        if cmd_X == "CHX_WVFM":
            self.disp.update_display(channel, data1, data2)

    def default_state(self):
        default = {}

        default["TIMEBASE"] = "1e-3"
        default["TIME_OFFSET"] = "0"
        default["NUM_POINTS"] = "1000"
        default["LABELS_ENABLED"] = "False"

        for channel in range(1, self.channels + 1):
            default[f"CH{channel}_VOLTS_DIV"] = "1"
            default[f"CH{channel}_OFFSET"] = "0"
            default[f"CH{channel}_BW_LIM"] = "False"
            default[f"CH{channel}_ACTIVE"] = "True"
            default[f"CH{channel}_IMPEDANCE"] = "1e6"
            default[f"CH{channel}_LABEL"] = f"Channel {channel}"
            default[f"CH{channel}_INVERT"] = "False"
            default[f"CH{channel}_PROBE_ATTEN"] = "1"
            default[f"CH{channel}_COUPLING"] = "DC"

        default["TRIGGER_LEVEL"] = "1"
        default["TRIGGER_COUPLING"] = "DC"
        default["TRIGGER_EDGE"] = "POS"
        default["TRIGGER_CHANNEL"] = "1"

        default["MEAS_SLOT1"] = ""
        default["MEAS_SLOT2"] = ""
        default["MEAS_SLOT3"] = ""
        default["MEAS_SLOT4"] = ""
        default["MEAS_SLOT5"] = ""

        return default

    def settings_to_UI(self):

        # self.disp.settings_to_UI()
        self.horiz.settings_to_UI()
        self.meas.settings_to_UI()
        self.trig.settings_to_UI()

        self.ch1.settings_to_UI()
        self.ch2.settings_to_UI()
        self.ch3.settings_to_UI()
        self.ch4.settings_to_UI()


class OscillscopeChannelWidget(QWidget):
    """Defines a UI for oscilloscope channels"""

    def __init__(self, channel: int, instrument):
        super().__init__()

        self.channel = channel
        self.instrument = instrument

        # ************** DEFINE UI *********************#

        self.channel_label = QLabel()
        if channel == 1:
            self.channel_label.setPixmap(load_icon("channel1_yellow.png"))
        elif channel == 2:
            self.channel_label.setPixmap(load_icon("channel2_green.png"))
        elif channel == 3:
            self.channel_label.setPixmap(load_icon("channel3_blue.png"))
        elif channel == 4:
            self.channel_label.setPixmap(load_icon("channel4_red.png"))
        else:
            self.channel_label.setText(f"Channel {channel}")

        # ****** DEFINE TEXT BOXES
        self.v_div_edit = QDoubleSpinBox()
        self.v_div_edit.editingFinished.connect(
            lambda: instrument.update_setting(
                f"CH{channel}_VOLTS_DIV", self.v_div_edit.text()
            )
        )
        try:
            self.v_div_edit.setValue(
                float(instrument.settings[f"CH{channel}_VOLTS_DIV"])
            )
        except:
            self.v_div_edit.setValue(0)
        self.v_div_edit.setDecimals(2)
        # self.v_div_edit.setRange()
        self.v_div_edit.setSingleStep(0.05)

        self.offset_edit = QDoubleSpinBox()
        self.offset_edit.editingFinished.connect(
            lambda: instrument.update_setting(
                f"CH{channel}_OFFSET", self.offset_edit.text()
            )
        )
        try:
            self.offset_edit.setValue(float(instrument.settings[f"CH{channel}_OFFSET"]))
        except:
            self.offset_edit.setValue(0)
        self.offset_edit.setDecimals(2)
        # self.offset_edit.setRange()
        self.offset_edit.setSingleStep(0.05)

        self.label_edit = QLineEdit()
        self.label_edit.editingFinished.connect(
            lambda: instrument.update_setting(
                f"CH{channel}_LABEL", self.label_edit.text()
            )
        )
        self.label_edit.setText(instrument.settings[f"CH{channel}_LABEL"])

        self.form = QFormLayout()
        self.form.addRow("Volts/Div (V):", self.v_div_edit)
        self.form.addRow("Vert. Offset (V):", self.offset_edit)
        self.form.addRow("Label:", self.label_edit)

        self.lower_grid = QGridLayout()

        # ******* DEFINE BUTTONS + DROPDOWNS
        self.active_but = QOnOffButton(instrument, f"CH{channel}_ACTIVE")

        self.BW_but = QPushButton()
        self.BW_but.setText("BW Limit")
        self.BW_but.setIcon(QIcon(load_icon("BWlim.png")))
        self.BW_but.setCheckable(True)
        self.BW_but.clicked.connect(
            lambda: instrument.update_setting(
                f"CH{channel}_BW_LIM", str(self.BW_but.isChecked())
            )
        )
        setButtonState(self.BW_but, instrument.settings[f"CH{channel}_BW_LIM"])

        self.Inv_but = QPushButton()
        self.Inv_but.setText("Invert")
        self.Inv_but.setCheckable(True)
        self.Inv_but.setIcon(QIcon(load_icon("invert.png")))
        self.Inv_but.clicked.connect(
            lambda: instrument.update_setting(
                f"CH{channel}_INVERT", str(self.Inv_but.isChecked())
            )
        )
        setButtonState(self.Inv_but, instrument.settings[f"CH{channel}_INVERT"])

        self.coupling_label = QLabel("Coupling:")
        self.coupling_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.coupling_drop = QComboBox()
        self.coupling_drop.addItems(["DC", "AC"])
        self.coupling_drop.currentIndexChanged.connect(
            lambda: instrument.update_setting(
                f"CH{channel}_COUPLING", self.coupling_drop.currentText()
            )
        )
        self.coupling_drop.setCurrentText(instrument.settings[f"CH{channel}_COUPLING"])

        self.impedance_label = QLabel("Impedance:")
        self.impedance_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.impedance_drop = QComboBox()
        self.impedance_drop.addItems(["1e6", "50"])
        self.impedance_drop.currentIndexChanged.connect(
            lambda: instrument.update_setting(
                f"CH{channel}_IMPEDANCE", self.impedance_drop.currentText()
            )
        )
        self.impedance_drop.setCurrentText(
            str(instrument.settings[f"CH{channel}_IMPEDANCE"])
        )

        self.probe_label = QLabel("Probe attenutation: ")
        self.probe_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.probe_drop = QComboBox()
        self.probe_drop.addItems([".001", ".01", ".1", "1", "10", "100", "1000"])
        self.probe_drop.currentIndexChanged.connect(
            lambda: instrument.update_setting(
                f"CH{channel}_PROBE_ATTEN", self.probe_drop.currentText()
            )
        )
        self.probe_drop.setCurrentText(
            str(instrument.settings[f"CH{channel}_PROBE_ATTEN"])
        )

        # Add widgets to grid layout
        self.lower_grid.addWidget(self.active_but, 0, 0)
        self.lower_grid.addWidget(self.BW_but, 1, 0)
        self.lower_grid.addWidget(self.Inv_but, 1, 1)
        self.lower_grid.addWidget(self.coupling_label, 2, 0)
        self.lower_grid.addWidget(self.coupling_drop, 2, 1)
        self.lower_grid.addWidget(self.impedance_label, 3, 0)
        self.lower_grid.addWidget(self.impedance_drop, 3, 1)
        self.lower_grid.addWidget(self.probe_label, 4, 0)
        self.lower_grid.addWidget(self.probe_drop, 4, 1)

        # ******* DEFINE OVERALL LAYOUT
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.channel_label, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.master_layout.addLayout(self.lower_grid, 2, 0)
        self.setLayout(self.master_layout)

    def settings_to_UI(self):

        try:
            self.v_div_edit.setValue(
                float(self.instrument.settings[f"CH{self.channel}_VOLTS_DIV"])
            )
        except:
            self.v_div_edit.setValue(0)

        try:
            self.offset_edit.setValue(
                float(self.instrument.settings[f"CH{self.channel}_OFFSET"])
            )
        except:
            self.offset_edit.setValue(0)

        self.label_edit.setText(self.instrument.settings[f"CH{self.channel}_LABEL"])
        setButtonState(
            self.active_but, self.instrument.settings[f"CH{self.channel}_ACTIVE"]
        )
        setButtonState(
            self.BW_but, self.instrument.settings[f"CH{self.channel}_BW_LIM"]
        )
        setButtonState(
            self.Inv_but, self.instrument.settings[f"CH{self.channel}_INVERT"]
        )
        self.coupling_drop.setCurrentText(
            self.instrument.settings[f"CH{self.channel}_COUPLING"]
        )
        self.impedance_drop.setCurrentText(
            str(self.instrument.settings[f"CH{self.channel}_IMPEDANCE"])
        )
        self.probe_drop.setCurrentText(
            str(self.instrument.settings[f"CH{self.channel}_PROBE_ATTEN"])
        )


class OscilloscopeTriggerWidget(QWidget):
    def __init__(self, instrument, display_widget=None):
        """ Initializes the OscilloscopeTriggerWidget

        Parameters
        ----------
        instrument
            hc.Oscilloscope instance to connect widget to
        display_widget
            Optional OscilloscopeDisplayWidget to connect widget with. Every time
            a single trigger is called, this display widget will be told to refresh
            its display if it is in 'single trigger' refresh mode. The refresh will
            occur self.refresh_delay_time_ms milliseconds after the single trigger.
            Default delay time is 1.5 seconds.
        """
        super().__init__()

        self.instrument = instrument
        self.display_widget = display_widget
        self.refresh_delay_time_ms = 1500

        # ************** DEFINE UI *********************#
        self.trigger_label_box = QHBoxLayout()
        self.trigger_label = QLabel()
        self.trigger_label.setPixmap(load_icon("trigger_label.png"))
        self.trigger_label_box.addWidget(self.trigger_label)

        # ****** DEFINE TEXT BOXES
        self.level_edit = QDoubleSpinBox()
        self.level_edit.editingFinished.connect(
            lambda: instrument.update_setting(
                "TRIGGER_LEVEL", str(self.level_edit.value())
            )
        )
        self.level_edit.setValue(float(instrument.settings["TRIGGER_LEVEL"]))
        self.level_edit.setSingleStep(0.01)
        self.level_edit.setDecimals(2)
        self.level_edit.setMinimum(-50.0)
        self.form = QFormLayout()
        self.form.addRow("Trigger Level (V):", self.level_edit)

        self.lower_grid = QGridLayout()

        # ******* DEFINE BUTTONS + DROPDOWNS
        self.trig_chan_label = QLabel("Channel: ")
        self.trig_chan_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.trig_chan_drop = QComboBox()
        self.trig_chan_drop.addItems(["None", "1", "2", "3", "4"])
        self.trig_chan_drop.currentIndexChanged.connect(
            lambda: instrument.update_setting(
                "TRIGGER_CHANNEL", self.trig_chan_drop.currentText()
            )
        )
        self.trig_chan_drop.setCurrentText(str(instrument.settings["TRIGGER_CHANNEL"]))

        self.coupling_label = QLabel("Coupling:")
        self.coupling_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.coupling_drop = QComboBox()
        self.coupling_drop.addItems(["DC", "AC", "LFReject", "HFReject"])
        self.coupling_drop.currentIndexChanged.connect(
            lambda: instrument.update_setting(
                "TRIGGER_COUPLING", self.coupling_drop.currentText()
            )
        )
        self.coupling_drop.setCurrentText(instrument.settings["TRIGGER_COUPLING"])

        self.edge_label = QLabel("Edge:")
        self.edge_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.edge_drop = QComboBox()
        self.edge_drop.addItems(["POS", "NEG", "EITH", "ALT"])
        self.edge_drop.currentIndexChanged.connect(
            lambda: instrument.update_setting(
                "TRIGGER_EDGE", self.edge_drop.currentText()
            )
        )
        self.edge_drop.setCurrentText(str(instrument.settings["TRIGGER_EDGE"]))

        self.single_but = QPushButton()
        self.single_but.setText("Single")
        self.single_but.clicked.connect(self.single_trigger)

        self.run_but = QPushButton()
        self.run_but.setText("Run")
        self.run_but.clicked.connect(lambda: instrument.command("RUN"))

        self.stop_but = QPushButton()
        self.stop_but.setText("Stop")
        self.stop_but.clicked.connect(lambda: instrument.command("STOP"))

        # Add widgets to grid layout
        self.lower_grid.addWidget(self.trig_chan_label, 0, 0)
        self.lower_grid.addWidget(self.trig_chan_drop, 0, 1)
        self.lower_grid.addWidget(self.coupling_label, 1, 0)
        self.lower_grid.addWidget(self.coupling_drop, 1, 1)
        self.lower_grid.addWidget(self.edge_label, 2, 0)
        self.lower_grid.addWidget(self.edge_drop, 2, 1)
        self.lower_grid.addWidget(self.single_but, 3, 0)
        self.lower_grid.addWidget(self.run_but, 3, 1)
        self.lower_grid.addWidget(self.stop_but, 4, 1)

        # ******* DEFINE OVERALL LAYOUT
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.trigger_label_box, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.master_layout.addLayout(self.lower_grid, 2, 0)
        self.setLayout(self.master_layout)

    def single_trigger(self):
        self.instrument.command("SINGLE_TRIGGER")

        QTimer.singleShot(self.refresh_delay_time_ms, self.display_refresh)

    def display_refresh(self):

        # Continue if display widget is present
        if self.display_widget is None:
            return

        # Continue if display widget is in single trigger mode
        if not self.display_widget.single_trig_mode:
            return

        # Refresh display
        self.display_widget.query_waveforms()

    def settings_to_UI(self):

        self.level_edit.setValue(float(self.instrument.settings["TRIGGER_LEVEL"]))
        self.trig_chan_drop.setCurrentText(
            str(self.instrument.settings["TRIGGER_CHANNEL"])
        )
        self.coupling_drop.setCurrentText(self.instrument.settings["TRIGGER_COUPLING"])
        self.edge_drop.setCurrentText(str(self.instrument.settings["TRIGGER_EDGE"]))


class OscilloscopeHorizontalWidget(QWidget):
    def __init__(self, instrument):
        super().__init__()

        self.instrument = instrument

        # Define timescale options
        self.units = {"s": 1, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}

        # ************** DEFINE UI *********************#
        self.horizontal_label_box = QHBoxLayout()
        self.horizontal_label = QLabel()
        self.horizontal_label.setPixmap(load_icon("horizontal_label.png"))
        self.horizontal_label_box.addWidget(self.horizontal_label)

        # ****** DEFINE TEXT BOXES
        self.timebase_edit = QDoubleSpinBox()
        try:
            self.timebase_edit.setValue(float(instrument.settings["TIMEBASE"]))
        except:
            self.timebase_edit.setValue(1e-3)
        self.timebase_edit.setSingleStep(1)
        self.timebase_edit.setDecimals(3)
        self.timebase_edit.setMaximum(1e6)
        self.timebase_edit.editingFinished.connect(
            lambda: instrument.update_setting(
                "TIMEBASE",
                str(
                    float(self.timebase_edit.text())
                    * self.units[self.timebase_edit_units.currentText()]
                ),
            )
        )
        self.timebase_edit.setValue(float(instrument.settings["TIMEBASE"]) * 1e3)

        self.timebase_edit_units = QComboBox()
        self.timebase_edit_units.addItems(self.units.keys())
        self.timebase_edit_units.setCurrentText("ms")
        self.timebase_edit_units.currentIndexChanged.connect(
            lambda: instrument.update_setting(
                "TIMEBASE",
                str(
                    float(self.timebase_edit.text())
                    * self.units[self.timebase_edit_units.currentText()]
                ),
            )
        )

        self.timebase_edit_layout = QGridLayout()
        self.timebase_edit_layout.addWidget(self.timebase_edit, 0, 0)
        self.timebase_edit_layout.addWidget(self.timebase_edit_units, 0, 1)

        self.time_offset_edit = QDoubleSpinBox()
        self.time_offset_edit.setSingleStep(1)
        self.time_offset_edit.setDecimals(3)
        self.time_offset_edit.setMaximum(1e6)
        self.time_offset_edit.setValue(float(instrument.settings["TIME_OFFSET"]) * 1e3)
        self.time_offset_edit.editingFinished.connect(
            lambda: instrument.update_setting(
                "TIME_OFFSET",
                str(
                    float(self.time_offset_edit.text())
                    * self.units[self.time_offset_edit_units.currentText()]
                ),
            )
        )

        self.time_offset_edit_units = QComboBox()
        # self.time_offset_edit_units.currentIndexChanged.connect(lambda: instrument.update_setting("time_offset", str(float(self.time_offset_edit.text()) * self.units[self.timebase_edit_units.currentText()])))
        self.time_offset_edit_units.addItems(self.units.keys())
        self.time_offset_edit_units.setCurrentText("ms")

        self.time_offset_edit_layout = QGridLayout()
        self.time_offset_edit_layout.addWidget(self.time_offset_edit, 0, 0)
        self.time_offset_edit_layout.addWidget(self.time_offset_edit_units, 0, 1)

        self.number_points_edit = QDoubleSpinBox()
        self.number_points_edit.setSingleStep(1)
        self.number_points_edit.setDecimals(0)
        self.number_points_edit.setMaximum(4e6)
        self.number_points_edit.setValue(float(instrument.settings["NUM_POINTS"]))
        self.number_points_edit.editingFinished.connect(
            lambda: instrument.update_setting(
                "NUM_POINTS", str(float(self.number_points_edit.text())),
            )
        )
        self.form = QFormLayout()
        self.form.addRow("Time/Div (s):", self.timebase_edit_layout)
        self.form.addRow("Offset (s): ", self.time_offset_edit_layout)
        self.form.addRow("Number of Points: ", self.number_points_edit)

        # ******* DEFINE OVERALL LAYOUT
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.horizontal_label_box, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.setLayout(self.master_layout)

    def settings_to_UI(self):

        self.timebase_edit_units.setCurrentText("ms")
        self.time_offset_edit_units.setCurrentText("ms")

        try:
            self.timebase_edit.setValue(
                1e3 * float(self.instrument.settings["TIMEBASE"])
            )
        except:
            self.timebase_edit.setValue(1e-3)

        self.time_offset_edit.setValue(
            float(self.instrument.settings["TIME_OFFSET"]) * 1e3
        )


class OscilloscopeDisplayWidget(QGroupBox):
    """ Creates a widget that displays a plot that can automatically refresh
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
        hc.Oscilloscope instance to connect display to.
    show_controls : bool
        Allows user to show or hide display refresh controls
    refresh : float
        Refresh period in seconds
    right_axis : list
        channels to display on right axis

    """

    def __init__(
        self,
        instrument,
        show_controls: bool = True,
        refresh: float = 5,
        right_axis=None,
    ):

        super().__init__("Oscilloscope Display")

        self.instrument = instrument
        self.right_axis = right_axis

        self.single_trig_mode = False

        # ************** DEFINE UI *********************#
        #
        self.display = pg.PlotWidget()
        self.display.show()
        self.p1 = self.display.plotItem
        self.p1.showGrid(x=True, y=True)
        self.p1.setMenuEnabled(enableMenu=True)
        # set up second axis
        if self.right_axis:
            self.p2 = pg.ViewBox()
            self.p1.showAxis("right")
            self.p1.scene().addItem(self.p2)
            self.p1.getAxis("right").linkToView(self.p2)
            self.p2.setXLink(self.p1)
            right_label_items = [f"channel {i}" for i in right_axis]
            left_label_items = [
                f"channel {i}" for i in range(1, 5) if i not in right_axis
            ]
            right_label = ", ".join(right_label_items)
            left_label = ", ".join(left_label_items)
            self.p1.getAxis("right").setLabel(right_label, **{"font-size": "20pt"})
            self.p1.getAxis("left").setLabel(left_label, **{"font-size": "20pt"})

        else:
            self.p2 = self.p1

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.display, 0, 0, 1, 5)

        channel_colors = {
            1: (255, 255, 13),
            2: (31, 255, 9),
            3: (0, 0, 254),
            4: (252, 0, 8),
        }

        self.lineCH1 = pg.mkPen(color=channel_colors[1], style=QtCore.Qt.SolidLine)
        self.lineCH2 = pg.mkPen(color=channel_colors[2], style=QtCore.Qt.SolidLine)
        self.lineCH3 = pg.mkPen(color=channel_colors[3], style=QtCore.Qt.SolidLine)
        self.lineCH4 = pg.mkPen(color=channel_colors[4], style=QtCore.Qt.SolidLine)
        self.CH1 = pg.PlotCurveItem(pen=self.lineCH1, symbol=None)
        self.CH2 = pg.PlotCurveItem(pen=self.lineCH2, symbol=None)
        self.CH3 = pg.PlotCurveItem(pen=self.lineCH3, symbol=None)
        self.CH4 = pg.PlotCurveItem(pen=self.lineCH4, symbol=None)

        for i, ch in enumerate([self.CH1, self.CH2, self.CH3, self.CH4]):
            if self.right_axis and i + 1 in self.right_axis:
                self.p2.addItem(ch)
            else:
                self.p1.addItem(ch)

        if self.right_axis:
            self.updateViews()
            self.p1.vb.sigResized.connect(self.updateViews)

        self.CH1_data = ([], [])
        self.CH2_data = ([], [])
        self.CH3_data = ([], [])
        self.CH4_data = ([], [])

        if show_controls:
            self.refresh_rate_label = QLabel("Refresh Period (s): ")

            self.refresh_rate_edit = QLineEdit()
            self.refresh_rate_edit.setValidator(QDoubleValidator())
            self.refresh_rate_edit.editingFinished.connect(
                lambda: self.refresh_rate(float(self.refresh_rate_edit.text()))
            )
            self.refresh_rate_edit.setText(str(refresh))

            self.refresh_but = QPushButton()
            self.refresh_but.setText("Refresh")
            self.refresh_but.clicked.connect(self.query_waveforms)

            self.refresh_mode_label = QLabel("Refresh Mode: ")

            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self.query_waveforms)
            self.update_timer.start(1000 * refresh)

            self.refresh_mode_drop = QComboBox()
            self.refresh_mode_drop.addItems(["Timer", "Manual", "Single Trig"])
            self.refresh_mode_drop.currentIndexChanged.connect(
                lambda: self.set_refresh_mode(self.refresh_mode_drop.currentText())
            )
            self.refresh_mode_drop.setCurrentText("Single Trig")

            self.master_layout.addWidget(self.refresh_mode_label, 1, 0)
            self.master_layout.addWidget(self.refresh_mode_drop, 1, 1)
            self.master_layout.addWidget(self.refresh_rate_label, 1, 2)
            self.master_layout.addWidget(self.refresh_rate_edit, 1, 3)
            self.master_layout.addWidget(self.refresh_but, 1, 4)

        self.setLayout(self.master_layout)

    def updateViews(self):
        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
        self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)

    # Set refresh rate (in Hz)
    def refresh_rate(self, rate: float):
        self.update_timer.setInterval(rate * 1000)

    # Set refresh rate (in ms)
    def refresh_period(self, period: float):
        self.update_timer.setInterval(period)

    def set_refresh_mode(self, mode: str):
        if mode == "Timer":
            if not self.update_timer.isActive():
                self.update_timer.start()
            self.single_trig_mode = False
        elif mode == "Single Trig":
            if self.update_timer.isActive():
                self.update_timer.stop()
            self.single_trig_mode = True
        else:
            if self.update_timer.isActive():
                self.update_timer.stop()
            self.single_trig_mode = False

    def update_display(self, channel: int, t: list, wave: list):
        # def update_display(self, wvfms: dict):

        if channel == 1:
            self.CH1.setData(t, wave)
            self.CH1_data = (t, wave)
        elif channel == 2:
            self.CH2.setData(t, wave)
            self.CH2_data = (t, wave)
        elif channel == 3:
            self.CH3.setData(t, wave)
            self.CH3_data = (t, wave)
        elif channel == 4:
            self.CH4.setData(t, wave)
            self.CH4_data = (t, wave)

    def query_waveforms(self):

        for c in range(1, 5):
            if self.instrument.settings[f"CH{c}_ACTIVE"] == "True":
                self.instrument.command_listdata(
                    f"CH{c}_WVFM?"
                )  # Ask for waveform data
            else:
                self.instrument.command_listdata(
                    f"CH{c}_CLEAR"
                )  # Tell backend to send empty data


class OscilloscopeMeasurementWidget(QWidget):
    def __init__(self, instrument):

        super().__init__()

        self.master_layout = QGridLayout()

        self.instrument = instrument

        # ******************** DEFINE UI ***************************
        self.measurement_label = QLabel()
        self.measurement_label.setPixmap(load_icon("measurement_label.png"))

        self.channel_label = QLabel("Source: ")

        self.channel_drop = QComboBox()
        self.channel_drop.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])
        # self.channel_drop.currentIndexChanged.connect(lambda: self.set_refresh_mode(self.refresh_mode_drop.currentText()))
        self.channel_drop.setCurrentText("CH 1")

        self.meas_label = QLabel("Measurement: ")

        self.meas_drop = QComboBox()
        self.meas_drop.addItems(
            ["Vpp", "Vrms", "Vmax", "Vmin", "Vavg", "Freq", "Period", "Phase 1->2"]
        )
        self.meas_drop.setCurrentText("Vpp")

        self.add_but = QPushButton()
        self.add_but.setText("Add Measurement")
        self.add_but.clicked.connect(self.add_measurement)

        self.clear_but = QPushButton()
        self.clear_but.setText("Clear")
        self.clear_but.clicked.connect(self.clear_measurements)

        self.master_layout.addWidget(self.measurement_label, 0, 0, 1, 2)
        self.master_layout.addWidget(self.channel_label, 1, 0, 1, 1)
        self.master_layout.addWidget(self.channel_drop, 2, 0, 1, 1)
        self.master_layout.addWidget(self.meas_label, 1, 1, 1, 1)
        self.master_layout.addWidget(self.meas_drop, 2, 1, 1, 1)
        self.master_layout.addWidget(self.clear_but, 3, 0, 1, 1)
        self.master_layout.addWidget(self.add_but, 3, 1, 1, 1)

        self.setLayout(self.master_layout)

        self.next_slot = 1

    def add_measurement(self):

        # Get parameter string from dropdown. Convert values to correct format for
        # backend to understand.

        add_channel = True
        meas_string = self.meas_drop.currentText().upper()
        if meas_string == "PERIOD":
            meas_string = "PER"
        elif meas_string == "Phase 1->2":
            meas_string = "RPH"
            add_channel = False

        if add_channel:
            meas_string = meas_string + ",CHAN" + self.channel_drop.currentText()[3]

        self.instrument.update_setting(f"MEAS_SLOT{self.next_slot}", meas_string)

        # Update next slot
        self.next_slot += 1
        if self.next_slot > 5:
            self.next_slot = 1

    # TODO: Make this delete measurements in internal settings variables
    def clear_measurements(self):
        self.instrument.command("CLEAR_MEAS")

    def settings_to_UI(self):

        pass
