#
# This defines the OscilloscopeControl and OscilloscopeComm classes. By passing
# an instance of a SCPI command wrapper class to an OscilloscpeControl objcet,
# you can easily create GUIs for oscilloscopes.
#

import copy
import json
import time  # Get rid of this guy!

import pkg_resources
import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QWidget,
    QFormLayout,
    QGridLayout,
    QComboBox,
)
import logging

logger = logging.getLogger(__name__)
from hardware_control.base import HC_Instrument


#
# This is a 4-channel oscilloscope control progam. It defines a UI for a 4-ch
# scope and has the sockets and signals to interface with a OscilloscopeComm
# instance, which facilitates communication with the instrument. The Osc.Comm
# object requires an object (originally passed to the control object) which
# fascilitates communication with the scope. An example of such a program is
# the Key4000XSCPI class for Keysight 4000X series oscilloscopes. These classes
# mostly just wrap SCPI commands so this UI+Communication code knows how to
# interface with any specific scope model.
#
# All instrument parameters are saved in a 'settings' dictionary. When a function
# such as set_timebase() is called, it updates the settings object and sends it to
# the communicaiton object instance. The communication object finds the change
# and sends the correct SCPI commands to the instrument to impliment the change.
#
class HC_DAQ(HC_Instrument):

    # Define sigs (to call functions in communication object)
    state_mosi_sig = pyqtSignal(dict)
    action_sig = pyqtSignal(str)
    write_sig = pyqtSignal(str)
    query_sig = pyqtSignal(str)

    def __init__(
        self,
        scpi_instr,
        window,
        name: str = "DAQ Control",
        initialize_with: str = "INSTRUMENT",
    ):

        super().__init__(window, name)

        self.settings = {}
        self.address = scpi_instr.connection_addr

        scpi_instr.dummy = self.window.app.dummy

        if scpi_instr in self.window.app.comms:
            self.comm = self.window.app.comms[scpi_instr]
            self.comm.addWidget(self)
        else:
            self.window.app.comms[scpi_instr] = HC_Comm(scpi_instr, self)
            self.comm = self.window.app.comms[scpi_instr]

        self.filename = ""

        # Connect signals and sigs
        self.state_mosi_sig.connect(self.comm.get_state)
        self.action_sig.connect(self.comm.get_command)
        self.comm.state_miso_sig.connect(self.get_state)
        self.comm.values_miso_sig.connect(self.values_received)
        #
        self.write_sig.connect(self.comm.write)
        self.query_sig.connect(self.comm.query)

        # Move comm object to comm thread
        self.comm_thread = QThread()
        self.comm.moveToThread(self.comm_thread)
        self.comm_thread.start()

        # # Initialize settings to correct values
        # if initialize_with == "INSTRUMENT":
        #     self.save_on_close = False
        #     # Can't save without filename
        #     self.settings = self.initialize_gui_instrument()
        # elif initialize_with == "DEFAULT":
        #     self.save_on_close = False
        #     # Can't save without filename
        self.settings = self.default_state()
        # else:
        #     self.load_state(initialize_with)
        #     self.filename = initialize_with

        # Create GUI
        #
        self.disp = OscilloscopeDisplayWidget(self, True)
        #
        self.horiz = OscilloscopeHorizontalWidget(self)
        #
        self.top_panel = QGridLayout()
        trig = OscilloscopeTriggerWidget(self)
        self.top_panel.addWidget(trig, 0, 0)
        #
        ch1 = OscillscopeChannelWidget(1, self, "yellow")
        ch2 = OscillscopeChannelWidget(2, self, "green")
        ch3 = OscillscopeChannelWidget(3, self, "blue")
        ch4 = OscillscopeChannelWidget(4, self, "red")
        self.channel_panel = QGridLayout()
        self.channel_panel.addWidget(ch1, 0, 0)
        self.channel_panel.addWidget(ch2, 0, 1)
        self.channel_panel.addWidget(ch3, 0, 2)
        self.channel_panel.addWidget(ch4, 0, 3)
        #

        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.disp, 0, 0, 1, 2)
        self.master_layout.addWidget(self.horiz, 0, 2, 1, 1)
        self.master_layout.addLayout(self.top_panel, 0, 3, 1, 1)
        self.master_layout.addLayout(self.channel_panel, 1, 0, 1, 4)

        #
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

    def initialize_gui_instrument():
        print("\n\nOh no! I haven't implimented this yet!!\n\n")
        pass

    def load_state(self, filename: str):

        # Get default state - this identifies all required fields
        dflt = self.default_state()

        # Read a settings from file
        try:
            with open(filename) as file:
                self.settings = json.load(file)
                print(f"settings for {self.comm.instr.ID} read from file '{filename}'")
        except:
            print(f"ERROR: Failed to read file '{filename}'. Using defualt case.")
            self.settings = self.default_state()

        # Ensure all fields in default_state are present in the loaded state
        for key in dflt:
            if not (key in self.settings):
                self.settings[key] = dflt[key]

    def save_state(self, filename: str):
        try:
            with open(filename, "w") as file:
                json.dump(self.settings, file)
                print(f"settings for {self.comm.instr.ID} saved to file '{filename}'")
        except Exception as e:
            print(f"ERROR: Failed to write file '{filename}'. settings not saved.")
            print(f"\t{e}")

    #
    # Close connection
    #
    def close(self, filename: str = ""):

        # Save settings if asked
        if self.save_on_close:
            self.save_state(self.filename)

        # Tell scope to close
        self.comm.close()

    #
    # Sends the settings to the communication object
    #
    def send_state(self):
        """ Use signals/slots to send the settings dictionary to the communication
        thread. """
        self.state_mosi_sig.emit(self.settings)
        pass

    #
    # Queries the settings from the communication object
    #
    def get_state(self, new_state: dict):
        """ Gets the settings from the oscilloscope. """
        self.settings = new_state

    #
    # Called when a waveform is read - updates the display
    #
    def values_received(self, values: dict):
        # Do plotting here
        self.disp.update_display(values)
        pass

    def set_time_offset(self, value: float):
        self.settings["time_offset"] = value
        self.send_state()

    def set_timebase(self, value: float):
        self.settings["timebase"] = value
        self.send_state()

    def set_volts_div(self, channel: int, value: float):
        self.settings["volts_div"][f"CH{channel}"] = value
        self.send_state()

    def set_offset(self, channel: int, value: float):
        self.settings["offset"][f"CH{channel}"] = value
        self.send_state()

    def set_channel_label(self, channel: int, value: str):
        self.settings["channel_label"][f"CH{channel}"] = value
        self.send_state()

    def set_channel_coupling(self, channel: int, value: str):
        if value != "AC" and value != "DC":
            value = "DC"
        self.settings["channel_coupling"][f"CH{channel}"] = value
        self.send_state()

    def set_channel_active(self, channel: int, value: bool):
        try:
            print(f"chan{channel} <- {value}")
            self.settings["channel_active"][f"CH{channel}"] = value
            self.send_state()
        except:
            for key in self.settings:
                print(f'\t\t["{key}"]')

    def set_BW_lim(self, channel: int, value: bool):
        self.settings["BW_lim"][f"CH{channel}"] = value
        self.send_state()

    def set_channel_invert(self, channel: int, value: bool):
        self.settings["channel_invert"][f"CH{channel}"] = value
        self.send_state()

    def set_channel_impedance(self, channel: int, value: float):
        self.settings["channel_impedance"][f"CH{channel}"] = value
        self.send_state()

    def set_probe_atten(self, channel: int, value: float):
        self.settings["probe_atten"][f"CH{channel}"] = value
        self.send_state()

    def single_trigger(self):
        self.action_sig.emit("SINGLE")
        if self.disp.single_trig_mode:
            self.query_waveforms()

    def normal_trigger(self):
        self.action_sig.emit("RUN")

    def halt(self):
        self.action_sig.emit("HALT")

    def set_trigger_level(self, value: float):
        self.settings["trigger_level"] = value
        self.send_state()

    def set_trigger_channel(self, value: int):
        self.settings["trigger_channel"] = value
        self.send_state()

    def set_trigger_edge(self, value: str):
        self.settings["trigger_edge"] = value
        self.send_state()

    def set_trigger_coupling(self, value: str):
        self.settings["trigger_coupling"] = value
        self.send_state()

    def query_waveforms(self):
        start_time = time.time()
        self.action_sig.emit("WAVEFORMS")

    #        print(f"'Control' spent {time.time()-start_time} seconds querying waveforms.");

    #
    # Manually send a SCPI command through the communication object to the INSTR
    #
    def write(self, command: str):
        """ Manually send SCPI commands to the oscilloscope. """
        write_sig.emit(command)

    #
    # Manually query a SCPI command through the communication obeect to the INSTR
    #
    def query(self, command: str):
        """ Manually send/receive commands to/from the oscilloscope. """
        return query_sig.emit(command)

    #
    # Create a default settings object if can't get settings from a file
    #
    def default_state(self):

        dflt = {}

        dflt["timebase"] = 1e-3
        dflt["time_offset"] = 0
        dflt["volts_div"] = {"CH1": 1, "CH2": 1, "CH3": 1, "CH4": 1}
        dflt["offset"] = {"CH1": 0, "CH2": 0, "CH3": 0, "CH4": 0}
        dflt["BW_lim"] = {"CH1": False, "CH2": False, "CH3": False, "CH4": False}
        dflt["channel_active"] = {"CH1": True, "CH2": False, "CH3": False, "CH4": False}
        dflt["channel_impedance"] = {"CH1": 1e6, "CH2": 1e6, "CH3": 1e6, "CH4": 1e6}
        dflt["channel_label"] = {
            "CH1": "Channel 1",
            "CH2": "Channel 2",
            "CH3": "Channel 3",
            "CH4": "Channel 4",
        }
        dflt["labels_enabled"] = False
        dflt["channel_invert"] = {
            "CH1": False,
            "CH2": False,
            "CH3": False,
            "CH4": False,
        }
        dflt["probe_atten"] = {"CH1": 10, "CH2": 10, "CH3": 10, "CH4": 10}
        dflt["channel_coupling"] = {"CH1": "DC", "CH2": "DC", "CH3": "DC", "CH4": "DC"}
        dflt["trigger_level"] = 1
        dflt["trigger_coupling"] = "DC"
        dflt["trigger_edge"] = "POS"
        dflt["trigger_channel"] = 1

        return dflt


