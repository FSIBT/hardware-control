"""Advantac ADAM 6024

.. image:: /images/ADAM-6024.jpg
  :height: 200

See class definition for details.

"""

import logging
import random
import socket

from ..base import Backend, ensure_online
from ..utility import ensure_float, get_channel_from_command

logger = logging.getLogger(__name__)


class Adam_6024(Backend):
    """A driver for the Adam 6024 input/output module.

    Instrument home page: https://www.advantech.com/products/a67f7853-013a-4b50-9b20-01798c56b090/adam-6024/mod_99d243cd-2f38-48a3-a82c-eeb5e0f4e278

    """

    def __init__(self, connection_addr):
        super().__init__(
            instrument_name="Advantac_ADAM-6025",
            connection_addr=connection_addr,
            default_port=1025,
        )

        self.buf = 200

        # This specifies the max number of channels the user can request
        self.num_ichannels = 8
        self.num_ochannels = 4

        self.values = {"CH1_V_meas": [], "CH2_V_meas": [], "CH3_V_meas": []}

        # Min/max voltages output supports
        self.out_min = 0
        self.out_max = 10

        self.addr = (self.ip_addr, self.port_no)
        self.termination = "\r"

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
                    f"opened socket connection to {self.ID} at {self.ip_addr}:{self.port_no}"
                )
            except:
                logger.debug("exception during try connect", exc_info=True)
                self.online = False
                return self.online

        # Independent of the state, try to receive data, if nothing is returned, then the device is offline
        self.online = self.check_connection()

    @ensure_online
    def update_setting(self, setting: str, value):

        if self.dummy:
            return value

        channel, setting_X = get_channel_from_command(setting)

        value = ensure_float(value)

        if setting_X == "CHX_analog_write":

            if value < self.out_min or value > self.out_max:
                logging.error("Error: value out of bounds")
                return "value out of bound"

            cmd = f"#01{channel:02d}{value:06.3f}\r"

            if not self.dummy:
                logger.debug(
                    f"{self.ID} sending command {cmd} at {self.ip_addr}:{self.port_no}"
                )
                self.device.sendto(cmd.encode("ascii"), self.addr)
                indata, inaddr = self.device.recvfrom(self.buf)
                output = indata.decode("ascii")
                if output == "?01\r":
                    print("Adam: Last command invalid")
                    return "Error: Invalid command sent to ADAM"
                if output == ">\r":
                    return f"{setting}={value}"
            else:
                logger.info(f"Adam: send {cmd}")
                return f"{setting}={value}"

            logger.error(
                f"{self.ID} trying to set unknown {setting} to {value} at {self.ip_addr}:{self.port_no}"
            )
            return "Error: unrecognized response from ADAM"

    @ensure_online
    def command(self, cmd: str):

        if self.dummy:
            num = random.random() * 10
            return f"{cmd.strip('?')}={num}"

        channel, cmd_X = get_channel_from_command(cmd)
        channel = int(channel[1])

        if cmd_X == "CHX_analog_read?":  # Read a voltage

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
            logger.error(f"Adam: unkonwn command {cmd}")

        # remove question mark in cmd
        return f"{cmd[:-1]}={rval}"

    def query(self, msg: str):
        """This is a override - sockets are used"""
        if not self.dummy:
            if not msg.endswith("\r"):
                msg = msg + "\r"
            self.device.send(msg.encode("ascii"))
            indata = self.device.recv(self.buf)
            data = indata.decode("ascii")[1:-1]
            return data
