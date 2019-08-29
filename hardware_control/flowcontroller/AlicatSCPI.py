#
#
# G M Giesbrecht
# 20/08/2019
#

import pyvisa
from typing import List
import numpy as np

def to_NR3(x:float):
    return f" {x:.6E}";

def to_NR1(x:int):
    return f"{x:d}";

def bool_NR1(x:bool):
    if (x):
        return "1";
    else:
        return "0";

class AlicatSCPI:

    def __init__(self, visa_addr, dummy:bool=False, print_commands:bool=False):

        self.ID = "AlicatMSeries";

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
                self.meter = rm.open_resource(self.visa_addr, send_end=True) #Open connection
            except: #Failed to conncet
                self.online = False;
            else:
                self.online = True;

        else:
            print(f"{self.ID}: creating dummy connection to {self.visa_addr}");
            self.online = True

    #
    # Close connection
    #
    def close(self):
        if (not self.dummy):
            self.meter.close();
        else:
            print(f"{self.ID}: closed dummy connection")

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

    def set_rate(self, value:float):
        #"""Sets the time per division"""

        print(f"NOT YET IMPLIMENTED: Would set flowrate to {value} (units: ?).");

        # if (not self.dummy):
        #     self.write(f":TIM:SCAL {to_NR3(value)}");

    def set_gas(self, value:str):
        #"""Sets the time per division"""

        print(f"NOT YET IMPLIMENTED: Would set gas type to {value}.");

        # if (not self.dummy):
        #     self.write(f":TIM:SCAL {to_NR3(value)}");

    def write(self, command:str):
        self.scope.write(command);
        if (self.print_commands):
            print(f"\t{self.ID}< \"{command}\"");

    def query(self, command:str):
        reply = self.scope.query(command);
        if (self.print_commands):
            print(f"\t{self.ID}< \"{command}\" > {reply}");
        return reply;