#
# Defines a UI for oscilloscope channels
#
class OscillscopeChannelWidget(QWidget):
    def __init__(self, channel: int, control, color):
        super().__init__()

        self.channel = channel

        # ************** DEFINE UI *********************#

        self.channel_label = QLabel()
        if color == "yellow":
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/icons/channel1_yellow.png"
                    )
                )
            )
        elif color == "green":
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/icons/channel2_green.png"
                    )
                )
            )
        elif color == "blue":
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/icons/channel3_blue.png"
                    )
                )
            )
        elif color == "red":
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/icons/channel4_red.png"
                    )
                )
            )
        else:
            self.channel_label.setText(f"Channel {channel}")

        # ****** DEFINE TEXT BOXES
        #
        self.v_div_edit = QLineEdit()
        self.v_div_edit.setValidator(QDoubleValidator())
        self.v_div_edit.editingFinished.connect(
            lambda: control.set_volts_div(channel, float(self.v_div_edit.text()))
        )
        self.v_div_edit.setText(str(control.settings["volts_div"][f"CH{channel}"]))
        #
        self.offset_edit = QLineEdit()
        self.offset_edit.setValidator(QDoubleValidator())
        self.offset_edit.editingFinished.connect(
            lambda: control.set_offset(self.channel, float(self.offset_edit.text()))
        )
        self.offset_edit.setText(str(control.settings["offset"][f"CH{channel}"]))
        #
        self.label_edit = QLineEdit()
        self.label_edit.editingFinished.connect(
            lambda: control.set_channel_label(self.channel, self.label_edit.text())
        )
        self.label_edit.setText(control.settings["channel_label"][f"CH{channel}"])
        #
        self.form = QFormLayout()
        self.form.addRow("Volts/Div (V):", self.v_div_edit)
        self.form.addRow("Vert. Offset (V):", self.offset_edit)
        self.form.addRow("Label:", self.label_edit)

        self.lower_grid = QGridLayout()

        # ******* DEFINE BUTTONS + DROPDOWNS
        #
        self.active_but = QPushButton()
        self.active_but.setText("Channel On/Off")
        self.active_but.setCheckable(True)
        self.active_but.clicked.connect(
            lambda: control.set_channel_active(
                self.channel, self.active_but.isChecked()
            )
        )
        setButtonState(
            self.active_but, control.settings["channel_active"][f"CH{self.channel}"]
        )
        #
        self.BW_but = QPushButton()
        self.BW_but.setText("BW Limit")
        self.BW_but.setIcon(
            QIcon(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/icons/BWlim.png"
                    )
                )
            )
        )
        self.BW_but.setCheckable(True)
        self.BW_but.clicked.connect(
            lambda: control.set_BW_lim(self.channel, self.BW_but.isChecked())
        )
        setButtonState(self.BW_but, control.settings["BW_lim"][f"CH{self.channel}"])
        #
        self.Inv_but = QPushButton()
        self.Inv_but.setText("Invert")
        self.Inv_but.setCheckable(True)
        self.Inv_but.setIcon(
            QIcon(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "Oscilloscope/icons/invert.png"
                    )
                )
            )
        )
        self.Inv_but.clicked.connect(
            lambda: control.set_channel_invert(self.channel, self.Inv_but.isChecked())
        )
        setButtonState(
            self.Inv_but, control.settings["channel_invert"][f"CH{self.channel}"]
        )
        #
        #
        self.coupling_label = QLabel("Coupling:")
        self.coupling_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.coupling_drop = QComboBox()
        self.coupling_drop.addItems(["DC", "AC"])
        self.coupling_drop.currentIndexChanged.connect(
            lambda: control.set_channel_coupling(
                self.channel, self.coupling_drop.currentText()
            )
        )
        self.coupling_drop.setCurrentText(
            control.settings["channel_coupling"][f"CH{self.channel}"]
        )
        #
        self.impedance_label = QLabel("Impedance:")
        self.impedance_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.impedance_drop = QComboBox()
        self.impedance_drop.addItems(["1e6", "50"])
        self.impedance_drop.currentIndexChanged.connect(
            lambda: control.set_channel_impedance(
                self.channel, float(self.impedance_drop.currentText())
            )
        )
        self.impedance_drop.setCurrentText(
            str(control.settings["channel_impedance"][f"CH{self.channel}"])
        )
        #
        self.probe_label = QLabel("Probe attenutation: ")
        self.probe_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.probe_drop = QComboBox()
        self.probe_drop.addItems([".001", ".01", ".1", "1", "10", "100", "1000"])
        self.probe_drop.currentIndexChanged.connect(
            lambda: control.set_probe_atten(
                self.channel, float(self.probe_drop.currentText())
            )
        )
        self.probe_drop.setCurrentText(
            str(control.settings["probe_atten"][f"CH{self.channel}"])
        )
        #
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
        #
        # self.lower_grid.addWidget(self.active_but, 0, 0);
        # self.lower_grid.addWidget(self.BW_but, 1, 0);
        # self.lower_grid.addWidget(self.Inv_but, 2, 0);
        # self.lower_grid.addWidget(self.coupling_label, 0, 1);
        # self.lower_grid.addWidget(self.coupling_drop, 1, 1);
        # self.lower_grid.addWidget(self.impedance_label, 2, 1);
        # self.lower_grid.addWidget(self.impedance_drop, 3, 1);
        # self.lower_grid.addWidget(self.probe_label, 4, 1);
        # self.lower_grid.addWidget(self.probe_drop, 5, 1);

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.channel_label, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.master_layout.addLayout(self.lower_grid, 2, 0)
        self.setLayout(self.master_layout)


