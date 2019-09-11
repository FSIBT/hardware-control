#
# This defines the OscilloscopeControl and OscilloscopeComm classes. By passing
# an instance of a SCPI command wrapper class to an OscilloscpeControl objcet,
# you can easily create GUIs for oscilloscopes.
#

from typing import List
import numpy as np
import json

import time #Get rid of this guy!

import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator, QPixmap
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
# All instrument parameters are saved in a 'state' dictionary. When a function
# such as set_timebase() is called, it updates the state object and sends it to
# the communicaiton object instance. The communication object finds the change
# and sends the correct SCPI commands to the instrument to impliment the change.
#
class PulseGenControl(QGroupBox):

    #Define sigs (to call functions in communication object)
    state_mosi_sig = pyqtSignal(dict);
    action_sig = pyqtSignal(str);
    write_sig = pyqtSignal(str);
    query_sig = pyqtSignal(str);

    def __init__(self, scpi_instr, initialize_with:str="INSTRUMENT", save_on_close:str=False):

        super().__init__("Pulse Generator Control");

        self.state = {};
        self.save_on_close = save_on_close;

        self.comm = PulseGenComm(scpi_instr);
        self.filename = "";

        #Connect signals and sigs
        self.state_mosi_sig.connect(self.comm.get_state);
        self.action_sig.connect(self.comm.get_command);
        self.comm.state_miso_sig.connect(self.get_state);
        #
        self.write_sig.connect(self.comm.write);
        self.query_sig.connect(self.comm.query);

        #Move comm object to comm thread
        self.comm_thread = QThread()
        self.comm.moveToThread(self.comm_thread)
        self.comm_thread.start()

        #Initialize state to correct values
        if (initialize_with == "INSTRUMENT"):
            self.save_on_close = False; #Can't save without filename
            self.state = self.initialize_gui_instrument();
        elif (initialize_with == "DEFAULT"):
            self.save_on_close = False; #Can't save without filename
            self.state = self.default_state();
        else:
            self.load_state(initialize_with);
            self.filename = initialize_with;

        #Create GUI
        #

        self.command_label = QLabel("Trigger Command: ");
        #
        self.command_edit = QLineEdit();
        self.command_edit.editingFinished.connect(lambda: self.set_command(self.command_edit.text() ));
        self.command_edit.setText(self.state["command"]);
        #
        self.trig_but = QPushButton();
        self.trig_but.setText("Trigger");
        self.trig_but.setCheckable(False);
        self.trig_but.clicked.connect(self.trigger);
        #
        self.master_layout = QGridLayout();
        self.master_layout.addWidget(self.command_label, 0, 0, 1, 1);
        self.master_layout.addWidget(self.command_edit, 0, 1, 1, 1);
        self.master_layout.addWidget(self.trig_but, 1, 0, 1, 1);
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

        #Read a state from file
        try:
            with open(filename) as file:
                self.state = json.load(file);
                print(f"State for {self.comm.instr.ID} read from file '{filename}'");
        except:
            print(f"ERROR: Failed to read file '{filename}'. Using defualt case.");
            self.state = self.default_state();

        #Ensure all fields in default_state are present in the loaded state
        for key in dflt:
            if (not(key in self.state)):
                self.state[key] = dflt[key];

    def save_state(self, filename:str):
        try:
            with open(filename, 'w') as file:
                json.dump(self.state, file);
                print(f"State for {self.comm.instr.ID} saved to file '{filename}'");
        except Exception as e:
            print(f"ERROR: Failed to write file '{filename}'. State not saved.");
            print(f"\t{e}")
    #
    # Close connection
    #
    def close(self, filename:str=""):

        #Save state if asked
        if (self.save_on_close):
            self.save_state(self.filename);

        #Tell scope to close
        self.comm.close();

    #
    # Sends the state to the communication object
    #
    def send_state(self):
        """ Use signals/slots to send the state dictionary to the communication
        thread. """
        self.state_mosi_sig.emit(self.state);
        pass;

    #
    # Queries the state from the communication object
    #
    def get_state(self, new_state:dict):
        """ Gets the state from the oscilloscope. """
        self.state = new_state;

    def set_command(self, command:str):
        self.state["command"] = command;
        self.send_state();

    def trigger(self):
        self.action_sig.emit("TRIGGER");

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {};

        dflt["command"] = ":SS";

        return dflt










#
# This is a 4-channel oscilloscope communication progam. It fascilitates
# communication with the scope. For more information on how this works, read the
# comment for the OscilloscopeControl class.
#
class PulseGenComm(QObject):

    state_miso_sig = pyqtSignal(dict);

    def __init__(self, scpi_instr):

        super().__init__();

        self.state = {}; #Read this guy in from a function?
        self.instr_state = {}; #Contains state of instrument so it knows which gs to update

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

        if (command == "TRIGGER"):
            self.instr.trigger();


    #
    # Receives a state object from the control object.
    #
    @pyqtSlot(dict)
    def get_state(self, new_state:dict):

        self.state = new_state;
        for key in self.state:
            if ((not(key in self.instr_state)) or (self.state[key] != self.instr_state[key])):
                self.update_parameter(key, self.state[key]);

        self.instr_state = copy.deepcopy(self.state);

    def update_parameter(self, key:str, value):

        if (key == "command"):
            self.instr.command = value;
        else:
            print(f"{self.instr.ID}: ERROR: Unrecognized parameter '{key}'");


    #
    # Sends the state object back to the control object.
    #
    def send_state(self):
        pass;

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
