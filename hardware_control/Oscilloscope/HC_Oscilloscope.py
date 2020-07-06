#
# This defines the OscilloscopeControl and OscilloscopeComm classes. By passing
# an instance of a SCPI command wrapper class to an OscilloscpeControl objcet,
# you can easily create GUIs for oscilloscopes.
#

import pkg_resources

from hardware_control.utility import regex_compare
from hardware_control.base import (
    HC_Instrument,
    HC_Comm,
    setButtonState,
    returnChannelNumber,
)
import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QWidget,
    QFormLayout,
    QGridLayout,
    QComboBox,
    QDoubleSpinBox,
)
import logging

logger = logging.getLogger(__name__)


class HC_Oscilloscope(HC_Instrument):
    """This is a 4-channel oscilloscope control progam.

    It defines a UI for a 4-ch scope and has the sockets and signals
    to interface with a OscilloscopeComm instance, which facilitates
    communication with the instrument. The Osc.Comm object requires an
    object (originally passed to the control object) which
    fascilitates communication with the scope. An example of such a
    program is the Key4000XSCPI class for Keysight 4000X series
    oscilloscopes. These classes mostly just wrap SCPI commands so
    this UI+Communication code knows how to interface with any
    specific scope model.

    All instrument parameters are saved in a 'settings'
    dictionary. When a function such as set_timebase() is called, it
    updates the settings object and sends it to the communicaiton
    object instance. The communication object finds the change and
    sends the correct SCPI commands to the instrument to impliment the
    change.

    """

    def __init__(
        self, backend, window, name: str = "Oscilloscope Control", lock_until_sync=False
    ):

        super().__init__(window, name, backend, lock_until_sync)

        self.settings = {}

        # backend.sigReturnWaves.connect(self.backend_return_waveform)
        backend.dummy = self.window.app.dummy
        self.address = backend.connection_addr

        if backend.connection_addr in self.window.app.comms:
            self.comm = self.window.app.comms[backend.connection_addr]
            self.comm.addWidget(self)
        else:
            self.window.app.comms[backend.connection_addr] = HC_Comm(
                backend, self, lock_until_sync=lock_until_sync
            )
            self.comm = self.window.app.comms[backend.connection_addr]

        self.filename = ""

        # # Initialize settings to correct values
        # if initialize_with == "DEFAULT":
        #     self.save_on_close = False
        #     # Can't save without filename
        self.settings = self.default_state()
        self.values = self.default_state()
        # else:
        #     self.load_state(initialize_with)
        #     self.filename = initialize_with

        # Create GUI
        self.disp = OscilloscopeDisplayWidget(self, True)

        self.horiz = OscilloscopeHorizontalWidget(self)

        self.meas = OscilloscopeMeasurementWidget(self)

        self.top_panel = QGridLayout()
        self.trig = OscilloscopeTriggerWidget(self)
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

    def backend_return_listdata(self, descr: str, data1: list, data2: list):

        if regex_compare("CH.+_WVFM", descr):
            c = returnChannelNumber(descr)
            if not c:
                c = 1
            self.disp.update_display(int(c), data1, data2)

    # def get_header(self):
    #     return "CH1 Voltage Range[V]"
    #
    # def get_value_keys(self):
    #     return ["CH1_volts_div"]

    def default_state(self):
        """Create a default settings object if can't get settings from a file"""
        dflt = {}

        dflt["timebase"] = "1e-3"

        dflt["time_offset"] = "0"

        dflt["CH1_volts_div"] = "1"
        dflt["CH2_volts_div"] = "1"
        dflt["CH3_volts_div"] = "1"
        dflt["CH4_volts_div"] = "1"

        dflt["CH1_volts_div"] = "1"
        dflt["CH2_volts_div"] = "1"
        dflt["CH3_volts_div"] = "1"
        dflt["CH4_volts_div"] = "1"

        dflt["CH1_volts_div"] = "1"
        dflt["CH2_volts_div"] = "1"
        dflt["CH3_volts_div"] = "1"
        dflt["CH4_volts_div"] = "1"

        dflt["CH1_offset"] = "0"
        dflt["CH2_offset"] = "0"
        dflt["CH3_offset"] = "0"
        dflt["CH4_offset"] = "0"

        dflt["CH1_BW_lim"] = "False"
        dflt["CH2_BW_lim"] = "False"
        dflt["CH3_BW_lim"] = "False"
        dflt["CH4_BW_lim"] = "False"

        dflt["CH1_active"] = "True"
        dflt["CH2_active"] = "False"
        dflt["CH3_active"] = "False"
        dflt["CH4_active"] = "False"

        dflt["CH1_impedance"] = "1e6"
        dflt["CH2_impedance"] = "1e6"
        dflt["CH3_impedance"] = "1e6"
        dflt["CH4_impedance"] = "1e6"

        dflt["CH1_label"] = "Channel 1"
        dflt["CH2_label"] = "Channel 2"
        dflt["CH3_label"] = "Channel 3"
        dflt["CH4_label"] = "Channel 4"

        dflt["labels_enabled"] = "False"

        dflt["CH1_invert"] = "False"
        dflt["CH2_invert"] = "False"
        dflt["CH3_invert"] = "False"
        dflt["CH4_invert"] = "False"

        dflt["CH1_probe_atten"] = "10"
        dflt["CH2_probe_atten"] = "10"
        dflt["CH3_probe_atten"] = "10"
        dflt["CH4_probe_atten"] = "10"

        dflt["CH1_coupling"] = "DC"
        dflt["CH2_coupling"] = "DC"
        dflt["CH3_coupling"] = "DC"
        dflt["CH4_coupling"] = "DC"

        dflt["trigger_level"] = "1"

        dflt["trigger_coupling"] = "DC"

        dflt["trigger_edge"] = "POS"

        dflt["trigger_channel"] = "1"

        dflt["meas_slot1"] = ""
        dflt["meas_slot2"] = ""
        dflt["meas_slot3"] = ""
        dflt["meas_slot4"] = ""
        dflt["meas_slot5"] = ""

        return dflt

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

    def __init__(self, channel: int, control):
        super().__init__()

        self.channel = channel
        self.control = control

        # ************** DEFINE UI *********************#

        self.channel_label = QLabel()
        if channel == 1:
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "icons/channel1_yellow.png"
                    )
                )
            )
        elif channel == 2:
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "icons/channel2_green.png"
                    )
                )
            )
        elif channel == 3:
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "icons/channel3_blue.png"
                    )
                )
            )
        elif channel == 4:
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "icons/channel4_red.png"
                    )
                )
            )
        else:
            self.channel_label.setText(f"Channel {channel}")

        # ****** DEFINE TEXT BOXES
        self.v_div_edit = QDoubleSpinBox()
        self.v_div_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_volts_div", self.v_div_edit.text()
            )
        )
        try:
            self.v_div_edit.setValue(float(control.settings[f"CH{channel}_volts_div"]))
        except:
            self.v_div_edit.setValue(0)
        self.v_div_edit.setDecimals(2)
        # self.v_div_edit.setRange()
        self.v_div_edit.setSingleStep(0.05)

        self.offset_edit = QDoubleSpinBox()
        self.offset_edit.editingFinished.connect(
            lambda: control.update_setting(
                f"CH{channel}_offset", self.offset_edit.text()
            )
        )
        try:
            self.offset_edit.setValue(float(control.settings[f"CH{channel}_offset"]))
        except:
            self.offset_edit.setValue(0)
        self.offset_edit.setDecimals(2)
        # self.offset_edit.setRange()
        self.offset_edit.setSingleStep(0.05)

        self.label_edit = QLineEdit()
        self.label_edit.editingFinished.connect(
            lambda: control.update_setting(f"CH{channel}_label", self.label_edit.text())
        )
        self.label_edit.setText(control.settings[f"CH{channel}_label"])

        self.form = QFormLayout()
        self.form.addRow("Volts/Div (V):", self.v_div_edit)
        self.form.addRow("Vert. Offset (V):", self.offset_edit)
        self.form.addRow("Label:", self.label_edit)

        self.lower_grid = QGridLayout()

        # ******* DEFINE BUTTONS + DROPDOWNS
        self.active_but = QPushButton()
        self.active_but.setText("Channel On/Off")
        self.active_but.setCheckable(True)
        self.active_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_active", str(self.active_but.isChecked())
            )
        )
        setButtonState(self.active_but, control.settings[f"CH{channel}_active"])

        self.BW_but = QPushButton()
        self.BW_but.setText("BW Limit")
        self.BW_but.setIcon(
            QIcon(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "icons/BWlim.png"
                    )
                )
            )
        )
        self.BW_but.setCheckable(True)
        self.BW_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_BW_lim", str(self.BW_but.isChecked())
            )
        )
        setButtonState(self.BW_but, control.settings[f"CH{channel}_BW_lim"])

        self.Inv_but = QPushButton()
        self.Inv_but.setText("Invert")
        self.Inv_but.setCheckable(True)
        self.Inv_but.setIcon(
            QIcon(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "icons/invert.png"
                    )
                )
            )
        )
        self.Inv_but.clicked.connect(
            lambda: control.update_setting(
                f"CH{channel}_invert", str(self.Inv_but.isChecked())
            )
        )
        setButtonState(self.Inv_but, control.settings[f"CH{channel}_invert"])

        self.coupling_label = QLabel("Coupling:")
        self.coupling_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.coupling_drop = QComboBox()
        self.coupling_drop.addItems(["DC", "AC"])
        self.coupling_drop.currentIndexChanged.connect(
            lambda: control.update_setting(
                f"CH{channel}_coupling", self.coupling_drop.currentText()
            )
        )
        self.coupling_drop.setCurrentText(control.settings[f"CH{channel}_coupling"])

        self.impedance_label = QLabel("Impedance:")
        self.impedance_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.impedance_drop = QComboBox()
        self.impedance_drop.addItems(["1e6", "50"])
        self.impedance_drop.currentIndexChanged.connect(
            lambda: control.update_setting(
                f"CH{channel}_impedance", self.impedance_drop.currentText()
            )
        )
        self.impedance_drop.setCurrentText(
            str(control.settings[f"CH{channel}_impedance"])
        )

        self.probe_label = QLabel("Probe attenutation: ")
        self.probe_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.probe_drop = QComboBox()
        self.probe_drop.addItems([".001", ".01", ".1", "1", "10", "100", "1000"])
        self.probe_drop.currentIndexChanged.connect(
            lambda: control.update_setting(
                f"CH{channel}_probe_atten", self.probe_drop.currentText()
            )
        )
        self.probe_drop.setCurrentText(
            str(control.settings[f"CH{channel}_probe_atten"])
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
                float(self.control.settings[f"CH{self.channel}_volts_div"])
            )
        except:
            self.v_div_edit.setValue(0)

        try:
            self.offset_edit.setValue(
                float(self.control.settings[f"CH{self.channel}_offset"])
            )
        except:
            self.offset_edit.setValue(0)

        self.label_edit.setText(self.control.settings[f"CH{self.channel}_label"])
        setButtonState(
            self.active_but, self.control.settings[f"CH{self.channel}_active"]
        )
        setButtonState(self.BW_but, self.control.settings[f"CH{self.channel}_BW_lim"])
        setButtonState(self.Inv_but, self.control.settings[f"CH{self.channel}_invert"])
        self.coupling_drop.setCurrentText(
            self.control.settings[f"CH{self.channel}_coupling"]
        )
        self.impedance_drop.setCurrentText(
            str(self.control.settings[f"CH{self.channel}_impedance"])
        )
        self.probe_drop.setCurrentText(
            str(self.control.settings[f"CH{self.channel}_probe_atten"])
        )