#
# Defines a UI for oscilloscope channels
#
class OscilloscopeTriggerWidget(QWidget):
    def __init__(self, control):
        super().__init__()

        # ************** DEFINE UI *********************#

        self.trigger_label_box = QHBoxLayout()
        self.trigger_label = QLabel()
        self.trigger_label.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "Oscilloscope/icons/trigger_label.png"
                )
            )
        )
        self.trigger_label_box.addWidget(self.trigger_label)

        # ****** DEFINE TEXT BOXES
        #
        self.level_edit = QLineEdit()
        self.level_edit.setValidator(QDoubleValidator())
        self.level_edit.editingFinished.connect(
            lambda: control.set_trigger_level(float(self.level_edit.text()))
        )
        self.level_edit.setText(str(control.settings["trigger_level"]))
        #
        self.form = QFormLayout()
        self.form.addRow("Trigger Level (V):", self.level_edit)

        self.lower_grid = QGridLayout()

        # ******* DEFINE BUTTONS + DROPDOWNS
        #
        self.trig_chan_label = QLabel("Channel: ")
        self.trig_chan_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_chan_drop = QComboBox()
        self.trig_chan_drop.addItems(["1", "2", "3", "4"])
        self.trig_chan_drop.currentIndexChanged.connect(
            lambda: control.set_trigger_channel(int(self.trig_chan_drop.currentText()))
        )
        self.trig_chan_drop.setCurrentText(str(control.settings["probe_atten"]))
        #
        self.coupling_label = QLabel("Coupling:")
        self.coupling_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.coupling_drop = QComboBox()
        self.coupling_drop.addItems(["DC", "AC"])
        self.coupling_drop.currentIndexChanged.connect(
            lambda: control.set_trigger_coupling(self.coupling_drop.currentText())
        )
        self.coupling_drop.setCurrentText(control.settings["trigger_coupling"])
        #
        self.edge_label = QLabel("Edge:")
        self.edge_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.edge_drop = QComboBox()
        self.edge_drop.addItems(["POS", "NEG", "EITH", "ALT"])
        self.edge_drop.currentIndexChanged.connect(
            lambda: control.set_trigger_edge(self.edge_drop.currentText())
        )
        self.edge_drop.setCurrentText(str(control.settings["trigger_edge"]))
        #
        self.single_but = QPushButton()
        self.single_but.setText("Single")
        self.single_but.clicked.connect(lambda: control.single_trigger())
        #
        self.run_but = QPushButton()
        self.run_but.setText("Run")
        self.run_but.clicked.connect(lambda: control.normal_trigger())
        #
        self.stop_but = QPushButton()
        self.stop_but.setText("Stop")
        self.stop_but.clicked.connect(lambda: control.halt())

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
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.trigger_label_box, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.master_layout.addLayout(self.lower_grid, 2, 0)
        self.setLayout(self.master_layout)


