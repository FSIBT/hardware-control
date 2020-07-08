"""

"""

import logging
import random
import socket

from hardware_control.HC_Backend import HC_Backend, ensure_online
from hardware_control.utility import ensure_float

logger = logging.getLogger(__name__)


class ADAM6024Ctrl(HC_Backend):
    """Control of Adam input/output module"""

    def __init__(self, connection_addr):

        super().__init__()

        self.online = False
        self.ID = "Advantac_ADAM-6025"
        self.buf = 200
        self.connection_addr = connection_addr

        self.parse_connection_addr()

        # This specifies the max number of channels the user can request
        self.num_ichannels = 8
        self.num_ochannels = 4

        self.values = {"CH1_V_meas": [], "CH2_V_meas": [], "CH3_V_meas": []}

        # Min/max voltages output supports
        self.out_min = 0
        self.out_max = 10

        self.addr = (self.ip_addr, self.port_no)

        self.termination = "\r"
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
                logger.debug(f"exception during try connect", exc_info=True)
                self.online = False
                return self.online

        # Independent of the state, try to receive data, if nothing is returned, then the device is offline
        try:
            self.device.send(b"#01\r")
            indata = self.device.recv(self.buf)
            self.online = True
            return self.online
        except:
            self.online = False
            return self.online

    @ensure_online
    def update_setting(self, setting: str, value):

        if self.dummy:
            return value

        if len(setting) >= 3:
            channel = int(setting[2])

        # overwrite channel number for easier comparison
        setting_X = setting[:2] + "X" + setting[3:]

        value = ensure_float(value)

        if setting_X == "CHX_analog_write":

            if value < self.out_min or value > self.out_max:
                return "Error: value out of bounds"

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
