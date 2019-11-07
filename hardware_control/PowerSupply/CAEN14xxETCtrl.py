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
import re


def to_NR3(x: float):
    return f" {x:.6E}"


def to_NR1(x: int):
    return f"{x:d}"


def bool_NR1(x: bool):
    if x:
        return "1"
    else:
        return "0"


def str_to_bool(x: str):
    if x == "True":
        return True
    else:
        return False


def regex_compare(pattern: str, comp: str):
    regex = re.compile(pattern)
    return bool(re.match(regex, comp))


class CAEN14xxETCtrl(HC_Backend):
    def __init__(
        self,
        visa_addr,
        dummy: bool = False,
        print_commands: bool = False,
        use_sockets: bool = False,
        ip_addr: str = "",
        port_no=5025,
    ):

        super().__init__()

        self.ID = "TDKL-GenH"

        self.visa_addr = visa_addr
        self.online = False
        self.dummy = dummy
        self.print_commands = print_commands

        self.use_sockets = use_sockets
        self.port_no = port_no
        self.ip_addr = ip_addr

        self.num_channels = 8
        # This specifies the max number of channels the user can request

    #
    # Tries to connect to the instrument. Is called by the timer every second.
    # If already connected, returns immediately.
    #
    def try_connect(self):
        """Checks if the backend is in communication with the object, if it is
        not, it tries to re-establish communication."""

        # Handle dummy case
        if self.dummy:
            if self.online:
                return True
            else:
                print(f"{self.ID}: creating dummy connection to {self.visa_addr}")
                self.online = True
                return True

        if self.online:  # Has previously connected to the isntrument

            try:  # Check if connected by asking for instrument ID
                self.device.query("*IDN?")
            except pyvisa.errors.VisaIOError as e:  # Not connected - reconnect
                if self.debug:
                    print("Lost connection to device. Will try to reconnect")
                    print(f"\t{str(e)}")
            else:  # Connection stable - return True
                return True

        if self.debug:
            print("trying to connect")

        # Try to connect to instrument
        try:
            if not self.use_sockets:  # Use Pyvisa
                rm = pyvisa.ResourceManager()
                self.device = rm.open_resource(self.visa_addr)  # Open connection

                # Verify actually connected (open_resource won't always throw error w/ disconnected USB)
                self.device.query("*IDN?")
                if self.debug:
                    print("opened connection")

            else:  # Use sockets
                self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                self.device.connect((self.ip_addr, self.port_no))
        except Exception as e:  # Failed to conncet

            self.online = False
            if self.debug:
                print(f"\t{str(e)}")
                print("OFFLINE")
        else:
            self.online = True

        return self.online

    def update_setting(self, setting: str, value):

        try:
            if self.dummy:
                return value
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of PSU
                if regex_compare("CH._enable", setting):
                    if str_to_bool(value):
                        self.write(":OUTP:STAT ON")
                    else:
                        self.write(":OUTP:STAT OFF")
                    rval = self.query(":OUTP:STAT?")
                    return str(rval == "1\n")
                elif regex_compare("CH._I_set", setting):
                    self.write(f":SOUR:CURR:LEV:IMM:AMPL {value}")
                    rval = self.query(":SOUR:CURR:LEV:IMM:AMPL?")
                    return rval
                elif regex_compare("CH._V_set", setting):
                    self.write(f":SOUR:VOLT:LEV:IMM:AMPL {value}")
                    rval = self.query(":SOUR:VOLT:LEV:IMM:AMPL?")
                    return rval
        except Exception as e:
            print(
                "An error occured in CAEN14xxETCtrl.py when sending SCPI commands to the instrument."
            )
            print(f"\t{str(e)}")
            print(f"\t{setting}, {value}")

    def command(self, cmd: str):

        try:
            if self.dummy:
                return cmd
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of PSU
                if regex_compare("CH._V_out", cmd):
                    rval = self.query(":MEAS:VOLT?")
                    chstr = cmd[0:3]
                    return f"{cmd}={rval}"
                elif regex_compare("CH._I_out", cmd):
                    rval = self.query(":MEAS:CURR?")
                    chstr = cmd[0:3]
                    return f"{cmd}={rval}"
                elif regex_compare("CH._I_set", cmd):
                    chstr = cmd[0:3]
                    rval = self.query(":SOUR:CURR:LEV:IMM:AMPL?")
                    return f"{cmd}={rval}"
                elif regex_compare("CH._V_set", cmd):
                    chstr = cmd[0:3]
                    rval = self.query(":SOUR:VOLT:LEV:IMM:AMPL?")
                    return f"{cmd}={rval}"
        except Exception as e:
            print(
                "An error occured in CAEN14xxETCtrl.py when sending SCPI commands to the instrument."
            )
            print(str(e))
