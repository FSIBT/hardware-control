"""Base class and helper function for implementing an instrument backend.

A backend for an instrument will run in its own thread. It should have
no Qt references, so that it can also be used in command line apps.

Several default connections modes are supported out of the box:
pyvisa, sockets, and modbus.

For other communications protocles, the user needs to overwrite the
connect function.

"""


import abc
from functools import wraps
import inspect
import logging
import socket
import time
import threading

import pyvisa
from pymodbus.client.sync import ModbusTcpClient as ModbusClient


logger = logging.getLogger(__name__)


def thread_info(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        start = time.time()

        frame = inspect.currentframe()
        retval = f(*args, **kwargs)
        end = time.time()
        print(
            f"Function: {inspect.getframeinfo(frame).function},"
            f" start: {start}, end: {end}, thread: {threading.get_ident()} dt: {start-end}"
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


class Backend(abc.ABC):
    """Base class for all instruments.

    This class should be inherited for every instrument backend.

    The backend implements the actual communications between python
    and the instrument.

    The class supports several connections modes out of the box:
    pyvisa, sockets, and modbus

    For other type of communictioan the try_connect function needs to
    be overwritten.

    When implementing a backend the abstracmethods need to be
    implemented: update_setting, command, and check_connection.

    """

    # class variables for the different supported connection types
    VISA = "visa"
    SOCKET = "socket"
    MODBUS = "modbus"

    SUPPORTED_CONNECTION_TYPES = [VISA, SOCKET, MODBUS]

    def __init__(
        self, instrument_name: str, connection_addr: str, default_port: int = None
    ):

        self.ID = instrument_name
        self.online = False  # does a connection to the instrument exist?

        self.device = None  # This is the physical instrument to write to
        self.dummy = False

        self.connection_addr = connection_addr
        self.connection_type = None

        self.ip_addr = None
        self.port_no = default_port
        self.termination = "\n"
        self.encoding = "utf-8"

        # This can be set to a single command or list of commands
        # which will enable automatic checks using these commands to
        # see if the instrument is still online. For more complicated
        # checks, the user can also overwite check_connections()
        self.check_connection_commands = None

        self.parse_connection_addr()

    def parse_connection_addr(self):
        """Figures out if pyvisa or other methods should be used.

        Currently pyvisa addresses are automatically recognised,
        everything else is assumed to be in the form of either just an
        IP address or an IP address and a port number seperated by a
        ":".  For this case sockets are automatically assumed. If
        modbus should be used, the user needs to overwrite this in the
        init function of the backend.

        """

        if (
            self.connection_addr.startswith("ASRL")
            or self.connection_addr.startswith("GPIB")
            or self.connection_addr.startswith("PXI")
            or self.connection_addr.startswith("VISA")
            or self.connection_addr.startswith("TCPIP")
            or self.connection_addr.startswith("USB")
            or self.connection_addr.startswith("VXI")
        ):
            self.connection_type = Backend.VISA
        else:
            self.connection_type = Backend.SOCKET
            values = self.connection_addr.rsplit(":", 1)
            if len(values) == 1:
                self.ip_addr = values[0]
            elif len(values) == 2:
                self.ip_addr, self.port_no = values
            self.port_no = int(self.port_no)

    def check_connection(self):
        """Test if the instrument is reachable.

        The functions checks `self.check_connection_commands` and runs
        those commands or if `None it will skip any tests.`

        Returns
        -------
        bool
           True if the instrument is reachable or no test have been done, False if not.

        """

        if not self.online:
            return False

        if self.check_connection_commands is None:
            return True
        if isinstance(self.check_connection_commands, str):
            self.query(self.check_connection_commands)
            return self.online
        if isinstance(self.check_connection_commands, (list, tuple)):
            for cmd in self.check_connection_commands:
                self.query(cmd)
            return self.online

    @abc.abstractmethod
    def update_setting(self, setting: str, value: str) -> str:
        """Overload this function to adjust settings on the device.


        Returns
        -------
        Must return a string (which hc.CommWorker will send back to
        the main thread)

        """
        pass

    @abc.abstractmethod
    def command(self, cmd: str) -> str:
        """Overload this function to send commands to the device.

        Returns
        -------
        Must return a string (which hc.CommWorker will send back to
        the main thread)

        """
        pass

    def command_listdata(self, cmd: str):
        """Overload this function to send commands to the device.

        Returns
        -------

        Must return a tuple with an str, list, and list (which
        hc.CommWorker will send back to the main thread)

        """
        return "", [], []

    def close(self):
        """Close connection to instrument."""

        if self.dummy:
            logger.debug(f"{self.ID}: Dummy connection closed")
            return False

        if self.device is None:
            logger.debug(f"{self.ID}: Called close with not device defined")
            return False

        self.device.close()

    def try_connect(self):
        """Checks if the backend is in communication with the object, if it is
        not, it tries to re-establish communication."""

        if self.dummy:
            if self.online:
                return True
            logger.debug(
                f"{self.ID}: creating dummy connection to {self.connection_addr}"
            )
            self.online = True
            return True

        if self.online:
            if self.check_connection():
                return True
            self.online = False

        logger.debug(f"{self.ID}: trying to connect")

        if self.connection_type == Backend.VISA:
            try:
                rm = pyvisa.ResourceManager("@py")
                self.device = rm.open_resource(self.connection_addr)
                self.device.read_termination = self.termination
                self.device.write_termination = self.termination
                logger.debug(
                    f"opened pyvisa connection to {self.ID} at {self.connection_addr}"
                )
            except Exception:
                self.online = False
                logger.debug(f"\t({self.ID}) ERROR connecting with visa.",)
                logger.debug(f"{self.ID} is offline")
            else:
                self.online = True
        elif self.connection_type == Backend.SOCKET:
            try:
                self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.device.settimeout(2)
                self.device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                self.device.connect((self.ip_addr, int(self.port_no)))

                logger.debug(
                    f"opened socket connection to {self.ID} at {self.ip_addr}:{self.port_no}"
                )
            except Exception:
                self.online = False
                logger.debug(f"\t({self.ID}) ERROR connecting with sockets.")
                logger.debug(f"{self.ID} is offline")
            else:
                self.online = True
        elif self.connection_type == Backend.MODBUS:
            try:
                self.device = ModbusClient(host=self.connection_addr)
                if self.device.connect():
                    self.online = True
                    logger.debug(
                        f"opened modbus connection to {self.ID} at {self.connection_addr}"
                    )
            except Exception:
                self.online = False
                logger.debug(f"\t({self.ID}) ERROR connecting with modbus.")
                logger.debug(f"{self.ID} is offline")

        # If connection purportedly successful, verify connection
        if self.online:
            if not self.check_connection():
                self.online = False

        return self.online

    # @thread_info
    @ensure_online
    def write(self, command: str):

        if self.dummy:
            return command

        try:
            logger.debug(f'\t{self.ID} < "{command}"')
            if self.connection_type == Backend.VISA:
                self.device.write(command)
                return command
            if self.connection_type == Backend.SOCKET:
                self.device.sendall(bytes(command + self.termination, self.encoding))
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
            if self.connection_type == Backend.VISA:
                reply = self.device.query(command)
            elif self.connection_type == Backend.SOCKET:
                self.device.sendall(bytes(command + self.termination, self.encoding))
                reply_bytes = Backend.recvall(self.device)
                reply = str(reply_bytes)
                reply = reply[2 : len(reply) - 3]
                logger.debug(f'\t{self.ID}< "{command}"')
            return reply
        except Exception:
            logger.debug(f"ERROR: Query {command} failed in {self.ID}", exc_info=True)
            self.online = False
            return f"{self.ID}-Offline"
