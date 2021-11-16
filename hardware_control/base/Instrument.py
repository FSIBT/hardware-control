from functools import wraps
import json
import logging
import socket
import time
from typing import Optional, Any, Callable, List, Dict, Union, Iterable

import pyvisa
from pymodbus.client.sync import ModbusTcpClient as ModbusClient

from .hooks import create_converter, call_hooks

logger = logging.getLogger(__name__)


def ensure_online(f):
    """Proceed only if the instrument is online.

    This decorator assumes that the first argument of the decorated function
    is an instrument class object.
    """

    @wraps(f)
    def wrapped(*args, **kwargs):
        self = args[0]

        if not self._online:
            return None

        return f(*args, **kwargs)

    return wrapped


class Instrument:
    """
    Base class and helper functions for all physical instrument drivers.

    Instrument drivers implement the actual communications between the user
    and the instrument. The class supports several connection modes out of the box:
    pyvisa, sockets, and modbus. For other types of communication protocols, the
    try_connect function must be overwritten.

    An instrument driver should be very basic, such that one can
    use it in a terminal. A driver should neither have any GUI elements
    nor any references to Qt.

    When initializing an instrument, the user inherits from this base class
    and then calls add_parameter and/or add_command several times. These
    define 'read only' commands (e.g. to start collecting data) and/or 'read
    and write' parameters (e.g. to read or set a voltage), which are linked to the
    actual message that needs to be sent to the physical instrument. We also overwrite
    __getitem__, __getattr__, and the corresponding set functions to
    allow for a more pythonic way of reading and writing these parameters.

    An instrument can also be used in `dummy` mode. In this mode, python will not
    try to connect to the physical instrument; it will instead return pre-defined data or
    call a user-defined function to generate the return value. This
    can be handy for creating and debugging an app when one does not
    have access to the hardware.

    Attributes
    ----------
    online : bool
         Online/Offline status of the instrument
    dummy : bool
         Whether instrument is in dummy mode (no commands are sent to the instrument) or normal mode;
         this parameter is set for all an app's instruments when an app is initialized
    """

    VISA = "visa"
    """Class variable that can be used to specify a pyvisa connection."""
    SOCKET = "socket"
    """Class variable that can be used to specify a socket connection."""
    MODBUS = "modbus"
    """Class variable that can be used to specify a modbus connection."""

    def __init__(
        self, instrument_name: str, connection_addr: str, default_port: int = None
    ) -> None:

        self.name = instrument_name
        self._online: bool = False

        # can be set when defining the instrument
        self.manufacturer: Optional[str] = None
        self.model: Optional[str] = None

        self.device: Union[
            None,
            socket.socket,
            pyvisa.resources.Resource,
            ModbusClient,
        ] = None  # This is the physical instrument to write to
        self._dummy: bool = False

        self.connection_addr = connection_addr
        self.connection_type: Optional[str] = None

        self.ip_addr = None
        self.port_no = default_port
        self._termination: str = "\n"
        self._encoding: str = "utf-8"
        self.write_termination = None
        self.read_termination = None
        self.startup_delay = 0.0
        self.delay = None
        self.timeout = None

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
        self.check_connection_commands: Union[None, str, Iterable[str]] = None

        self.parse_connection_addr()

    def parse_connection_addr(self) -> None:
        """Determine the connection protocol to be used.

        Currently pyvisa addresses are automatically recognised;
        everything else is assumed to be in the form of either an
        IP address or an IP address and a port number seperated by a
        ":". For these cases, sockets are automatically assumed. If
        modbus should be used, the user needs to overwrite this in the
        init function of the instrument driver.
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

    def check_connection(self) -> bool:
        """Check if the instrument is reachable.

        The function runs the commands in `self.check_connection_commands`.

        Returns
        -------
        bool
           True if the instrument is reachable or no test have been done, False if not.
        """
        if not self._online:
            return False

        if self.check_connection_commands is None:
            return True
        if isinstance(self.check_connection_commands, str):
            self.query(self.check_connection_commands)
            return self._online
        if isinstance(self.check_connection_commands, (list, tuple)):
            for cmd in self.check_connection_commands:
                self.query(cmd)
            return self._online

    def add_parameter(
        self,
        parameter: str,
        read_command: Union[Optional[str], Optional[Callable]] = None,
        set_command: Union[Optional[str], Optional[Callable]] = None,
        pre_hooks: Optional[List] = None,
        post_hooks: Optional[List] = None,
        dummy_return: Optional[Any] = None,
    ) -> None:
        """Add a new parameter to the instrument.

        One has the option of initializing parameters without either a
        read_command or a set_command, but at least one must be specified. For
        reading and setting capability, one must specify both a read_command
        and a set_command.

        Parameters
        ----------
        parameter
           This parameter name must be unique and will be used within hardware control to
           access this setting.
        read_command
           The control characters that need to be sent to the instrument to read the parameter
        set_command
           The control characters that need to be sent to the instrument to set
           the parameter. This string can include '{}' to indicate where the set_value should
           be place in the control command.
        dummy_return
           A value or a user-defined function that will be returned in dummy mode.
           These can easily be overwritten in an app in order to be customized.
        """
        if parameter in ["ONLINE", "IGNORE"]:
            logger.error(
                f"Parameter '{parameter}' is a special command and cannot be used in instrument {self.name}."
            )
            return

        if " " in parameter:
            logger.error(
                f"Parameter '{parameter}' uses a whitespace in its name. This is not allowed."
            )
            return

        if read_command is not None:
            if parameter in self.read_commands:
                logger.error(
                    f"A read command already exists for parameter '{parameter}' in instrument {self.name}."
                )
                return
            self.read_commands[parameter] = read_command

        if set_command is not None:
            if parameter in self.set_commands:
                logger.error(
                    f"A set command already exists for parameter '{parameter}' in instrument {self.name}."
                )
                return
            self.set_commands[parameter] = set_command

        if pre_hooks is not None:
            if parameter in self.pre_hooks:
                logger.error(
                    f"You have specified multiple pre-hooks for parameter '{parameter}' in instrument {self.name}. Please combine all pre-hooks for parameter '{parameter}' into a list."
                )
                return
            for hook in pre_hooks:
                self.add_pre_hook(parameter, hook)

        if post_hooks is not None:
            if parameter in self.post_hooks:
                logger.error(
                    f"You have specified multiple post-hooks for parameter '{parameter}' in instrument {self.name}. Please combine all post-hooks for parameter '{parameter}' into a list."
                )
                return
            for hook in post_hooks:
                self.add_post_hook(parameter, hook)

        if dummy_return is not None:
            if parameter in self.dummy_returns:
                logger.error(
                    f"Dummy return for parameter '{parameter}' already exists in instrument {self.name}."
                )
                return

            if isinstance(dummy_return, str) and " " in dummy_return:
                logger.error(
                    f"Dummy return '{dummy_return}' for parameter '{parameter}' in instrument {self.name} should not include a whitespace. Not adding it."
                )
                return

            self.dummy_returns[parameter] = dummy_return

    def add_command(self, command_name: str, command: Union[str, Callable]) -> None:
        """Add a command to an instrument."""
        if command_name in self.commands:
            logger.error(
                f"Command {command_name} already exists in instrument {self.name}."
            )
            return
        self.commands[command_name] = command

    def add_pre_hook(self, parameter: str, function: Callable) -> None:
        """Add a 'hook function' to be exectued prior to the setting of a parameter."""
        if parameter in self.pre_hooks:
            self.pre_hooks[parameter].append(function)
        else:
            self.pre_hooks[parameter] = [function]

    def add_post_hook(self, parameter: str, function: Callable) -> None:
        """Add a 'hook function' to be exectued after reading a parameter."""
        if parameter in self.post_hooks:
            self.post_hooks[parameter].append(function)
        else:
            self.post_hooks[parameter] = [function]

    def add_lookup(self, parameter: str, lookuptable: Dict) -> None:
        """Add a pre- and a post-hook to convert values according to a lookup table.

        The lookup table will be used in the pre-hook, and an inverse of the
        lookup table will be created for the post-hook.
        """
        self.add_pre_hook(parameter, create_converter(lookuptable))

        inverse_lookuptable = {b: a for a, b in lookuptable.items()}
        self.add_post_hook(parameter, create_converter(inverse_lookuptable))

    def list_parameters(self) -> List[str]:
        """List all instrument commands, parameter read_commands, and parameter set_commands.

        This is mostly used so that the main app can know what commands are available.
        """
        return (
            list(self.read_commands.keys()) + ["ONLINE"],
            list(self.set_commands.keys()),
            list(self.commands.keys()),
        )

    def get_value(self, parameter: str):
        """Get the value of a parameter from the physical instrument.

        This function also handles the special cases of querying the
        _online and _dummy variable values.

        Note: User-defined functions in dummy mode should not return
        None, since None indicates that a parameter does not exist.
        """

        if parameter == "ONLINE":
            return self._online

        value = None
        if self._dummy:
            if parameter in self.dummy_returns:
                value = self.dummy_returns[parameter]
                if callable(value):
                    value = value()
                    if value is None:
                        logger.error(
                            "User-defined function for dummy mode returned None."
                        )
            else:
                logger.error(
                    f"When calling 'Instrument.get_value': User requested parameter '{parameter}' in instrument '{self.name}' in dummy mode, but no dummy return was defined."
                )
        else:
            # talk to the instrument
            if parameter in self.read_commands:
                if callable(self.read_commands[parameter]):
                    value = self.read_commands[parameter]()
                else:
                    value = self.query(self.read_commands[parameter])
            # only handle post_hooks at the instrument level when we are not in dummy mode
            # since we call hooks such as IEEE754_converter_to_ulong_pair here
            if parameter in self.post_hooks:
                hooks = self.post_hooks[parameter]
                value = call_hooks(hooks, value)

        return value

    def __getitem__(self, parameter: str):
        """Allow values to be easily accessed.

        Example Usage:
        b = certain_instrument()
        volts = b['voltage']
        """
        val = self.get_value(parameter)
        if val is not None:
            return val
        logger.error(
            f"When calling 'Instrument.__getitem__': '{parameter}' not available in instrument '{self.name}'"
        )

    def __getattr__(self, parameter: str):
        """Allow values to be easily accessed.

        Example Usage:
        b = certain_instrument()
        volts = b.voltage
        """
        val = self.get_value(parameter)
        if val is not None:
            return val

        logger.error(
            f"When calling 'Instrument.__getattr__': '{parameter}' not available in instrument '{self.name}'"
        )

    def set_value(self, parameter: str, value) -> None:
        """Call all of an instrument parameter's pre-hooks, then set the value of the parameter."""
        if parameter in self.set_commands:
            if parameter in self.pre_hooks:
                hooks = self.pre_hooks[parameter]
                value = call_hooks(hooks, value)
            if value is None:
                return
            if callable(self.set_commands[parameter]):
                self.set_commands[parameter](value)
            else:
                self.write(self.set_commands[parameter].format(value))
            return
        logger.error(
            f"When calling 'Instrumentset_value': '{parameter}' not available in instrument '{self.name}'"
        )

    def __setitem__(self, parameter, value) -> None:
        """Allow values to be easily set.

        Example Usage:
        b = certain_instrument()
        b['voltage'] = 10
        """
        self.set_value(parameter, value)

    def __setattr__(self, parameter: str, value) -> None:
        """Allow values to be easily set.

        Example Usage:
        b = certain_instrument()
        b.voltage = 10
        """
        # Need to check if 'set_commands' is in self.__dict__ to avoid an infinite loop
        if (
            "set_commands" in self.__dict__
            and "pre_hooks" in self.__dict__
            and "post_hooks" in self.__dict__
            and parameter in self.set_commands
        ):
            self.set_value(parameter, value)
        super().__setattr__(parameter, value)

    def command(self, command_name: str) -> None:
        """Execute an instrument command.

        Example Usage:
        b = certain_instrument()
        b.command('trigger')
        """
        if command_name in self.commands:
            if self._dummy:
                logger.debug(
                    f"{self.name}: Would call {command_name} -> {self.commands[command_name]}"
                )
                return
            if callable(self.commands[command_name]):
                self.commands[command_name]()
            else:
                self.write(self.commands[command_name])
            return

        logger.error(
            f"When calling 'command': {command_name} not available in instrument {self.name}"
        )

    def close(self) -> None:
        """Close connection to the instrument."""
        if self._dummy:
            logger.debug(f"{self.name}: Dummy connection closed.")
            return

        if self.device is None:
            logger.debug(f"{self.name}: Called close with no device defined.")
            return

        self.device.close()

    def try_connect(self) -> bool:
        """Checks if the instrument is in communication with the driver and tries to re-establish communication if it not.

        Certain instruments require that this function be overwritten.
        """
        if self._dummy:
            if self._online:
                return True
            logger.debug(
                f"{self.name}: creating dummy connection to {self.connection_addr}"
            )
            self._online = True
            return True

        if self._online:
            if self.check_connection():
                return True
            self._online = False

        logger.debug(f"{self.name}: trying to connect")

        if self.connection_type == Instrument.VISA:
            try:
                rm = pyvisa.ResourceManager("@py")
                self.device = rm.open_resource(self.connection_addr)
                self.device.read_termination = (
                    self._termination
                    if not self.read_termination
                    else self.read_termination
                )
                self.device.write_termination = (
                    self._termination
                    if not self.write_termination
                    else self.write_termination
                )
                if self.timeout:
                    self.device.timeout = self.timeout
                logger.debug(
                    f"opened pyvisa connection to {self.name} at {self.connection_addr}"
                )
            except Exception as e:
                self._online = False
                logger.error(
                    f"\t({self.name}) received the following error connecting with visa: {e}."
                )
                logger.debug(f"{self.name} is offline")
            else:
                self._online = True
        elif self.connection_type == Instrument.SOCKET:
            try:
                self.device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.device.settimeout(2)
                self.device.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
                self.device.connect((self.ip_addr, int(self.port_no)))

                logger.debug(
                    f"opened socket connection to {self.name} at {self.ip_addr}:{self.port_no}"
                )
            except Exception as e:
                self._online = False
                logger.error(
                    f"\t({self.name}) received the following error connecting with sockets: {e}."
                )
                logger.debug(f"{self.name} is offline")
            else:
                self._online = True
        elif self.connection_type == Instrument.MODBUS:
            try:
                self.device = ModbusClient(host=self.connection_addr)
                if self.device.connect():
                    self._online = True
                    logger.debug(
                        f"opened modbus connection to {self.name} at {self.connection_addr}"
                    )
            except Exception as e:
                self._online = False
                logger.error(
                    f"\t({self.name}) received the following error connecting with modbus: {e}."
                )
                logger.debug(f"{self.name} is offline")

        time.sleep(self.startup_delay)
        # If connection purportedly successful, verify connection
        if self._online:
            if not self.check_connection():
                self._online = False

        return self._online

    def config_serial(
        self,
        baud_rate: Optional[int] = None,
        stop_bits: Optional[int] = None,
        data_bits: Optional[int] = None,
        parity: Optional[int] = None,
    ) -> None:
        """Configure a serial port."""
        if self.device is None:
            logger.error(f"No visa device for '{self.name}'")
            self._online = False
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
    def write(self, command: str) -> None:
        """Write a command directly to the insturment."""
        if self._dummy:
            logger.debug(f"{self.name} sending write command {command}")
            return

        try:
            logger.debug(f"write: '{command}' to '{self.name}'")
            if self.connection_type == Instrument.VISA:
                self.device.write(command)
                return
            if self.connection_type == Instrument.SOCKET:
                self.device.sendall(bytes(command + self._termination, self._encoding))
                return
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
                    self.device.write_coil(address=address, value=value, unit=unit)
                elif command == "write_registers":
                    self.device.write_registers(
                        address=address, values=value, unit=unit
                    )
                else:
                    logger.error(
                        f"modbus command for {command} currently not implemented for instrument '{self.name}'"
                    )
        except Exception:
            logger.error(f"Write {command} failed in {self.name}", exc_info=True)
            self._online = False
            return

    @staticmethod
    def _recvall(sock):
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
    def query(self, command: str, delay: Optional[float] = None):
        """Query the insturment directly."""
        if self._dummy:
            logger.debug(f"'{self.name}' sending query command '{command}'")
            return

        try:
            logger.debug(f"'{self.name}' sending query command '{command}'")
            if self.connection_type == Instrument.VISA:
                if self.delay is not None:
                    inst_delay = self.delay
                else:
                    inst_delay = 0.0

                if delay is not None:
                    inst_delay = delay

                self.device.write(command)
                time.sleep(inst_delay)
                reply = self.device.read(
                    termination=(self.read_termination or self._termination)
                )
            elif self.connection_type == Instrument.SOCKET:
                self.device.sendall(bytes(command + self._termination, self._encoding))
                reply_bytes = Instrument._recvall(self.device)
                reply = str(reply_bytes)
                reply = reply[2 : len(reply) - 1 - 2 * len(self._termination)]
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
            logger.error(f"Query {command} failed in {self.name}", exc_info=True)
            self._online = False
            return None