#
# Defines a UI for oscilloscope channels
#
class OscilloscopeHorizontalWidget(QWidget):
    def __init__(self, control):
        super().__init__()

        # ************** DEFINE UI *********************#

        self.horizontal_label_box = QHBoxLayout()
        self.horizontal_label = QLabel()
        self.horizontal_label.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "Oscilloscope/icons/horizontal_label.png"
                )
            )
        )
        self.horizontal_label_box.addWidget(self.horizontal_label)

        # ****** DEFINE TEXT BOXES
        #
        self.timebase_edit = QLineEdit()
        self.timebase_edit.setValidator(QDoubleValidator())
        self.timebase_edit.editingFinished.connect(
            lambda: control.set_timebase(float(self.timebase_edit.text()))
        )
        self.timebase_edit.setText(str(control.settings["timebase"]))
        #
        self.time_offset_edit = QLineEdit()
        self.time_offset_edit.setValidator(QDoubleValidator())
        self.time_offset_edit.editingFinished.connect(
            lambda: control.set_time_offset(float(self.time_offset_edit.text()))
        )
        self.time_offset_edit.setText(str(control.settings["time_offset"]))
        #
        self.form = QFormLayout()
        self.form.addRow("Time/Div (s):", self.timebase_edit)
        self.form.addRow("Offset (s): ", self.time_offset_edit)

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.horizontal_label_box, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0)
        self.setLayout(self.master_layout)


