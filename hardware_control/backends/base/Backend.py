"""Base class and helper function for implementing an instrument backend.

A backend for an instrument should be kept very basic, so that one can
use it in a terminal for example. A backend should not have any GUI
elements and therefore no references to Qt.

Hardware control will automatically start each backend in its own
thread, see the ZMQ adapter class.

Several default connections modes are supported out of the box:
pyvisa, sockets, and modbus.

For other communications protocles, the user needs to overwrite the
connect function.

"""


from functools import wraps
import logging
import socket
from typing import Optional, Any

import pyvisa
from pymodbus.client.sync import ModbusTcpClient as ModbusClient


logger = logging.getLogger(__name__)


def ensure_online(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        self = args[0]

        if not self.online:
            return f"{self.ID}-Offline"

        return f(*args, **kwargs)

    return wrapped


class Backend:
    """Base class for all physical instruments.

    The backend implements the actual communications between python
    and the instrument.

    The class supports several connections modes out of the box:
    pyvisa, sockets, and modbus

    For other type of communictioan the try_connect function needs to
    be overwritten.

    When implementing a backend, the user inherits from this base class
    and then calls add_parameter and add_command several times. These
    commands define 'read only' or 'read and write' parameters, for
    example, voltage settings or just basic commands, such as,
    'trigger' and links these to the actual hardware command that
    needs to be send to the instrument.

    We also overwrite __getitem__, __getattr__ and the corresponding set functions to
    allow for a more pythonic way of reading and writing these parameters.

    An instrument can also be in `dummy` mode. Here, python will not
    try to connect to the instrument and return pre-defined data or
    call a user-defined function to generate the return value. This
    can be handy for creating and debugging an app when one doesn't
    have access to the hardware.

    Attributes
    ----------
    online : bool
         status of the instrument
    dummy : bool
         are we in dummy mode (no commands are send to the instrument) or normal mode

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
        self.online: bool = False

        self.device = None  # This is the physical instrument to write to
        self.dummy: bool = False

        self.connection_addr = connection_addr
        self.connection_type = None

        self.ip_addr = None
        self.port_no = default_port
        self.termination: str = "\n"
        self.encoding: str = "utf-8"

        # We save all possible commands and settings in several dictionaries
        self.set_commands = {}  # e.g. a voltage that can be set
        self.read_commands = {}  # e.g. a voltage that can be read and return a value
        self.commands = {}  # e.g. a trigger command that does not return a value
        self.dummy_returns = {}

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

    def add_parameter(
        self,
        name: str,
        read_command: str,
        set_command: Optional[str] = None,
        dummy_return: Optional[Any] = None,
    ) -> None:
        """Adds a new parameter to the backend.

        If the parameter is read_only (say the actual voltage in a
        power supply), only the read_command needs to be defined. If
        the parameter can also be written to the set_command should
        also be defined.

        Parameters
        ----------
        name
           This name must be unique and will be used within hardware control to
           access this setting.
        read_command
           The control characters that need to be send to the instrument
           to read this value
        set_command
           The control characters that need to be send to the instrument to set
           this value. This string can include '{value}' including possible formating
           definitions where the value should be used.
        dummy_return
           A value or a user-defined function that will be returned in dummy mode.
           These can also easily be overwritten in an actual app to customize this.

        """
        if name == "online":
            logger.error(
                f"command 'online' is a special command and cannot be used in backend {self.name}"
            )
            return

        if name in self.read_commands:
            logger.error(f"command {name} already exists in backend {self.name}")
            return

        self.read_commands[name] = read_command

        if set_command is not None:
            if name in self.set_commands:
                logger.error(f"command {name} already exists in backend {self.name}")
                return

            self.set_commands[name] = set_command

        if dummy_return is not None:
            if name in self.dummy_returns:
                logger.error(f"dummy {name} already exists in backend {self.name}")
                return

            self.dummy_returns[name] = dummy_return

    def add_command(self, name: str, command: str):
        if name == "online":
            logger.error(
                f"command 'online' is a special command and cannot be used in backend {self.name}"
            )
            return
        if name in self.commands:
            logger.error(f"command {name} already exists in backend {self.name}")
            return
        self.commands[name] = command

    def list_commands(self):
        """Return all names of all commands.

        This is mostly used so that the main app can know what commands are available.
        """
        return (
            list(self.read_commands.keys()),
            list(self.set_commands.keys()),
            list(self.commands.keys()),
        )

    def get_value(self, name: str):
        """Get a value from an instrument.

        Also handle the special case to query 'online' status and
        dummy mode.

        Note: user defined functions in dummy mode should not return
        None, since we use this to indicate that the name doesn't
        exists.

        """
        if name == "online":
            return self.online

        if self.dummy:
            if name in self.dummy_returns:
                val = self.dummy_returns[name]
                if callable(val):
                    val = val()
                    if val is None:
                        logger.error(
                            "User defined function for dummy mode returned None"
                        )
                    return val
                else:
                    return val
            else:
                return

        # talk to the instrument
        if name in self.read_commands:
            value = self.query(self.read_commands[name])
            return value

    def __getitem__(self, name: str):
        """Allow values to be easily accessed.

        b = certain_backend()
        volts = b['voltage']

        """
        val = self.get_value(name)
        if val is not None:
            return val
        logger.error(f"{name} not available in backend {self.name}")

    def __getattr__(self, name: str):
        """Allow values to be easily accessed.

        b = certain_backend()
        volts = b.voltage

        """
        val = self.get_value(name)
        if val is not None:
            return val

        raise AttributeError

    def __setitem__(self, name, value):
        """Allow values to be easily accessed.

        b = certain_backend()
        b['voltage'] = 10

        """
        if name in self.set_commands:
            self.write(self.set_commands[name].format(value))
            return
        logger.error(f"{name} not available in backend {self.name}")

    def __setattr__(self, name: str, value):
        """Allow values to be easily accessed.

        b = certain_backend()
        b.voltage = 10

        """

        # need to check if 'set_commands' is in self.__dict__ to avoid an invinite loop
        if "set_commands" in self.__dict__ and name in self.set_commands:
            self.write((self.set_commands[name]).format(value))
            return
        super().__setattr__(name, value)

    def command(self, name: str):
        """Allow values to be easily accessed.

        b = certain_backend()
        b.command('trigger')

        """

        if name in self.commands:
            if self.dummy:
                logger.debug(f"{self.ID}: Would call {name} -> {self.commands[name]}")
                return
            self.write(self.commands[name])
            return

        logger.error(f"{name} not available in backend {self.name}")

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
                logger.debug(
                    f"\t({self.ID}) ERROR connecting with visa.",
                )
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

    @ensure_online
    def write(self, command: str):

        if self.dummy:
            logger.info(f"{self.name} sending command {command}")
            return

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
                reply = reply[2 : len(reply) - 1 - 2 * len(self.termination)]
                logger.debug(f'\t{self.ID}< "{command}"')
            return reply
        except Exception:
            logger.debug(f"ERROR: Query {command} failed in {self.ID}", exc_info=True)
            self.online = False
            return f"{self.ID}-Offline"
