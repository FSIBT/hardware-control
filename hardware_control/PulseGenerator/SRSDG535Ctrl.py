# This class wraps SCPI commands with python functions. It is fed to the
# communication object used by the control object. Originally this SCPI class
# was part of the control class, but they were separated so that command line
# program or scipts can be made that don't depend on Qt - this function will
# have no Qt dependencies.
#
#
# G M Giesbrecht
# 20/08/2019
#

import pyvisa
from typing import List
import numpy as np
import socket

def to_NR3(x:float):
    return f" {x:.6E}";

def to_NR1(x:int):
    return f"{x:d}";

def bool_NR1(x:bool):
    if (x):
        return "1";
    else:
        return "0";

class SRSDG535Ctrl:

    def __init__(self, visa_addr, dummy:bool=False, print_commands:bool=False):

        self.ID = "SRS_DG535";

        self.visa_addr = visa_addr;
        self.online = False;
        self.dummy = dummy;
        self.print_commands = print_commands;
        self.num_vert_divisions = 8;

        self.try_connect();

    #
    # Tries to connect to the oscilloscope. Is called by the timer every second.
    # If already connected, returns immediately.
    #
    def try_connect(self):

        if (self.online):
            return

        if (not self.dummy):

            try:
                rm = pyvisa.ResourceManager();
                self.instr = rm.open_resource(self.visa_addr) #Open connection
                # self.configure_read_waveform();
            except Exception as e: #Failed to conncet);
                print(e);
                self.online = False;
            else:
                self.online = True;

        else:
            print(f'{self.ID}: creating dummy connection to {self.visa_addr}')
            self.online = True

    #
    # Close connection
    #
    def close(self):
        if (not self.dummy and self.online):
            self.instr.close();
        else:
            print('KEY4000X: closed dummy connection')

    #
    # Receives a state object from the control object.
    #
    def get_state(new_state:dict):
        self.state = new_state;

        new = set(self.state.items());
        old = set(self.instr_state.items());

        diff = new - old;

        for param in diff:
            update_parameter(param[0], param[1]);
            pass;



    def set_command(self, value:str):
        """Sets the command to send when triggering."""
        self.command = value;

    def trigger(self):
        """Tells DG535 to trigger"""
        self.write(self.command);
        pass;

    def write(self, command:str):
        if (self.online and not self.dummy):
            if (not self.use_sockets):
                self.instr.write(command);
            else:
                self.instr.sendall(bytes(command+"\n", "utf-8"));
            if (self.print_commands):
                print(f"\tKEY4000X< \"{command}\"");


    def query(self, command:str):
        if (self.online and not self.dummy):
            if (not self.use_sockets):
                reply = self.instr.query(command);
            else:
                self.instr.sendall(bytes(command+"\n", "utf-8"));
                reply_bytes = recvall(self.instr);
                print(f"reply size: {len(reply_bytes)}")
                reply = str(reply_bytes);
                if (len(reply) < 100):
                    print("\t\t"+reply);
                reply = reply[2:len(reply)-3];
            if (self.print_commands):
                print(f"\t{self.ID}< \"{command}\"");
            return reply;
        else:
            return "";


#71-209
