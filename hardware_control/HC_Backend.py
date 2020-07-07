from abc import ABC
from functools import wraps
import inspect
import time
import threading

import pyvisa
import socket
from pymodbus.client.sync import ModbusTcpClient as ModbusClient

from colorama import Fore, Style
import logging
from hardware_control.utility import regex_compare

logger = logging.getLogger(__name__)

VISA = "visa"
SOCKET = "socket"
MODBUS = "modbus"


def thread_info(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        self = args[0]
        start = time.time()

        frame = inspect.currentframe()
        retval = f(*args, **kwargs)
        end = time.time()
        print(
            f"Function: {inspect.getframeinfo(frame).function}, start: {start}, end: {end}, thread: {threading.get_ident()} dt: {start-end}"
        )
        inspect.getframeinfo(frame).function
        print(
            "Function: %-20.20s thread: %17.17d dt: %15f"
            % (inspect.stack()[1][3], threading.get_ident(), end - start)
        )
        return retval

    return wrapped


def ensure_online(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        self = args[0]

        if not self.online:
            return f"{self.ID}-Offline"

        return f(*args, **kwargs)

    return wrapped


class HC_Backend(ABC):
    """Base class for all instruments"""

    # @thread_info
    def __init__(self):

        self.ID = None  # this should be a string with instrument name
        self.online = False  # does a connection to the instrument exist?

        self.device = None  # This is the physical instrument to write to
        self.dummy = False

        self.connection_addr = None
        self.connection_type = None
        self.port_no = None
        self.ip_addr = None
        self.termination = "\n"

    def parse_connection_addr(self):

        if (
            self.connection_addr.startswith("ASRL")
            or self.connection_addr.startswith("GPIB")
            or self.connection_addr.startswith("PXI")
            or self.connection_addr.startswith("VISA")
            or self.connection_addr.startswith("TCPIP")
            or self.connection_addr.startswith("USB")
            or self.connection_addr.startswith("VXI")
        ):
            self.connection_type = VISA
        else:
            self.connection_type = SOCKET
            try:
                self.ip_addr, self.port_no = self.connection_addr.rsplit(":", 1)
                self.port_no = int(self.port_no)
            except ValueError as e:
                logger.error(
                    f"{self.ID} cannot parse connection address {self.connection_addr}"
                )
                self.ip_addr = self.connection_addr
                self.port_no = None

    # @thread_info
    def check(self):
        """Some error checking

        to be called at the end of __init__ in the instrument

        """
        if self.connection_type not in [VISA, SOCKET, MODBUS]:
            logger.error(
                f"The connection type {self.connection_type}" + " is not supported"
            )
        if self.ID is None:
            logger.error(f"Need to set the instrument ID")

    # @thread_info
    def update_setting(self, setting: str, value: str):
        """Overload this function to adjust settings on the device. Must return
        a string (which HC_CommWorker will send back to the main thread)"""
        return value

    # @thread_info
    def command(self, cmd: str):
        """Overload this function to send commands to the device. Must return
        a string (which HC_CommWorker will send back to the main thread)"""
        return cmd

    # @thread_info
    def command_listdata(self, cmd: str):
        """Overload this function to send commands to the device. Must return
        a tuple with an str, list, and list (which HC_CommWorker will send back
         to the main thread)"""
        return "", [], []

    # @thread_info
    def close(self):
        """Close connection to instrument"""

        if self.dummy:
            logger.debug(f"{self.ID}: Dummy connection closed")
            return False

        if self.device is None:
            logger.debug(f"{self.ID}: Called close with not device defined")
            return False

        self.device.close()

    # @thread_info
    def try_connect(self):
        """Checks if the backend is in communication with the object, if it is
        not, it tries to re-establish communication."""

        if self.dummy:
            if self.online:
                return True
            else:
                logger.debug(
                    f"{self.ID}: creating dummy connection"
                    + f" to {self.connection_addr}"
                )
                self.online = True
                return True

        if self.online:
            return True  # Todo: Add check_connection() here?

        logger.debug(f"{self.ID}: trying to connect")

        # Try to connect to instrument
        if self.connection_type == VISA:
            try:
                rm = pyvisa.ResourceManager("@py")
                self.device = rm.open_resource(self.connection_addr)
                self.device.read_termination = self.termination
                logger.debug(
                    f"opened pyvisa connection to {self.ID} at {self.connection_addr}"
                )
            except Exception as e:
                self.online = False
                logger.debug(
                    f"\t({self.ID}) ERROR connecting with visa.", exc_info=True
                )
                logger.debug(f"{self.ID} is offline")
            else:
                self.online = True
        elif self.connection_type == SOCKET:
            try:
                self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.device.settimeout(2)
                self.device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                self.device.connect((self.ip_addr, int(self.port_no)))

                logger.debug(
                    f"opened socket connection to {self.ID} at {self.ip_addr}:{self.port_no}"
                )
            except Exception as e:
                self.online = False
                logger.debug(
                    f"\t({self.ID}) ERROR connecting with sockets.", exc_info=True
                )
                logger.debug(f"{self.ID} is offline")
            else:
                self.online = True
        elif self.connection_type == MODBUS:
            try:
                self.device = ModbusClient(host=self.connection_addr)
                if self.device.connect(self.connection_addr):
                    self.online = True
                    logger.debug(
                        f"opened modbus connection to {self.ID} at {self.connection_addr}"
                    )
            except Exception as e:
                self.online = False
                logger.debug(
                    f"\t({self.ID}) ERROR connecting with modbus.", exc_info=True
                )
                logger.debug(f"{self.ID} is offline")

        # If connection purportedly successful, verify connection
        if self.online == True:
            if self.check_connection() == False:
                self.online = False

        return self.online

    # @thread_info
    def check_connection(self):
        """
        This function should be overwritten by each backend. It will verify
        that the instrument is actually connected by querying something from the
        instrument such as the instrument's model number or ID.

        Return True if connected, False if not connected, None if not implimented
        """

        return None

    # @thread_info
    @ensure_online
    def write(self, command: str):

        if self.dummy:
            return command

        try:
            logger.debug(f'\t{self.ID} < "{command}"')
            if self.connection_type == VISA:
                self.device.write(command)
                return command
            elif self.connection_type == SOCKET:
                self.device.sendall(bytes(command + "\n", "utf-8"))
                return command
        except Exception:
            logger.debug(f"ERROR: Write {command} failed in {self.ID}", exc_info=True)
            self.online = False
            return f"{self.ID}-Offline"

    # @thread_info
    @staticmethod
    def recvall(sock):
        BUFF_SIZE = 4096  # 4 KiB
        data = b""
        while True:
            part = sock.recv(BUFF_SIZE)
            data += part
            t_str = str(part)
            if t_str[len(t_str) - 3 : len(t_str) - 1] == "\\n":
                break
        return data

    # @thread_info
    @ensure_online
    def query(self, command: str):

        if self.dummy:
            return command

        try:
            logger.debug(f"INFO: Sending query {command} in {self.ID}")
            if self.connection_type == VISA:
                reply = self.device.query(command)
            elif self.connection_type == SOCKET:
                self.device.sendall(bytes(command + self.termination, "utf-8"))
                reply_bytes = HC_Backend.recvall(self.device)
                reply = str(reply_bytes)
                reply = reply[2 : len(reply) - 3]
                logger.debug(f'\t{self.ID}< "{command}"')
            return reply
        except Exception:
            logger.debug(f"ERROR: Query {command} failed in {self.ID}", exc_info=True)
            self.online = False
            return f"{self.ID}-Offline"


def get_channel_from_command(command: str):
    """
    Processes a command from the front end and returns a tuple with:
        1.) channel number
        2.) original command with all channel numbers replaced by a single 'X'
    If the channel is not specified, the channel number is returned as 'None'
    and the original command is returned without any replacements.

    The channel is specified by writing CH#_
    """

    # Check command length
    if len(command) < 3:
        return None, command

    # Check 'CH' specifier comes first
    if command[:2] != "CH":
        return None, command

    # Find end of channel number
    idx_underscore = command.find("_")
    if idx_underscore == -1:
        return None, command

    # Get channel number
    try:
        chan = int(command[2:idx_underscore])
    except Exception as e:
        chan = command[2:idx_underscore]

    # overwrite channel number for easier comparison
    command_X = command[:2] + "X" + command[idx_underscore:]

    return chan, command_X
