#
# This defines the OscilloscopeControl and OscilloscopeComm classes. By passing
# an instance of a SCPI command wrapper class to an OscilloscpeControl objcet,
# you can easily create GUIs for oscilloscopes.
#

from typing import List
import numpy as np
import json
import pkg_resources

import time #Get rid of this guy!

from hardware_control.QHelper import QInstrument
import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator, QPixmap, QIcon
from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout,
                             QLineEdit, QPushButton,
                             QHBoxLayout, QLabel, QWidget, QFormLayout, QGridLayout, QComboBox)
import copy

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
class HFunctionGenerator(QInstrument):

    #Define sigs (to call functions in communication object)
    state_mosi_sig = pyqtSignal(dict);
    action_sig = pyqtSignal(str);
    write_sig = pyqtSignal(str);
    query_sig = pyqtSignal(str);

    def __init__(self, scpi_instr, window, name:str="Oscilloscope Control", initialize_with:str="INSTRUMENT", save_on_close:str=False, num_channels:int=2):

        super().__init__(window, name);

        self.settings = {};
        self.save_on_close = save_on_close;

        self.comm = FunctionGeneratorComm(scpi_instr);
        self.filename = "";

        #Connect signals and sigs
        self.state_mosi_sig.connect(self.comm.get_state);
        self.action_sig.connect(self.comm.get_command);
        self.comm.state_miso_sig.connect(self.get_state);
        self.comm.values_miso_sig.connect(self.values_received);
        #
        self.write_sig.connect(self.comm.write);
        self.query_sig.connect(self.comm.query);

        #Move comm object to comm thread
        self.comm_thread = QThread()
        self.comm.moveToThread(self.comm_thread)
        self.comm_thread.start()

        #Initialize settings to correct values
        if (initialize_with == "INSTRUMENT"):
            self.save_on_close = False; #Can't save without filename
            self.settings = self.initialize_gui_instrument();
        elif (initialize_with == "DEFAULT"):
            self.save_on_close = False; #Can't save without filename
            self.settings = self.default_state();
        else:
            self.load_state(initialize_with);
            self.filename = initialize_with;

        ch1 = FunctionGeneratorChannelWidget(1, self);
        

        self.channel_panel = QGridLayout();
        self.channel_panel.addWidget(ch1, 0, 0);
        
        if (num_channels == 2):
            ch2 = FunctionGeneratorChannelWidget(2, self);
            self.channel_panel.addWidget(ch2, 0, 1)

        self.master_layout = QGridLayout();
        self.master_layout.addLayout(self.channel_panel, 1, 0, 1, 4);

        #
        self.setLayout(self.master_layout);

        #Write state to scope - synch scope with GUI
        self.send_state();

    def initialize_gui_instrument():
        print("\n\nOh no! I haven't implimented this yet!!\n\n");
        pass;


    def load_state(self, filename:str):

        #Get default state - this identifies all required fields
        dflt = self.default_state();

        #Read a settings from file
        try:
            with open(filename) as file:
                self.settings = json.load(file);
                print(f"settings for {self.comm.instr.ID} read from file '{filename}'");
        except:
            print(f"ERROR: Failed to read file '{filename}'. Using defualt case.");
            self.settings = self.default_state();

        #Ensure all fields in default_state are present in the loaded state
        for key in dflt:
            if (not(key in self.settings)):
                self.settings[key] = dflt[key];

    def save_state(self, filename:str):
        try:
            with open(filename, 'w') as file:
                json.dump(self.settings, file);
                print(f"settings for {self.comm.instr.ID} saved to file '{filename}'");
        except Exception as e:
            print(f"ERROR: Failed to write file '{filename}'. settings not saved.");
            print(f"\t{e}")
    #
    # Close connection
    #
    def close(self, filename:str=""):

        #Save settings if asked
        if (self.save_on_close):
            self.save_state(self.filename);

        #Tell scope to close
        self.comm.close();

    #
    # Sends the settings to the communication object
    #
    def send_state(self):
        """ Use signals/slots to send the settings dictionary to the communication
        thread. """
        self.state_mosi_sig.emit(self.settings);
        pass;

    #
    # Queries the settings from the communication object
    #
    def get_state(self, new_state:dict):
        """ Gets the settings from the oscilloscope. """
        self.settings = new_state;

    #
    # Called when a waveform is read - updates the display
    #
    def values_received(self, values:dict):
        #Do plotting here
        self.disp.update_display(values);
        pass

    def set_settings_and_send(parameter:str, value):
        if (type(value) != type(self.settings[parameter])):
            current_val = self.settings[parameter]
            print(f"ERROR: Tried to assign value of type '{type(value)}' to field '{parameter}', which has type '{type(current_val)}'");
            return;
        self.settings[parameter] = value;

    def query_waveforms(self):
        start_time = time.time();
        self.action_sig.emit("WAVEFORMS");
