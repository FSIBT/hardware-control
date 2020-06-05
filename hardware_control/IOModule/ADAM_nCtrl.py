"""
This is a device for reading Temperatures
It receives a string "CH#_TEMP?"
There are no settings to be set
"""

import random
import re
import socket

from hardware_control.HC_Backend import HC_Backend, ensure_online
from hardware_control.utility import regex_compare
import logging

logger = logging.getLogger(__name__)


class ADAM_nCtrl(HC_Backend):
    """Control of Adam input/output module"""

    def __init__(self, connection_addr="192.168.1.25:1025"):

        super().__init__()

        self.online = False
        self.ID = "Advantac_ADAM-6015"
        self.buf = 200
        self.connection_addr = connection_addr

        self.parse_connection_addr()

        # This specifies the max number of channels the user can request
        self.num_ichannels = 3
        self.num_ochannels = 1

        # Min/max voltages output supports
        self.out_min = 0
        self.out_max = 10

        self.addr = (self.ip_addr, self.port_no)

        self.try_connect()

    def try_connect(self):
        """this is a override - sockets are used"""
        if not self.dummy:
            # First Check current state
            if not self.online:  # If not online, try to connect
                try:
                    self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.s.settimeout(0.950)
                    self.s.connect(self.addr)
                    logger.debug(f"opened socket connection to {self.ID} at {self.ip_addr}:{self.port_no}")
                except:
                    logger.debug(f"exception during try connect", exc_info=True)
                    self.online = False
                    return self.online

            # Independent of the state, try to receive data, if nothing is returned, then the device is offline
            try:
                self.s.send("#01\r".encode("ascii"))
                indata = self.s.recv(self.buf)
                self.online = True
                return self.online
            except:
                self.online = False
                return self.online
        else:
            if not self.online:
                logger.debug(f"Adam: creating dummy connection to {self.addr}")
            self.online = True
            return self.online

    ##########################

    @ensure_online
    def update_setting(self, setting: str, value):

        if self.dummy:
            return value

        if len(setting) >= 3:
            channel = int(setting[2])

        # overwrite channel number for easier comparison
        setting_X = setting[:2] + "X" + setting[3:]

        value = ensure_float(value)

        if setting_X == "CHX_V_set":

            if value < self.out_min or value > self.out_max:
                return "Error: value out of bounds"

            cmd = f"#01{channel:02d}{value:06.3f}\r"

            if not self.dummy:
                logger.debug(f"{self.ID} sending command {cmd} at {self.ip_addr}:{self.port_no}")
                self.s.sendto(cmd.encode("ascii"), self.addr)
                indata, inaddr = self.s.recvfrom(self.buf)
                output = indata.decode("ascii")
                if output == "?01\r":
                    print("Adam: Last command invalid")
                    return "Error: Invalid command sent to ADAM"
                if output == ">\r":
                    return str(value)
            else:
                logger.info(f"Adam: send {cmd}")
                return str(value)

            return "Error: unrecognized response from ADAM"

    @ensure_online
    def command(self, cmd: str):

        if self.dummy:
            num = random.random() * 10
            return f"{cmd.strip('?')}={num}"

        channel = int(cmd[2])

        # overwrite channel number for easier comparison
        cmd_X = cmd[:2] + "X" + cmd[3:]

        if cmd_X == "CHX_V_meas?":

            # Read all data
            data = self.query("#01\r")
            # the data comes as one string with 7 bytes for each value
            # 1 byte: +- sign
            # 2 digits decimalpoint 3 digits
            # there is no space or separator between data points
            try:
                start_idx = (channel - 1) * 7
                end_idx = channel * 7
                rval = float(data[start_idx:end_idx])
            except ValueError:
                rval = 0
                logger.error(
                    f"Adam: Error in read values: p={data[0:7]} I={data[7:14]} V={data[14:21]}"
                )
        else:
            rval = "Error"
            logger.error(
                f"Adam: unkonwn command {cmd}"
            )

        # remove question mark in cmd
        return f"{cmd[:-1]}={rval}"

    ##########################

    def close(self):
        """this is a override - sockets are used"""
        if not self.dummy:
            self.s.close()
        else:
            logger.debug("Adam: close dummy connection")
        return False

    def query(self, msg: str):
        """this is a override - sockets are used"""
        if not self.dummy:
            if not msg.endswith("\r"):
                msg = msg + "\r"
            self.s.send(msg.encode("ascii"))
            indata = self.s.recv(self.buf)
            data = indata.decode("ascii")[1:-1]
            return data

    # def read(self):
    #     """Read values from Adam"""
    #     """this is a override - sockets are used"""
    #     if not self.dummy:
    #         self.s.send("#01\r".encode("ascii"))
    #         indata = self.s.recv(self.buf)
    #         data = indata.decode("ascii")
    #     else:
    #         # Just a random answer it once received
    #         data = ">+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000"
    #     return data

    # def command(self, cmd: str):
    #     """Use Convention "CH#_TEMP?"  the answer is like >+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000 """
    #     if self.dummy:
    #         d = cmd[:-1] + "=" + str(random.randint(0, 10000) / 10)
    #         return d
    #     if self.online:
    #         try:
    #             if regex_compare("CH._TEMP?", cmd) and int(cmd[2]) in range(0, 7):
    #                 # cmd[2] equals the channel#
    #                 out = "#01\r"  # simply asks for all channels
    #                 self.s.send(out.encode("ascii"))
    #                 indata = self.s.recv(self.buf)
    #                 data = indata.decode("ascii")[1:]  # cut off ">"
    #                 n = int(cmd[2])
    #                 data = data[n * 10 : n * 10 + 10]
    #                 return "CH" + str(n) + "_TEMP=" + data
    #             else:
    #                 return "Unexpected Command"
    #         except Exception as e:
    #             logger.error(
    #                 self.ID + " online status : " + str(self.try_connect()),
    #                 exc_info=True,
    #             )
    #
    # def update_setting(self, setting: str, value: str):
    #     """Device has no Settings"""
    #     pass
