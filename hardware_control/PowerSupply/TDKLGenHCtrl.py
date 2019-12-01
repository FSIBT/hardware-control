import pyvisa
from typing import List
import numpy as np
import socket
from hardware_control.HC_Backend import HC_Backend
import re
import random


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


class TDKLGenHCtrl(HC_Backend):
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

        self.num_channels = 1
        # This specifies the max number of channels the user can request

    def update_setting(self, setting: str, value):

        if not self.online:
            return f"{self.ID}-Offline"

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
                f"An error occured in {self.ID} when sending SCPI commands to the instrument."
            )
            print(f"\t{str(e)}")
            print(f"\t{setting}, {value}")

    def command(self, cmd: str):

        if not self.online:
            return f"{self.ID}-Offline"

        try:
            if self.dummy:
                num = random.randint(0, 10)
                return f"{cmd.strip('?')}={num}"
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of PSU
                if regex_compare("CH._V_out?", cmd):
                    rval = self.query(":MEAS:VOLT?")
                    chstr = cmd[0:3]
                    return f"{cmd}={rval}"
                elif regex_compare("CH._I_out?", cmd):
                    rval = self.query(":MEAS:CURR?")
                    chstr = cmd[0:3]
                    return f"{cmd}={rval}"
                elif regex_compare("CH._I_set?", cmd):
                    chstr = cmd[0:3]
                    rval = self.query(":SOUR:CURR:LEV:IMM:AMPL?")
                    return f"{cmd}={rval}"
                elif regex_compare("CH._V_set?", cmd):
                    chstr = cmd[0:3]
                    rval = self.query(":SOUR:VOLT:LEV:IMM:AMPL?")
                    return f"{cmd}={rval}"
        except Exception as e:
            print(
                "An error occured in CAEN14xxETCtrl.py when sending SCPI commands to the instrument."
            )
            print(str(e))
