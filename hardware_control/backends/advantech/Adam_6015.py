"""Advantac ADAM 6015 (4 thermo couple readouts)

.. image:: /images/ADAM-6015.jpg
  :height: 200

See class definition for details.

"""

import logging
import random
import socket

from ..base import Backend
from ..utility import get_channel_from_command

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
        self.termination = "\r"
        self.encoding = "ascii"

        if self.connection_type != Backend.SOCKET:
            logger.error(
                "Wrong instrument address. Needs to be socket type (ip or ip:port)."
            )

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

    def command(self, cmd: str):
        """Query the temperature of a channel.

        Use Convention "CH<#>_TEMP?".

        This will query all channels,
        the answer is like >+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000
        and then pick out the correct channel

        """

        if self.dummy:
            return cmd[:-1] + "=" + str(random.randint(0, 10000) / 10)

        if self.online:
            channel, cmd_X = get_channel_from_command(cmd)

            if channel < 0 or channel > 7:
                logger.error("Wrong channel number")
                return "Unexpected Command"

            try:
                self.device.sendall(b"#01\r")

                indata = self.device.recv(self.buf)
                # cut off ">"
                data = indata.decode("ascii")[1:]
                data = data[channel * 10 : channel * 10 + 10]
                return f"CH{channel}_TEMP={data}"
            except:
                logger.error(
                    self.ID + " online status : " + str(self.try_connect()),
                    exc_info=True,
                )
                return "Unexpected Command"

    def update_setting(self, setting: str, value: str):
        """Device has no Settings"""
        pass
