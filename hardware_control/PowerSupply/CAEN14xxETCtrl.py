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


class CAEN14xxETCtrl(HC_Backend):
    def __init__(
        self,
        visa_addr,
        dummy: bool = False,
        debug: bool = False,
        use_sockets: bool = False,
        ip_addr: str = "",
        port_no=5025,
    ):

        super().__init__()

        self.ID = "TDKL-GenH"

        self.visa_addr = visa_addr
        self.online = False
        self.dummy = dummy
        self.debug = debug

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
                self.device.query("$BD:00,CMD:MON,PAR:BDNAME")
            except visa.errors.VisaIOError as e:  # Not connected - reconnect
                if self.debug:
                    print("Lost connection to device. Will try to reconnect")
                    print(f"\t{str(e)}")
            else:  # Connection stable - return True
                return True

        if self.debug:
            print("trying to connect")

        # Try to connect to instrument
        try:
            if not self.use_sockets:  # Use visa
                rm = visa.ResousrceManager("@py")
                self.device = rm.open_resource(self.visa_addr)  # Open connection
                self.device.read_termination = "\r\n"
                self.device.write_termination = "\r\n"

                # Verify actually connected (open_resource won't always throw error w/ disconnected USB)
                self.device.query("$BD:00,CMD:MON,PAR:BDNAME")
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

        if not self.online:
            return "Offline"

        try:
            if self.dummy:
                return value
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of PSU
                if regex_compare("CH._enable", setting):

                    c = setting[2]
                    if str_to_bool(value):
                        self.query(f"$BD:00,CMD:SET,CH:{c},PAR:ON")
                    else:
                        self.query(f"$BD:00,CMD:SET,CH:{c},PAR:OFF")
                    status = self.read_status(c)

                    if status is None:
                        return "None"
                    return str(bool(status["on_off"]))

                elif regex_compare("CH._I_set", setting):

                    c = setting[2]
                    self.query(f"$BD:00,CMD:SET,CH:{c},PAR:ISET,VAL:{value}")
                    result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:ISET")

                    if result is None:
                        return "None"
                    return result[-7:]

                elif regex_compare("CH._V_set", setting):

                    c = setting[2]
                    self.query(f"$BD:00,CMD:SET,CH:{c},PAR:VSET,VAL:{value}")
                    result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:VSET")

                    if result is None:
                        return "None"
                    return result[-6:]

        except Exception as e:
            print(
                "An error occured in CAEN14xxETCtrl.py when sending SCPI commands to the instrument."
            )
            print(f"\t{str(e)}")
            print(f"\t{setting}, {value}")

    def command(self, cmd: str):

        if not self.online:
            return "Offline"

        try:
            if self.dummy:
                return cmd
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of PSU
                if regex_compare("CH._V_out?", cmd):  # Get CHx V out

                    c = cmd[2]
                    result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:VMON")

                    if result is None:
                        return "None"
                    rval = result[-6:]

                    return f"{cmd}={rval}"

                elif regex_compare("CH._I_out?", cmd):  # Get CHx I out

                    c = cmd[2]
                    result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:IMON")

                    if result is None:
                        return "None"
                    rval = result[-7:]

                    return f"{cmd}={rval}"

                elif regex_compare("CH._I_set", cmd):  # Get CHx I setpoint

                    c = cmd[2]
                    result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:ISET")

                    if result is None:
                        return "None"
                    rval = result[-6:]

                    return f"{cmd}={rval}"

                elif regex_compare("CH._V_set", cmd):  # Get CHx V setpoint

                    c = cmd[2]
                    result = self.query(f"$BD:00,CMD:MON,CH:{c},PAR:VSET")

                    if result is None:
                        return "None"
                    rval = result[-6:]

                    return f"{cmd}={rval}"

        except Exception as e:
            print(
                "An error occured in CAEN14xxETCtrl.py when sending SCPI commands to the instrument."
            )
            print(str(e))

    def read_status(self, channel):
        """See table on page 24 of manual"""
        if self.dummy:
            outputs = [1 + 128 + 1024, 128, 1, 1024]
            value = random.choice(outputs)
        else:
            result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:STAT")
            if result is None:
                return None
            value = int(result[-5:])

        status = {
            "on_off": value & 1,
            "ramping_up": value & 2,
            "ramping_down": value & 4,
            "over_current": value & 8,
            "over_voltage": value & 16,
            "under_voltage": value & 32,
            "max_voltage": value & 64,
            "tripped": value & 128,
            "over_power": value & 256,
            "over_temperature": value & 512,
            "disabled": value & 1024,
            "kill": value & 2048,
            "interlocked": value & 4096,
            "calibration_error": value & 8192,
        }
        return status