class OscilloscopeTriggerWidget(QWidget):
    def __init__(self, control):
        super().__init__()

        self.control = control

        # ************** DEFINE UI *********************#
        self.trigger_label_box = QHBoxLayout()
        self.trigger_label = QLabel()
        self.trigger_label.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "icons/trigger_label.png"
                )
            )
        )
        self.trigger_label_box.addWidget(self.trigger_label)

        # ****** DEFINE TEXT BOXES
        self.level_edit = QDoubleSpinBox()
        self.level_edit.editingFinished.connect(
            lambda: control.update_setting(
                "trigger_level", str(self.level_edit.value())
            )
        )
        self.level_edit.setValue(float(control.settings["trigger_level"]))
        self.level_edit.setSingleStep(0.01)
        self.level_edit.setDecimals(2)
        self.form = QFormLayout()
        self.form.addRow("Trigger Level (V):", self.level_edit)

        self.lower_grid = QGridLayout()

        # ******* DEFINE BUTTONS + DROPDOWNS
        self.trig_chan_label = QLabel("Channel: ")
        self.trig_chan_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.trig_chan_drop = QComboBox()
        self.trig_chan_drop.addItems(["None", "1", "2", "3", "4"])
        self.trig_chan_drop.currentIndexChanged.connect(
            lambda: control.update_setting(
                "trigger_channel", self.trig_chan_drop.currentText()
            )
        )
        self.trig_chan_drop.setCurrentText(str(control.settings["trigger_channel"]))

        self.coupling_label = QLabel("Coupling:")
        self.coupling_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.coupling_drop = QComboBox()
        self.coupling_drop.addItems(["DC", "AC", "LFReject", "HFReject"])
        self.coupling_drop.currentIndexChanged.connect(
            lambda: control.update_setting(
                "trigger_coupling", self.coupling_drop.currentText()
            )
        )
        self.coupling_drop.setCurrentText(control.settings["trigger_coupling"])

        self.edge_label = QLabel("Edge:")
        self.edge_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.edge_drop = QComboBox()
        self.edge_drop.addItems(["POS", "NEG", "EITH", "ALT"])
        self.edge_drop.currentIndexChanged.connect(
            lambda: control.update_setting("trigger_edge", self.edge_drop.currentText())
        )
        self.edge_drop.setCurrentText(str(control.settings["trigger_edge"]))

        self.single_but = QPushButton()
        self.single_but.setText("Single")
        self.single_but.clicked.connect(lambda: control.comm.command("SINGLE_TRIGGER"))

        self.run_but = QPushButton()
        self.run_but.setText("Run")
        self.run_but.clicked.connect(lambda: control.comm.command("RUN"))

        self.stop_but = QPushButton()
        self.stop_but.setText("Stop")
        self.stop_but.clicked.connect(lambda: control.comm.command("STOP"))

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

    def settings_to_UI(self):

        self.level_edit.setValue(float(self.control.settings["trigger_level"]))
        self.trig_chan_drop.setCurrentText(
            str(self.control.settings["trigger_channel"])
        )
        self.coupling_drop.setCurrentText(self.control.settings["trigger_coupling"])
        self.edge_drop.setCurrentText(str(self.control.settings["trigger_edge"]))