#        print(f"'Control' spent {time.time()-start_time} seconds querying waveforms.");

    #
    # Manually send a SCPI command through the communication object to the INSTR
    #
    def write(self, command:str):
        """ Manually send SCPI commands to the oscilloscope. """
        write_sig.emit(command);

    #
    # Manually query a SCPI command through the communication obeect to the INSTR
    #
    def query(self, command:str):
        """ Manually send/receive commands to/from the oscilloscope. """
        return query_sig.emit(command);

    #
    # Create a default settings object if can't get settings from a file
    #
    def default_state(self):

        dflt = {};

        dflt["CH1_amplitude"] = 1;
        dflt["CH1_frequency"] = 1e3;
        dflt["CH1_offset"] = 0;
        dflt["CH1_waveform"] = "Sine";
        dflt["CH1_modulation_on"] = False;
        dflt["CH1_burst_on"] = False;
        dflt["CH1_impedance"] = 1e6;
        dflt["CH1_output_on"] = False;
        
        dflt["CH2_amplitude"] = 1;
        dflt["CH2_frequency"] = 1e3;
        dflt["CH2_offset"] = 0;
        dflt["CH2_waveform"] = "Sine";
        dflt["CH2_modulation_on"] = False;
        dflt["CH2_burst_on"] = False;
        dflt["CH2_impedance"] = 1e6;
        dflt["CH2_output_on"] = False;

        return dflt





