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
import re
from hardware_control.HC_Backend import HC_Backend


def to_NR3(x: float):
    return f" {x:.6E}"


def str_NR3(x: str):
    x_float = float(x)
    return f" {x_float:.6E}"


def to_NR1(x: int):
    return f"{x:d}"


def str_NR1(x: str):
    x_int = int(x)
    return f"{x_int:d}"


def bool_NR1(x: bool):
    if x:
        return "1"
    else:
        return "0"


def boolstr_NR1(x: str):
    if x == "True":
        return "1"
    else:
        return "0"


def regex_compare(pattern: str, comp: str):
    regex = re.compile(pattern)
    return bool(re.match(regex, comp))


class ZMQOscilloscopeCtrl(HC_Backend):
    def __init__(
        self,
        zmq_addr,
        dummy: bool = False,
        print_commands: bool = False,
        use_sockets: bool = False,
        ip_addr: str = "",
        port_no=5025,
    ):

        super().__init__()
        self.ID = "ZMQ-Oscilloscope"

        # Create context and socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)

        self.zmq_address = zmq_address
        self.online = False
        self.dummy = dummy
        self.print_commands = print_commands
        self.num_vert_divisions = 8

        self.use_sockets = use_sockets
        self.port_no = port_no
        self.ip_addr = ip_addr
        # self.try_connect()

    def update_setting(self, setting: str, value):

        if not self.online:
            return "Offline"

        try:
            if self.dummy:
                return value
            else:
                if regex_compare("CH._volts_div", setting):
                    chan = setting[2]
                    self.write(f":CHAN{chan}:SCAL {str_NR3(value)}")
                    return self.query(f":CHAN{chan}:SCAL?")

                elif setting == "timebase":
                    self.write(f":TIM:SCAL {str_NR3(value)}")
                    return self.query(":TIM:SCAL?")

                elif setting == "time_offset":
                    self.write(f":TIM:POS {str_NR3(value)}")
                    return self.query(":TIM:POS?")

                elif regex_compare("CH._offset", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:OFFS {to_NR3(-1.0 * float(value))}")
                    return self.query(f"CHAN{chan}:OFFS?")

                elif regex_compare("CH._BW_lim", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:BWL {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:BWL?")

                elif regex_compare("CH._active", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:DISP {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:DISP?")

                elif regex_compare("CH._impedance", setting):
                    chan = setting[2]
                    if value == "50":
                        self.write(f"CHAN{chan}:IMP FIFT")
                    else:
                        self.write(f"CHAN{chan}:IMP ONEM")
                    return self.query(f"CHAN{chan}:IMP?")

                elif regex_compare("CH._label", setting):

                    # Length is capped at 32 characters
                    if len(value) > 32:
                        value = value[0:32]

                    chan = setting[2]
                    self.write(f"CHAN{chan}:LAB {value}")
                    return self.query(f"CHAN{chan}:LAB?")

                elif setting == "labels_enabled":
                    self.write(f"DISP:LAB {boolstr_NR1(value)}")
                    print(f"DISP:LAB {boolstr_NR1(value)}")
                    return self.query(f"DISP:LAB?")

                elif regex_compare("CH._invert", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:INV {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:INV?")

                elif regex_compare("CH._probe_atten", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:PROB {str_NR3(value)}")
                    return self.query(
                        f"CHAN{chan}:PROB?"
                    )  # ie. 10 gives x10 or 10:1 probe

                elif regex_compare("CH._coupling", setting):
                    chan = setting[2]

                    # Make sure valid value provided
                    if value != "AC" and value != "DC":
                        value = "DC"

                    self.write(f"CHAN{chan}:COUP {value}")
                    return self.query(f"CHAN{chan}:COUP?")

                elif setting == "trigger_level":
                    self.write(f"TRIG:EDGE:LEV {str_NR3(value)}")
                    return self.query(f"TRIG:EDGE:LEV?")

                elif setting == "trigger_coupling":

                    # Make sure valid option given
                    if value != "AC" and value != "DC" and value != "LFReject":
                        value = "DC"

                    self.write(f"TRIG:COUP {value}")
                    return self.query(f"TRIG:COUP?")

                elif setting == "trigger_edge":

                    # Make sure valid option given
                    if (
                        value != "BOTH"
                        and value != "NEG"
                        and value != "POS"
                        and value != "ALT"
                    ):
                        value = "POS"

                    self.write(f"TRIG:EDGE:SLOP {value}")
                    return self.query(f"TRIG:EDGE:SLOP?")

                elif setting == "trigger_channel":

                    self.write(f"TRIG:SOUR CHAN{str_NR1(value)}")
                    return self.query(f"TRIG:SOUR?")
        except Exception as e:
            print(
                "An error occured in Key4000XCtrl.py when sending SCPI commands to the instrument."
            )
            print(str(e))

    def command(self, cmd: str):
        if not self.online:
            return "Offline"
        else:
            return cmd

    def try_connect(self):

        if self.dummy:
            if self.online:
                return True
            else:
                print(f"{self.ID}: creating dummy connection to {self.visa_addr}")
                self.online = True
                return True

        if self.online:
            # Todo: check that this will reconnect automatically, if not fix
            return True

        socket.connect(self.zmq_address)

        self.online = True

        return True


# 71-209