class OscilloscopeHorizontalWidget(QWidget):
    def __init__(self, control):
        super().__init__()

        self.control = control

        # Define timescale options
        self.units = {"s": 1, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}

        # ************** DEFINE UI *********************#
        self.horizontal_label_box = QHBoxLayout()
        self.horizontal_label = QLabel()
        self.horizontal_label.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "icons/horizontal_label.png"
                )
            )
        )
        self.horizontal_label_box.addWidget(self.horizontal_label)

        # ****** DEFINE TEXT BOXES
        # ToDo: change Units to a more useful dimension than s - eg ms or mu
        #
        self.timebase_edit = QDoubleSpinBox()
        try:
            self.timebase_edit.setValue(float(control.settings["timebase"]))
        except:
            self.timebase_edit.setValue(1e-3)
        self.timebase_edit.setSingleStep(1)
        self.timebase_edit.setDecimals(3)
        self.timebase_edit.setMaximum(1e6)
        self.timebase_edit.editingFinished.connect(
            lambda: control.update_setting(
                "timebase",
                str(
                    float(self.timebase_edit.text())
                    * self.units[self.timebase_edit_units.currentText()]
                ),
            )
        )
        self.timebase_edit.setValue(float(control.settings["timebase"]) * 1e3)

        self.timebase_edit_units = QComboBox()
        self.timebase_edit_units.addItems(self.units.keys())
        self.timebase_edit_units.setCurrentText("ms")
        self.timebase_edit_units.currentIndexChanged.connect(
            lambda: control.update_setting(
                "timebase",
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
        self.time_offset_edit.setValue(float(control.settings["time_offset"]) * 1e3)
        self.time_offset_edit.editingFinished.connect(
            lambda: control.update_setting(
                "time_offset",
                str(
                    float(self.time_offset_edit.text())
                    * self.units[self.time_offset_edit_units.currentText()]
                ),
            )
        )

        self.time_offset_edit_units = QComboBox()
        # self.time_offset_edit_units.currentIndexChanged.connect(lambda: control.update_setting("time_offset", str(float(self.time_offset_edit.text()) * self.units[self.timebase_edit_units.currentText()])))
        self.time_offset_edit_units.addItems(self.units.keys())
        self.time_offset_edit_units.setCurrentText("ms")

        self.time_offset_edit_layout = QGridLayout()
        self.time_offset_edit_layout.addWidget(self.time_offset_edit, 0, 0)
        self.time_offset_edit_layout.addWidget(self.time_offset_edit_units, 0, 1)

        self.form = QFormLayout()
        self.form.addRow("Time/Div (s):", self.timebase_edit_layout)
        self.form.addRow("Offset (s): ", self.time_offset_edit_layout)

        # ******* DEFINE OVERALL LAYOUT
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.horizontal_label_box, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.setLayout(self.master_layout)

    def settings_to_UI(self):

        self.timebase_edit_units.setCurrentText("ms")
        self.time_offset_edit_units.setCurrentText("ms")

        try:
            self.timebase_edit.setValue(1e3 * float(self.control.settings["timebase"]))
        except:
            self.timebase_edit.setValue(1e-3)

        self.time_offset_edit.setValue(
            float(self.control.settings["time_offset"]) * 1e3
        )


class OscilloscopeDisplayWidget(QGroupBox):
    def __init__(self, control, show_controls: bool = False, refresh: float = 0.2):

        super().__init__("Oscilloscope Display")

        self.control = control

        self.single_trig_mode = False

        # ************** DEFINE UI *********************#
        #
        self.display = pg.PlotWidget()
        self.pi = self.display.getPlotItem()
        self.pi.showGrid(x=True, y=True)
        self.pi.setMenuEnabled(enableMenu=True)

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.display, 0, 0, 1, 5)

        self.lineCH1 = pg.mkPen(color=(255, 255, 13), style=QtCore.Qt.SolidLine)
        self.lineCH2 = pg.mkPen(color=(31, 255, 9), style=QtCore.Qt.SolidLine)
        self.lineCH3 = pg.mkPen(color=(0, 0, 254), style=QtCore.Qt.SolidLine)
        self.lineCH4 = pg.mkPen(color=(252, 0, 8), style=QtCore.Qt.SolidLine)

        self.CH1 = self.display.plot(pen=self.lineCH1, symbol=None)
        self.CH2 = self.display.plot(pen=self.lineCH2, symbol=None)
        self.CH3 = self.display.plot(pen=self.lineCH3, symbol=None)
        self.CH4 = self.display.plot(pen=self.lineCH4, symbol=None)

        if show_controls:
            self.refresh_rate_label = QLabel("Refresh Rate (Hz): ")

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

            self.refresh_mode_drop = QComboBox()
            # self.refresh_mode_drop.addItems(["Timer", "Single Trig", "Manual"]) #TODO: Impliment single trigger
            self.refresh_mode_drop.addItems(
                ["Timer", "Manual"]
            )  # TODO: Impliment single trigger
            self.refresh_mode_drop.currentIndexChanged.connect(
                lambda: self.set_refresh_mode(self.refresh_mode_drop.currentText())
            )
            self.refresh_mode_drop.setCurrentText("Timer")

            self.master_layout.addWidget(self.refresh_mode_label, 1, 0)
            self.master_layout.addWidget(self.refresh_mode_drop, 1, 1)
            self.master_layout.addWidget(self.refresh_rate_label, 1, 2)
            self.master_layout.addWidget(self.refresh_rate_edit, 1, 3)
            self.master_layout.addWidget(self.refresh_but, 1, 4)

        self.setLayout(self.master_layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.query_waveforms)
        self.update_timer.start(1000 / refresh)

    # Set refresh rate (in Hz)
    def refresh_rate(self, rate: float):
        self.update_timer.setInterval(1000 / rate)

    # Set refresh rate (in ms)
    def refresh_period(self, period: float):
        self.update_timer.setInterval(period)

    def set_refresh_mode(self, mode: str):
        if mode == "Timer":
            if not self.update_timer.isActive():
                self.update_timer.start()
            single_trig_mode = False
        elif mode == "Single Trig":
            if self.update_timer.isActive():
                self.update_timer.stop()
            self.single_trig_mode = True
        else:
            if self.update_timer.isActive():
                self.update_timer.stop()
            single_trig_mode = False

    def update_display(self, channel: int, t: list, wave: list):
        # def update_display(self, wvfms: dict):

        if channel == 1:
            self.CH1.setData(t, wave)
        elif channel == 2:
            self.CH2.setData(t, wave)
        elif channel == 3:
            self.CH3.setData(t, wave)
        elif channel == 4:
            self.CH4.setData(t, wave)

    def query_waveforms(self):

        for c in range(1, 5):
            if self.control.settings[f"CH{c}_active"] == "True":
                self.control.command_listdata(f"CH{c}_WVFM?")  # Ask for waveform data
            else:
                self.control.command_listdata(
                    f"CH{c}_CLEAR"
                )  # Tell backend to send empty data


class OscilloscopeMeasurementWidget(QWidget):
    def __init__(self, control):

        super().__init__()

        self.master_layout = QGridLayout()

        self.control = control

        # ******************** DEFINE UI ***************************
        self.measurement_label = QLabel()
        self.measurement_label.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "icons/measurement_label.png"
                )
            )
        )

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

        self.control.update_setting(f"meas_slot{self.next_slot}", meas_string)

        # Update next slot
        self.next_slot += 1
        if self.next_slot > 5:
            self.next_slot = 1

    # TODO: Make this delete measurements in internal settings variables
    def clear_measurements(self):
        self.control.command("CLEAR_MEAS")

    def settings_to_UI(self):

        pass