#
# Defines a UI for AWG channels
#
class FunctionGeneratorChannelWidget(QWidget):

    def __init__(self, channel:int, control):
        super().__init__();

        self.channel = channel;

        #************** DEFINE UI *********************#

        self.channel_label = QLabel();
        if (self.channel == 1):
            self.channel_label.setPixmap(QPixmap(pkg_resources.resource_filename('hardware_control', 'FunctionGenerator/graphics/channel1_yellow.png')));
        else:
            self.channel_label.setPixmap(QPixmap(pkg_resources.resource_filename('hardware_control', 'FunctionGenerator/graphics/channel2_green.png')));

        #****** DEFINE TEXT BOXES
        #
        self.amplitude_edit = QLineEdit();
        self.amplitude_edit.setValidator(QDoubleValidator());
        self.amplitude_edit.editingFinished.connect(lambda: control.set_settings_and_send(f"CH{channel}_amplitude", float(self.amplitude_edit.text())));
        self.amplitude_edit.setText(str(control.settings[f"CH{channel}_amplitude"]));
        #
        self.offset_edit = QLineEdit();
        self.offset_edit.setValidator(QDoubleValidator());
        self.offset_edit.editingFinished.connect(lambda: control.set_settings_and_send(f"CH{channel}_amplitude", float(self.offset_edit.text())));
        self.offset_edit.setText(str(control.settings[f"CH{channel}_offset"]));
        #
        self.frequency_edit = QLineEdit();
        self.frequency_edit.setValidator(QDoubleValidator());
        self.frequency_edit.editingFinished.connect(lambda: control.set_settings_and_send(f"CH{channel}_amplitude", float(self.frequency_edit.text())));
        self.frequency_edit.setText(str(control.settings[f"CH{channel}_frequency"]));
        #
        self.form = QFormLayout();
        self.form.addRow("Amplitude (Vpp):", self.amplitude_edit);
        self.form.addRow("Offset (V):", self.offset_edit);
        self.form.addRow("Frequency (Hz):", self.frequency_edit);


        self.lower_grid = QGridLayout();

        #******* DEFINE BUTTONS + DROPDOWNS
        #
        self.active_but = QPushButton();
        self.active_but.setText("Output On/Off");
        self.active_but.setCheckable(True);
        self.active_but.clicked.connect(lambda: control.set_settings_and_send(f"CH{channel}_output_on", self.active_but.isChecked()));
        setButtonState(self.active_but, control.settings[f"CH{channel}_output_on"]);
        #
        self.mod_but = QPushButton();
        self.mod_but.setText("Modulation");
        self.mod_but.setIcon(QIcon((QPixmap(pkg_resources.resource_filename('hardware_control', 'FunctionGenerator/graphics/modulation.png')))));
        self.mod_but.setCheckable(True);
        self.mod_but.clicked.connect(lambda: control.set_settings_and_send(f"CH{channel}_output_on", self.mod_but.isChecked()));
        setButtonState(self.mod_but, control.settings[f"CH{channel}_output_on"]);
        #
        self.burst_but = QPushButton();
        self.burst_but.setText("Burst");
        self.burst_but.setCheckable(True);
        self.burst_but.setIcon(QIcon((QPixmap(pkg_resources.resource_filename('hardware_control', 'FunctionGenerator/graphics/burst.png')))));
        self.burst_but.clicked.connect(lambda: control.set_settings_and_send(f"CH{channel}_burst_on", self.burst_but.isChecked()));
        setButtonState(self.burst_but, control.settings[f"CH{channel}_burst_on"]);
        #
        #
        self.waveform_label = QLabel("Waveform:");
        self.waveform_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.waveform_drop = QComboBox();
        self.waveform_drop.addItems(["Sine", "Square", "Triangle", "Noise", "DC", "File"]);
        self.waveform_drop.currentIndexChanged.connect(lambda: control.set_channel_coupling(self.channel, self.coupling_drop.currentText()));
        self.waveform_drop.setCurrentText(control.settings[f"CH{channel}_waveform"]);
        #
        self.impedance_label = QLabel("Impedance:");
        self.impedance_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.impedance_drop = QComboBox();
        self.impedance_drop.addItems(["1e6", "50"]);
        self.impedance_drop.currentIndexChanged.connect(lambda: control.set_settings_and_send(f"CH{channel}_impedance", float(self.impedance_drop.currentText())));
        self.impedance_drop.setCurrentText(str(control.settings[f"CH{channel}_impedance"]));
        #
        #Add widgets to grid layout
        self.lower_grid.addWidget(self.active_but, 0, 0);
        self.lower_grid.addWidget(self.mod_but, 1, 0);
        self.lower_grid.addWidget(self.burst_but, 1, 1);
        self.lower_grid.addWidget(self.waveform_label, 2, 0);
        self.lower_grid.addWidget(self.waveform_drop, 2, 1);
        self.lower_grid.addWidget(self.impedance_label, 3, 0);
        self.lower_grid.addWidget(self.impedance_drop, 3, 1);

        #******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout();
        self.master_layout.addWidget(self.channel_label, 0, 0)
        self.master_layout.addLayout(self.form, 1, 0);
        self.master_layout.addLayout(self.lower_grid, 2, 0);
        self.setLayout(self.master_layout);






