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
from hardware_control.HC_Backend import HC_Backend


def to_NR3(x: float):
    return f" {x:.6E}"


def to_NR1(x: int):
    return f"{x:d}"


def bool_NR1(x: bool):
    if x:
        return "1"
    else:
        return "0"


class SRSDG535Ctrl(HC_Backend):
    def __init__(self, visa_addr, dummy: bool = False, print_commands: bool = False):

        self.ID = "SRS_DG535"

        self.visa_addr = visa_addr
        self.online = False
        self.dummy = dummy
        self.print_commands = print_commands
        self.num_vert_divisions = 8

        self.command_str = ""

        self.use_sockets = (
            False
        )  # This tells the default try_connect() function to use Pyvisa

    def update_setting(self, setting: str, value):
        try:
            if self.dummy:
                return value
            else:
                if setting == "command":
                    self.command_str = value
                    return value
        except Exception as e:
            print("An exception occured in update_setting() of SRSDG535Ctrl.py.")
            print(str(e))

    def command(self, cmd: str):
        if cmd == "TRIGGER":
            """Tells DG535 to trigger"""
            self.write(self.command_str)
        return cmd

    def write(self, cmd: str):
        if self.online and not self.dummy:
            if not self.use_sockets:
                self.instr.write(cmd)
            if self.print_commands:
                print(f'\tSRSDG535< "{cmd}"')
