#
#

from typing import List
import numpy as np
import json

import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator, QPixmap
from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout,
                             QLineEdit, QPushButton,
                             QHBoxLayout, QLabel, QWidget, QFormLayout, QGridLayout, QComboBox)
import copy

#
#
class FlowControllerControl(QGroupBox):

    #Define sigs (to call functions in communication object)
    state_mosi_sig = pyqtSignal(dict);
    write_sig = pyqtSignal(str);
    query_sig = pyqtSignal(str);

    def __init__(self, scpi_instr, initialize_with:str="INSTRUMENT", save_on_close:str=False, dummy=False):

        super().__init__("Mass Flow Controller Control");

        self.state = {};
        self.save_on_close = save_on_close;

        self.comm = FlowControllerComm(scpi_instr);
        self.filename = "";

        #Connect signals and sigs
        self.state_mosi_sig.connect(self.comm.get_state);
        self.comm.state_miso_sig.connect(self.get_state);
        self.comm.values_miso_sig.connect(self.values_received);
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

        #*************************Create GUI************************

        #****** DEFINE TEXT BOXES
        #
        self.rate_edit = QLineEdit();
        self.rate_edit.setValidator(QDoubleValidator());
        self.rate_edit.editingFinished.connect(lambda: self.set_rate(float(self.rate_edit.text())));
        self.rate_edit.setText(str(self.state["rate"]));
        #
        self.form = QFormLayout();
        self.form.addRow("Flow rate (CFM?):", self.rate_edit);

        self.lower_grid = QGridLayout();
        #
        #******* DEFINE DROPDOWNS + READOUT
        #
        self.gas_label = QLabel("Gas:");
        self.gas_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.gas_drop = QComboBox();
        self.gas_drop.addItems(["Argon", "Helium", "Hydrogen", "Air"]);
        self.gas_drop.currentIndexChanged.connect(lambda: self.set_gas(self.gas_drop.currentText()));
        self.gas_drop.setCurrentText(self.state["gas"]);
        #
        self.pressure_label_fix0 = QLabel("Pressure: ");
        self.pressure_label_fix0.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.pressure_label_readout = QLabel("--");
        self.pressure_label_readout.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.pressure_label_fix1 = QLabel(" Torr?");
        self.pressure_label_fix1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        #
        self.flow_label_fix0 = QLabel("Flow: ");
        self.flow_label_fix0.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.flow_label_readout = QLabel("--");
        self.flow_label_readout.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.flow_label_fix1 = QLabel(" CFM?");
        self.flow_label_fix1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        #Add widgets to grid layout
        self.lower_grid.addWidget(self.gas_label, 0, 0, 1, 1);
        self.lower_grid.addWidget(self.gas_drop, 0, 1, 1, 2);
        self.lower_grid.addWidget(self.pressure_label_fix0, 1, 0, 1, 1);
        self.lower_grid.addWidget(self.pressure_label_readout, 1, 1, 1, 1);
        self.lower_grid.addWidget(self.pressure_label_fix1, 1, 2, 1, 1);
        self.lower_grid.addWidget(self.flow_label_fix0, 2, 0, 1, 1);
        self.lower_grid.addWidget(self.flow_label_readout, 2, 1, 1, 1);
        self.lower_grid.addWidget(self.flow_label_fix1, 2, 2, 1, 1);


        #******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout();
        self.master_layout.addLayout(self.form, 0, 0);
        self.master_layout.addLayout(self.lower_grid, 1, 0);
        self.setLayout(self.master_layout);

        #Write state to scope - synch scope with GUI
        self.send_state();

    def initialize_gui_instrument():
        print("\n\nOh no! I haven't implimented this yet!!\n\n");
        pass;


    def load_state(self, filename:str):
        try:
            with open(filename) as file:
                self.state = json.load(file);
                print(f"State for {self.comm.instr.ID} read from file '{filename}'");
        except:
            print(f"ERROR: Failed to read file '{filename}'. Using defualt case.");
            self.state = self.default_state();

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

    def set_gas(self, gas:str):
        """Sets the gas the flow controller is to regulate"""
        self.state["gas"] = gas;
        self.send_state();

    def set_rate(self, rate:float):
        """Sets the flow rate"""
        self.state["rate"] = rate;
        self.send_state();

    #
    # Receives values for pressure and flow rate in dict from comm object (whcih queries meter)
    #
    def values_received(self, values:dict):
        self.pressure_label_readout.setText(str(values["pressure"]));
        self.flow_label_readout.setText(str(values["flow"]));

    #
    # Manually send a SCPI command through the communication object to the INSTR
    #
    def write(self, command:str):
        """ Manually send SCPI commands to the instruments. """
        write_sig.emit(command);

    #
    # Manually query a SCPI command through the communication obeect to the INSTR
    #
    def query(self, command:str):
        """ Manually send/receive commands to/from the instrument. """
        return query_sig.emit(command);

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {};

        dflt["gas"] = "Argon";
        dflt["rate"] = 0.0;

        return dflt










#
# This is a 4-channel oscilloscope communication progam. It fascilitates
# communication with the scope. For more information on how this works, read the
# comment for the OscilloscopeControl class.
#
class FlowControllerComm(QObject):

    state_miso_sig = pyqtSignal(dict);
    values_miso_sig = pyqtSignal(dict);

    def __init__(self, scpi_instr):

        super().__init__();

        self.state = {}; #Read this guy in from a function?
        self.instr_state = {}; #Contains state of instrument so it knows which keys to update

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

        self.display_timer = QTimer(self)
        self.display_timer.timeout.connect(self.get_values);
        self.display_timer.start(1000); #1s period

        #This program needs to impliment a second timer to automatically update the pressure readout

    #
    # Tries to connect to the oscilloscope. Is called by the timer every second.
    # If already connected, returns immediately.
    #
    def try_connect(self):
        self.instr.try_connect();

    #
    # Close connection
    #
    def close(self):
        self.instr.close();


    #
    # Receives a state object from the control object.
    #
    def get_state(self, new_state:dict):

        self.state = new_state;
        for key in self.state:
            if ((not(key in self.instr_state)) or (self.state[key] != self.instr_state[key])):
                self.update_parameter(key, self.state[key]);

        self.instr_state = copy.deepcopy(self.state);

    def update_parameter(self, key:str, value):

        if (key == "rate"):
            self.instr.set_rate(value);
        elif (key == "gas"):
            self.instr.set_gas(value);
        else:
            print(f"{self.instr.ID}: ERROR: Unrecognized parameter '{key}'");

    #Gets flow and pressure from meter, returns it to 'control' object
    def get_values(self):
        vals = self.instr.get_values();
        self.values_miso_sig.emit(vals);



    #
    # Sends the state object back to the control object.
    #
    def send_state():
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
