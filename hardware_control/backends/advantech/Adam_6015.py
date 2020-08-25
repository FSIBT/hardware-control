"""Advantac ADAM 6015 (4 thermo couple readouts)

.. image:: /images/ADAM-6015.jpg
  :height: 200

See class definition for details.

"""

import logging
import random
import socket

from ..base import Backend
from ..utility import regex_compare

logger = logging.getLogger(__name__)


class Adam_6015(Backend):
    """A driver for the Adam 6015.

    Instrument home page: https://www.advantech.com/products/a67f7853-013a-4b50-9b20-01798c56b090/adam-6015/mod_9c835a28-5c91-49fc-9de1-ec7f1dd3a82d

    """

    def __init__(self, connection_addr):

        super().__init__(
            instrument_name="Advantac_ADAM-6015",
            connection_addr=connection_addr,
            default_port=1025,
        )

        self.buf = 200
        self.addr = (self.ip_addr, self.port_no)

        self.try_connect()

    def try_connect(self):
        """Force the use of sockets with different option (DGRAM instead of STREAM)."""
        if self.dummy:
            if not self.online:
                logger.debug(f"Adam: creating dummy connection to {self.addr}")
            self.online = True
            return self.online

        # First Check current state
        if not self.online:  # If not online, try to connect
            try:
                self.device = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.device.settimeout(0.950)
                self.device.connect(self.addr)
                logger.debug(
                    f"opened socket connection to {self.ID} at"
                    f" {self.ip_addr}:{self.port_no}"
                )
            except:
                logger.debug("exception during try connect", exc_info=True)
                self.online = False
                return self.online

        # Independent of the state, try to receive data, if nothing is
        # returned, then the device is offline
        self.online = self.check_connection()

    def close(self):
        """this is a override - sockets are used"""
        if not self.dummy:
            self.socket.close()
        else:
            logger.debug("Adam: close dummy connection")
        return False

    def write(self, msg: str):
        """this is a override - sockets are used"""
        if not self.dummy:
            msg = msg + "\r"
            self.socket.send(msg.encode("ascii"))
            indata = self.socket.recv(self.buf)
            data = indata.decode("ascii")[1:-1]
            return data

    def read(self):
        """Read values from Adam"""
        """this is a override - sockets are used"""
        if not self.dummy:
            self.socket.send(b"#01\r")
            indata = self.socket.recv(self.buf)
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
                    self.socket.send(out.encode("ascii"))
                    indata = self.socket.recv(self.buf)
                    data = indata.decode("ascii")[1:]  # cut off ">"
                    n = int(cmd[2])
                    data = data[n * 10 : n * 10 + 10]
                    return "CH" + str(n) + "_TEMP=" + data
                else:
                    return "Unexpected Command"
            except Exception:
                logger.error(
                    self.ID + " online status : " + str(self.try_connect()),
                    exc_info=True,
                )

    def update_setting(self, setting: str, value: str):
        """Device has no Settings"""
        pass