#
# This is a 4-channel oscilloscope communication progam. It fascilitates
# communication with the scope. For more information on how this works, read the
# comment for the OscilloscopeControl class.
#
class FunctionGeneratorComm(QObject):

    state_miso_sig = pyqtSignal(dict);
    values_miso_sig = pyqtSignal(dict);

    def __init__(self, scpi_instr):

        super().__init__();

        self.settings = {}; #Read this guy in from a function?
        self.instr_state = {}; #Contains settings of instrument so it knows which gs to update

        self.instr = scpi_instr;

        self.instr.try_connect();
        if (not self.instr.online):
            print(f"{self.instr.ID}: Failed to connect");
        else:
            print(f"{self.instr.ID}: Connected");

        #Connect timer
        self.connect_timer = QTimer(self)
        self.connect_timer.timeout.connect(self.instr.try_connect);
        self.connect_timer.start(1000); #1s period

    #
    # Close connection
    #
    def close(self):
        self.instr.close();

    @pyqtSlot(str)
    def get_command(self, command:str):

        if (command == "SINGLE"):
            self.instr.single_trigger();
        elif (command == "RUN"):
            self.instr.norm_trigger();
        elif (command == "HALT"):
            self.instr.halt();
        elif(command == "WAVEFORMS"):
            self.send_waveform();


    #
    # Receives a settings object from the control object.
    #
    @pyqtSlot(dict)
    def get_state(self, new_state:dict):

        self.settings = new_state;
        for key in self.settings:
            if ((not(key in self.instr_state)) or (self.settings[key] != self.instr_state[key])):
                self.update_parameter(key, self.settings[key]);

        self.instr_state = copy.deepcopy(self.settings);

    def update_parameter(self, key:str, value):

        if (key == "se"):
            self.instr.set_timebase(value);
        elif (key == "time_offset"):
            self.instr.set_time_offset(value);
        elif (key == "volts_div"):
            self.instr.set_volts_div(1, value["CH1"]);
            self.instr.set_volts_div(2, value["CH2"]);
            self.instr.set_volts_div(3, value["CH3"]);
            self.instr.set_volts_div(4, value["CH4"]);
        elif (key == "offset"):
            self.instr.set_offset(1, value["CH1"]);
            self.instr.set_offset(2, value["CH2"]);
            self.instr.set_offset(3, value["CH3"]);
            self.instr.set_offset(4, value["CH4"]);
        elif (key == "channel_label"):
            self.instr.set_channel_label(1, value["CH1"]);
            self.instr.set_channel_label(2, value["CH2"]);
            self.instr.set_channel_label(3, value["CH3"]);
            self.instr.set_channel_label(4, value["CH4"]);
        elif (key == "channel_active"):
            self.instr.set_channel_active(1, value["CH1"]);
            self.instr.set_channel_active(2, value["CH2"]);
            self.instr.set_channel_active(3, value["CH3"]);
            self.instr.set_channel_active(4, value["CH4"]);
        elif (key == "BW_lim"):
            self.instr.set_BW_lim(1, value["CH1"]);
            self.instr.set_BW_lim(2, value["CH2"]);
            self.instr.set_BW_lim(3, value["CH3"]);
            self.instr.set_BW_lim(4, value["CH4"]);
        elif (key == "channel_invert"):
            self.instr.set_channel_invert(1, value["CH1"]);
            self.instr.set_channel_invert(2, value["CH2"]);
            self.instr.set_channel_invert(3, value["CH3"]);
            self.instr.set_channel_invert(4, value["CH4"]);
        elif (key == "channel_impedance"):
            self.instr.set_channel_impedance(1, value["CH1"]);
            self.instr.set_channel_impedance(2, value["CH2"]);
            self.instr.set_channel_impedance(3, value["CH3"]);
            self.instr.set_channel_impedance(4, value["CH4"]);
        elif (key == "channel_coupling"):
            self.instr.set_channel_coupling(1, value["CH1"]);
            self.instr.set_channel_coupling(2, value["CH2"]);
            self.instr.set_channel_coupling(3, value["CH3"]);
            self.instr.set_channel_coupling(4, value["CH4"]);
        elif (key == "probe_atten"):
            self.instr.set_probe_atten(1, value["CH1"]);
            self.instr.set_probe_atten(2, value["CH2"]);
            self.instr.set_probe_atten(3, value["CH3"]);
            self.instr.set_probe_atten(4, value["CH4"]);
        elif(key == "trigger_level"):
            self.instr.set_trigger_level(value);
        elif(key == "trigger_coupling"):
            self.instr.set_trigger_coupling(value);
        elif(key == "trigger_edge"):
            self.instr.set_trigger_edge(value);
        elif(key == "trigger_channel"):
            self.instr.set_trigger_channel(value);
        elif(key == "labels_enabled"):
            self.instr.set_labels_enabled(value);
        else:
            print(f"{self.instr.ID}: ERROR: Unrecognized parameter '{key}'");
        # elif (key == "BW_lim"):
        #     instr.set_BW_lim(value);
        # elif (key == "channel_active"):
        #     pass;


    #
    # Sends the settings object back to the control object.
    #
    def send_state(self):
        pass;

    #
    # Reads the waveform from the oscilloscope and sends it back to the UI/control object
    #
    def send_waveform(self):
        start_time = time.time();
        wfms = self.instr.read_all_waveforms(self.settings["channel_active"]["CH1"], self.settings["channel_active"]["CH2"], self.settings["channel_active"]["CH3"], self.settings["channel_active"]["CH4"]);
        self.values_miso_sig.emit(wfms);
#        print(f"'Comm' spent {time.time()-start_time} seconds querying + sending waveforms.");


    @pyqtSlot()
    def write(self, command):
        self.instr.write(command);

    @pyqtSlot()
    def query(self, command):
        return self.instr.query(command);


def setButtonState(button:QPushButton, value:bool):
    if (value):
        if (not button.isChecked()):
            button.toggle();
    else:
        if (button.isChecked()):
            button.toggle();
