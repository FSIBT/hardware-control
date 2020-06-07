"""
This is a device for reading Temperatures
It receives a string "CH#_TEMP?"
There are no settings to be set
"""

import random
import re
import socket

from hardware_control.HC_Backend import HC_Backend
from hardware_control.utility import regex_compare
import logging

logger = logging.getLogger(__name__)


class Adam_6015(HC_Backend):
    """Control of Adam input/output module"""

    def __init__(self, connection_addr="192.168.1.25:1025"):

        super().__init__()

        self.online = False
        self.ID = "Advantac_ADAM-6015"
        self.buf = 200
        self.connection_addr = connection_addr

        self.parse_connection_addr()

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
                except:
                    self.online = False
                    return self.online

            # Independent of the state, try to receive data, if nothing is returned, then the device is offline
            try:
                self.s.send(b"#01\r")
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

    def close(self):
        """this is a override - sockets are used"""
        if not self.dummy:
            self.s.close()
        else:
            logger.debug("Adam: close dummy connection")
        return False

    def write(self, msg: str):
        """this is a override - sockets are used"""
        if not self.dummy:
            msg = msg + "\r"
            self.s.send(msg.encode("ascii"))
            indata = self.s.recv(self.buf)
            data = indata.decode("ascii")[1:-1]
            return data

    def read(self):
        """Read values from Adam"""
        """this is a override - sockets are used"""
        if not self.dummy:
            self.s.send(b"#01\r")
            indata = self.s.recv(self.buf)
            data = indata.decode("ascii")
        else:
            # Just a random answer it once received
            data = ">+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000"
        return data

    def command(self, cmd: str):
        """Use Convention "CH#_TEMP?"  the answer is like >+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000 """
        if self.dummy:
            d = cmd[:-1] + "=" + str(random.randint(0, 10000) / 10)
            return d
        if self.online:
            try:
                if regex_compare("CH._TEMP?", cmd) and int(cmd[2]) in range(0, 7):
                    # cmd[2] equals the channel#
                    out = "#01\r"  # simply asks for all channels
                    self.s.send(out.encode("ascii"))
                    indata = self.s.recv(self.buf)
                    data = indata.decode("ascii")[1:]  # cut off ">"
                    n = int(cmd[2])
                    data = data[n * 10 : n * 10 + 10]
                    return "CH" + str(n) + "_TEMP=" + data
                else:
                    return "Unexpected Command"
            except Exception as e:
                logger.error(
                    self.ID + " online status : " + str(self.try_connect()),
                    exc_info=True,
                )

    def update_setting(self, setting: str, value: str):
        """Device has no Settings"""
        pass
