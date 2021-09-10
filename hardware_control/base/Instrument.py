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
import json
import logging
import socket
from typing import Optional, Any, Callable, List

import pyvisa
from pymodbus.client.sync import ModbusTcpClient as ModbusClient

from .hooks import create_converter

logger = logging.getLogger(__name__)


def call_hooks(hooks_list, value):
    """Call a list of function.

    If any of the functions returns None, the final value will be
    ignored and the no further hooks will be called.

    Every hook function must take a single parameter: the value of the
    parameter to be set (set to None for commands)

    If a hook needs several parameter, one should pass these in when
    defining the hook using lambda functions, e.g.:

    app.add_hook(instrument, parameter, 'pre_set_hooks', lambda x: change_ui(app, x, widget)

    where app and widget are defined in the enironment where add_hook
    is called.

    """
    for hook in hooks_list:
        if callable(hook):
            value = hook(value)
            if value is None:
                return None
    return str(value)


def ensure_online(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        self = args[0]

        if not self.online:
            return f"{self.name}-Offline"

        return f(*args, **kwargs)

    return wrapped


class Instrument:
    """Base class for all physical instruments.

    The instrument implements the actual communications between python
    and the instrument.

    The class supports several connections modes out of the box:
    pyvisa, sockets, and modbus

    For other type of communictioan the try_connect function needs to
    be overwritten.

    When implementing a instrument, the user inherits from this base class
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

    def __init__(
        self, instrument_name: str, connection_addr: str, default_port: int = None
    ):

        self.name = instrument_name
        self.online: bool = False

        # can be set when defining the instrument
        self.manufacturer = None
        self.model = None

        self.device = None  # This is the physical instrument to write to
        self.dummy: bool = False

        self.connection_addr = connection_addr
        self.connection_type = None

        self.ip_addr = None
        self.port_no = default_port
        self.termination: str = "\n"
        self.encoding: str = "utf-8"
        self.write_termination = None
        self.read_termination = None

        # We save all possible commands and settings in several dictionaries
        self.set_commands = {}  # e.g. a voltage that can be set
        self.read_commands = {}  # e.g. a voltage that can be read and return a value
        self.commands = {}  # e.g. a trigger command that does not return a value

        self.dummy_returns = {}

        self.pre_hooks = {}
        self.post_hooks = {}

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
        init function of the instrument.

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
            self.connection_type = Instrument.VISA
        else:
            self.connection_type = Instrument.SOCKET
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
        read_command: str or Callable,
        set_command: Optional[str] = None or Optional[Callable],
        pre_hooks: Optional[List] = None,
        post_hooks: Optional[List] = None,
        dummy_return: Optional[Any] = None,
    ) -> None:
        """Adds a new parameter to the instrument.

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
        if name in ["online", "command", "get"]:
            logger.error(
                f"command 'online','get', and 'command' a special command and cannot be used in instrument {self.name}"
            )
            return

        if " " in name:
            logger.error(
                f"command '{name}' uses a whitespace in its name. This is not allowed."
            )
            return

        if read_command is not None:
            if name in self.read_commands:
                logger.error(f"command {name} already exists in instrument {self.name}")
                return
            self.read_commands[name] = read_command

        if set_command is not None:
            if name in self.set_commands:
                logger.error(f"command {name} already exists in instrument {self.name}")
                return

            self.set_commands[name] = set_command

        if pre_hooks is not None:
            if name in self.pre_hooks:
                logger.error(
                    f"pre_hooks {name} already exists in instrument {self.name}"
                )
                return
            for hook in pre_hooks:
                self.add_pre_hook(name, hook)

        if post_hooks is not None:
            if name in self.post_hooks:
                logger.error(
                    f"post_hooks {name} already exists in instrument {self.name}"
                )
                return
            for hook in post_hooks:
                self.add_post_hook(name, hook)

        if dummy_return is not None:
            if name in self.dummy_returns:
                logger.error(f"dummy {name} already exists in instrument {self.name}")
                return

            self.dummy_returns[name] = dummy_return

    def add_command(self, name: str, command: str):
        if name == "online":
            logger.error(
                f"command 'online' is a special command and cannot be used in instrument {self.name}"
            )
            return
        if name in self.commands:
            logger.error(f"command {name} already exists in instrument {self.name}")
            return
        self.commands[name] = command

    def add_pre_hook(self, name: str, function: Callable):
        if name in self.pre_hooks:
            self.pre_hooks[name].append(function)
        else:
            self.pre_hooks[name] = [function]

    def add_post_hook(self, name: str, function: Callable):
        if name in self.post_hooks:
            self.post_hooks[name].append(function)
        else:
            self.post_hooks[name] = [function]

    def add_lookup(self, name, lookuptable):
        """Adds a pre and a post hook to convert values according to the lookuptable.

        The lookuptable will be used in the pre-hook and an inverse one will be created for the post-hook.
        """

        self.add_pre_hook(name, create_converter(lookuptable))

        inverse_lookuptable = {b: a for a, b in lookuptable.items()}
        self.add_post_hook(name, create_converter(inverse_lookuptable))

    def list_parameters(self):
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
                logger.debug(f"No dummy defined for {name} in instrument '{self.name}'")
                return

        # talk to the instrument
        if name in self.read_commands:
            if callable(self.read_commands[name]):
                self.read_commands[name]
            else:
                value = self.query(self.read_commands[name])
            if name in self.post_hooks:
                hooks = self.post_hooks[name]
                value = call_hooks(hooks, value)
            return value

    def __getitem__(self, name: str):
        """Allow values to be easily accessed.

        b = certain_instrument()
        volts = b['voltage']

        """
        val = self.get_value(name)
        if val is not None:
            return val
        logger.error(f"'{name}' not available in instrument '{self.name}'")

    def __getattr__(self, name: str):
        """Allow values to be easily accessed.

        b = certain_instrument()
        volts = b.voltage

        """
        val = self.get_value(name)
        if val is not None:
            return val

        raise AttributeError

    def set_value(self, name, value):
        if name in self.set_commands:
            if name in self.pre_hooks:
                hooks = self.pre_hooks[name]
                value = call_hooks(hooks, value)
            if value is None:
                return
            if callable(self.set_commands[name]):
                self.set_commands[name]
            else:
                self.write(self.set_commands[name].format(value))
            return
        logger.error(f"'{name}' not available in instrument '{self.name}'")

    def __setitem__(self, name, value):
        """Allow values to be easily accessed.

        b = certain_instrument()
        b['voltage'] = 10

        """
        self.set_value(name, value)

    def __setattr__(self, name: str, value):
        """Allow values to be easily accessed.

        b = certain_instrument()
        b.voltage = 10

        """

        # need to check if 'set_commands' is in self.__dict__ to avoid an infinite loop
        if (
            "set_commands" in self.__dict__
            and "pre_hooks" in self.__dict__
            and "post_hooks" in self.__dict__
            and name in self.set_commands
        ):
            self.set_values(name, value)
        super().__setattr__(name, value)

    def command(self, name: str):
        """Allow values to be easily accessed.

        b = certain_instrument()
        b.command('trigger')

        """

        if name in self.commands:
            if self.dummy:
                logger.debug(f"{self.name}: Would call {name} -> {self.commands[name]}")
                return
            if callable(self.commands[name]):
                self.commands[name]
            else:
                self.write(self.commands[name])
            return

        logger.error(f"{name} not available in instrument {self.name}")

    def close(self):
        """Close connection to instrument."""

        if self.dummy:
            logger.debug(f"{self.name}: Dummy connection closed")
            return False

        if self.device is None:
            logger.debug(f"{self.name}: Called close with not device defined")
            return False

        self.device.close()

    def try_connect(self):
        """Checks if the instrument is in communication with the object, if it is
        not, it tries to re-establish communication."""

        if self.dummy:
            if self.online:
                return True
            logger.debug(
                f"{self.name}: creating dummy connection to {self.connection_addr}"
            )
            self.online = True
            return True

        if self.online:
            if self.check_connection():
                return True
            self.online = False

        logger.debug(f"{self.name}: trying to connect")

        if self.connection_type == Instrument.VISA:
            try:
                rm = pyvisa.ResourceManager("@py")
                self.device = rm.open_resource(self.connection_addr)
                self.device.read_termination = (
                    self.termination
                    if not self.read_termination
                    else self.read_termination
                )
                self.device.write_termination = (
                    self.termination
                    if not self.write_termination
                    else self.write_termination
                )
                logger.debug(
                    f"opened pyvisa connection to {self.name} at {self.connection_addr}"
                )
            except Exception:
                self.online = False
                logger.debug(
                    f"\t({self.name}) ERROR connecting with visa.",
                )
                logger.debug(f"{self.name} is offline")
            else:
                self.online = True
        elif self.connection_type == Instrument.SOCKET:
            try:
                self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.device.settimeout(2)
                self.device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                self.device.connect((self.ip_addr, int(self.port_no)))

                logger.debug(
                    f"opened socket connection to {self.name} at {self.ip_addr}:{self.port_no}"
                )
            except Exception:
                self.online = False
                logger.debug(f"\t({self.name}) ERROR connecting with sockets.")
                logger.debug(f"{self.name} is offline")
            else:
                self.online = True
        elif self.connection_type == Instrument.MODBUS:
            try:
                self.device = ModbusClient(host=self.connection_addr)
                if self.device.connect():
                    self.online = True
                    logger.debug(
                        f"opened modbus connection to {self.name} at {self.connection_addr}"
                    )
            except Exception:
                self.online = False
                logger.debug(f"\t({self.name}) ERROR connecting with modbus.")
                logger.debug(f"{self.name} is offline")
        # If connection purportedly successful, verify connection
        if self.online:
            if not self.check_connection():
                self.online = False

        return self.online

    def config_serial(
        self,
        baud_rate: int = None,
        stop_bits: int = None,
        data_bits: int = None,
        parity: int = None,
    ):
        if self.device is None:
            logger.error(f"No visa device for '{self.name}'")
            self.online = False
            return
        if self.connection_type == Instrument.VISA:
            self.device.encoding = "ascii"
            if baud_rate:
                self.device.baud_rate = baud_rate
            if stop_bits:
                self.device.stop_bits = stop_bits
            if data_bits:
                self.device.data_bits = data_bits
            if parity:
                self.device.parity = parity

    @ensure_online
    def write(self, command: str):

        if self.dummy:
            logger.info(f"{self.name} sending write command {command}")
            return

        try:
            logger.debug(f'\t{self.name} < "{command}"')
            if self.connection_type == Instrument.VISA:
                self.device.write(command)
                return command
            if self.connection_type == Instrument.SOCKET:
                self.device.sendall(bytes(command + self.termination, self.encoding))
                return command
            if self.connection_type == Instrument.MODBUS:
                # modbus commands must be formatted in the following way:
                # command:address:value:unit, e.g. 4 colon separated values
                # since we are getting a string, we will parse the 'value' using json
                # back into a python object
                command, address, value, unit = command.split(":")

                address = int(address)
                value = json.loads(value)
                unit = int(unit)

                if command == "write_coil":
                    self.device.write_coil(address=address, values=value, unit=unit)
                else:
                    logger.error(
                        f"modbus command for {command} currently not implemented for instrument '{self.name}'"
                    )
        except Exception:
            logger.debug(f"ERROR: Write {command} failed in {self.name}", exc_info=True)
            self.online = False
            return f"{self.name}-Offline"

    @staticmethod
    def recvall(sock):
        BUFF_SIZE = 4096  # 4 KiB
        data = b""
        while True:
            part = sock.recv(BUFF_SIZE)
            data += part
            data_str = str(part)
            if data_str[-3:-1] == "\\n":
                break
        return data

    @ensure_online
    def query(self, command: str):

        if self.dummy:
            logger.info(f"{self.name} sending query command {command}")
            return

        try:
            logger.debug(f"INFO: Sending query {command} in {self.name}")
            if self.connection_type == Instrument.VISA:
                reply = self.device.query(command)
            elif self.connection_type == Instrument.SOCKET:
                self.device.sendall(bytes(command + self.termination, self.encoding))
                reply_bytes = Instrument.recvall(self.device)
                reply = str(reply_bytes)
                reply = reply[2 : len(reply) - 1 - 2 * len(self.termination)]
                logger.debug(f'\t{self.name}< "{command}"')
            elif self.connection_type == Instrument.MODBUS:
                # modbus commands must be formatted in the following way:
                # command:address:nr_bytes:unit, e.g. 4 colon separated values
                command, address, nr, unit = command.split(":")
                address = int(address)
                nr = int(nr)
                unit = int(unit)
                if command == "read_input_registers":
                    reply = self.device.read_input_registers(
                        count=nr, address=address, unit=unit
                    )
                else:
                    logger.error(
                        f"modbus command for {command} currently not implemented for instrument '{self.name}'"
                    )

            return reply
        except Exception:
            logger.debug(f"ERROR: Query {command} failed in {self.name}", exc_info=True)
            self.online = False
            return f"{self.name}-Offline"

    def load_state(self, filename: str):
        """Reads and sets instrument settings from a json dictionary"""
        try:
            with open(filename) as file:
                default_settings = json.load(file)
                logger.info(f"settings for {self.name} read from file '{filename}'")
        except:
            logger.error(
                f"Failed to read file '{filename}'. Using defualt case.", exc_info=True
            )
            return

        for key in default_settings:
            if key in list(self.set_commands.keys()):
                self.__setitem__(key, default_settings[key])