class OscilloscopeDisplayWidget(QWidget):
    def __init__(self, control, show_controls: bool = False, refresh: float = 0.2):

        super().__init__()

        self.control = control

        self.single_trig_mode = False

        # ************** DEFINE UI *********************#
        #
        self.display = pg.PlotWidget()
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.display, 0, 0, 1, 5)
        #
        self.lineCH1 = pg.mkPen(color=(100, 100, 255), style=QtCore.Qt.DashLine)
        self.lineCH2 = pg.mkPen(color=(255, 100, 100), style=QtCore.Qt.DashLine)
        self.lineCH3 = pg.mkPen(color=(100, 255, 100), style=QtCore.Qt.DashLine)
        self.lineCH4 = pg.mkPen(color=(200, 200, 200), style=QtCore.Qt.DashLine)
        #
        self.CH1 = self.display.plot(pen=self.lineCH1, symbol=None)
        self.CH2 = self.display.plot(pen=self.lineCH2, symbol=None)
        self.CH3 = self.display.plot(pen=self.lineCH3, symbol=None)
        self.CH4 = self.display.plot(pen=self.lineCH4, symbol=None)
        #
        if show_controls:
            self.refresh_rate_label = QLabel("Refresh Rate (Hz): ")
            #
            self.refresh_rate_edit = QLineEdit()
            self.refresh_rate_edit.setValidator(QDoubleValidator())
            self.refresh_rate_edit.editingFinished.connect(
                lambda: self.refresh_rate(float(self.refresh_rate_edit.text()))
            )
            self.refresh_rate_edit.setText(str(refresh))
            #
            self.refresh_but = QPushButton()
            self.refresh_but.setText("Refresh")
            self.refresh_but.clicked.connect(control.query_waveforms)
            #
            self.refresh_mode_label = QLabel("Refresh Mode: ")
            #
            self.refresh_mode_drop = QComboBox()
            self.refresh_mode_drop.addItems(["Timer", "Single Trig", "Manual"])
            self.refresh_mode_drop.currentIndexChanged.connect(
                lambda: self.set_refresh_mode(self.refresh_mode_drop.currentText())
            )
            self.refresh_mode_drop.setCurrentText("Timer")
            #
            #
            self.master_layout.addWidget(self.refresh_mode_label, 1, 0)
            self.master_layout.addWidget(self.refresh_mode_drop, 1, 1)
            self.master_layout.addWidget(self.refresh_rate_label, 1, 2)
            self.master_layout.addWidget(self.refresh_rate_edit, 1, 3)
            self.master_layout.addWidget(self.refresh_but, 1, 4)

        self.setLayout(self.master_layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(control.query_waveforms)
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
                print("Stop!")
            single_trig_mode = False

    def update_display(self, wvfms: dict):
        start_time = time.time()
        if "CH1" in wvfms:
            self.CH1.setData(wvfms["CH1"][1], wvfms["CH1"][0])
        else:
            pass

        if "CH2" in wvfms:
            self.CH2.setData(wvfms["CH2"][1], wvfms["CH2"][0])
        else:
            pass

        if "CH3" in wvfms:
            self.CH3.setData(wvfms["CH3"][1], wvfms["CH3"][0])
        else:
            pass

        if "CH4" in wvfms:
            self.CH4.setData(wvfms["CH4"][1], wvfms["CH4"][0])
        else:
            pass


#        print(f"'Widget' spent {time.time()-start_time} seconds updating waveforms.");


#
# This is a 4-channel oscilloscope communication progam. It fascilitates
# communication with the scope. For more information on how this works, read the
# comment for the OscilloscopeControl class.
#
class DAQComm(QObject):

    state_miso_sig = pyqtSignal(dict)
    values_miso_sig = pyqtSignal(dict)

    def __init__(self, scpi_instr):

        super().__init__()

        self.settings = {}
        # Read this guy in from a function?
        self.instr_state = {}
        # Contains settings of instrument so it knows which gs to update

        self.instr = scpi_instr

        self.instr.try_connect()
        if not self.instr.online:
            print(f"{self.instr.ID}: Failed to connect")
        else:
            print(f"{self.instr.ID}: Connected")

        # Connect timer
        self.connect_timer = QTimer(self)
        self.connect_timer.timeout.connect(self.instr.try_connect)
        self.connect_timer.start(1000)
        # 1s period

    #
    # Close connection
    #
    def close(self):
        self.instr.close()

    @pyqtSlot(str)
    def get_command(self, command: str):

        if command == "SINGLE":
            self.instr.single_trigger()
        elif command == "RUN":
            self.instr.norm_trigger()
        elif command == "HALT":
            self.instr.halt()
        elif command == "WAVEFORMS":
            self.send_waveform()

    #
    # Receives a settings object from the control object.
    #
    @pyqtSlot(dict)
    def get_state(self, new_state: dict):

        self.settings = new_state
        for key in self.settings:
            if (not (key in self.instr_state)) or (
                self.settings[key] != self.instr_state[key]
            ):
                self.update_parameter(key, self.settings[key])

        self.instr_state = copy.deepcopy(self.settings)

    def update_parameter(self, key: str, value):

        if key == "timebase":
            self.instr.set_timebase(value)
        elif key == "time_offset":
            self.instr.set_time_offset(value)
        elif key == "volts_div":
            self.instr.set_volts_div(1, value["CH1"])
            self.instr.set_volts_div(2, value["CH2"])
            self.instr.set_volts_div(3, value["CH3"])
            self.instr.set_volts_div(4, value["CH4"])
        elif key == "offset":
            self.instr.set_offset(1, value["CH1"])
            self.instr.set_offset(2, value["CH2"])
            self.instr.set_offset(3, value["CH3"])
            self.instr.set_offset(4, value["CH4"])
        elif key == "channel_label":
            self.instr.set_channel_label(1, value["CH1"])
            self.instr.set_channel_label(2, value["CH2"])
            self.instr.set_channel_label(3, value["CH3"])
            self.instr.set_channel_label(4, value["CH4"])
        elif key == "channel_active":
            self.instr.set_channel_active(1, value["CH1"])
            self.instr.set_channel_active(2, value["CH2"])
            self.instr.set_channel_active(3, value["CH3"])
            self.instr.set_channel_active(4, value["CH4"])
        elif key == "BW_lim":
            self.instr.set_BW_lim(1, value["CH1"])
            self.instr.set_BW_lim(2, value["CH2"])
            self.instr.set_BW_lim(3, value["CH3"])
            self.instr.set_BW_lim(4, value["CH4"])
        elif key == "channel_invert":
            self.instr.set_channel_invert(1, value["CH1"])
            self.instr.set_channel_invert(2, value["CH2"])
            self.instr.set_channel_invert(3, value["CH3"])
            self.instr.set_channel_invert(4, value["CH4"])
        elif key == "channel_impedance":
            self.instr.set_channel_impedance(1, value["CH1"])
            self.instr.set_channel_impedance(2, value["CH2"])
            self.instr.set_channel_impedance(3, value["CH3"])
            self.instr.set_channel_impedance(4, value["CH4"])
        elif key == "channel_coupling":
            self.instr.set_channel_coupling(1, value["CH1"])
            self.instr.set_channel_coupling(2, value["CH2"])
            self.instr.set_channel_coupling(3, value["CH3"])
            self.instr.set_channel_coupling(4, value["CH4"])
        elif key == "probe_atten":
            self.instr.set_probe_atten(1, value["CH1"])
            self.instr.set_probe_atten(2, value["CH2"])
            self.instr.set_probe_atten(3, value["CH3"])
            self.instr.set_probe_atten(4, value["CH4"])
        elif key == "trigger_level":
            self.instr.set_trigger_level(value)
        elif key == "trigger_coupling":
            self.instr.set_trigger_coupling(value)
        elif key == "trigger_edge":
            self.instr.set_trigger_edge(value)
        elif key == "trigger_channel":
            self.instr.set_trigger_channel(value)
        elif key == "labels_enabled":
            self.instr.set_labels_enabled(value)
        else:
            print(f"{self.instr.ID}: ERROR: Unrecognized parameter '{key}'")
        # elif (key == "BW_lim"):
        #     instr.set_BW_lim(value);
        # elif (key == "channel_active"):
        #     pass;

    #
    # Sends the settings object back to the control object.
    #
    def send_state(self):
        pass

    #
    # Reads the waveform from the oscilloscope and sends it back to the UI/control object
    #
    def send_waveform(self):
        start_time = time.time()
        wfms = self.instr.read_all_waveforms(
            self.settings["channel_active"]["CH1"],
            self.settings["channel_active"]["CH2"],
            self.settings["channel_active"]["CH3"],
            self.settings["channel_active"]["CH4"],
        )
        self.values_miso_sig.emit(wfms)

    #        print(f"'Comm' spent {time.time()-start_time} seconds querying + sending waveforms.");

    @pyqtSlot()
    def write(self, command):
        self.instr.write(command)

    @pyqtSlot()
    def query(self, command):
        return self.instr.query(command)


def setButtonState(button: QPushButton, value: bool):
    if value:
        if not button.isChecked():
            button.toggle()
    else:
        if button.isChecked():
            button.toggle()
    # if (control.settings["channel_active"][f"CH{channel}"]):
    #     if (not self.active_but.isChecked()):
    #         self.active_but.toggle();
    # else:
    #     if (self.active_but.isChecked()):
    #         self.active_but.toggle();
