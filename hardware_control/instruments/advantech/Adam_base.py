import logging
import socket

from ...base import Instrument

logger = logging.getLogger(__name__)


class AdamBase(Instrument):
    """Base class for all Adam instruments that overwrites some instrument base class attributes with unique Adam module attributes."""

    def __init__(
        self,
        instrument_name: str = "ADAM",
        connection_addr: str = "",
        default_port=1025,
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=default_port,
        )

        self._termination = "\r"
        self._encoding = "ascii"
        self.buffer_length = 200
        self.connection_tries = 0

        self.addr = (self.ip_addr, self.port_no)
        if self.connection_type != Instrument.SOCKET:
            logger.error(
                "Wrong instrument address. Needs to be socket type (ip or ip:port)."
            )

        self.try_connect()

    def write(self, command: str) -> None:
        """Unique 'write' function for writing to Adam instruments."""
        if self._dummy:
            logger.debug(f"{self.name} sending write command {command}")
            return

        try:
            self.device.sendto(
                (command + self._termination).encode(self._encoding), self.addr
            )
            # check return code
            indata, _ = self.device.recvfrom(self.buffer_length)
            output = indata.decode("ascii")
            if output == "?01\r":
                logger.error("Adam: Last command invalid")
                return
            if output == ">\r":
                return
        except socket.timeout:
            self._online = False

    def query(self, command: str) -> None:
        """Unique 'write' function for writing to Adam instruments."""
        if self._dummy:
            logger.debug(f"{self.name} sending query command {command}")
            return

        try:
            self.device.sendto(
                (command + self._termination).encode(self._encoding), self.addr
            )
            # check return code
            indata, _ = self.device.recvfrom(self.buffer_length)
            output = indata.decode("ascii")
            if output == "?01\r":
                logger.error("Adam: Last command invalid")
                return
            if output == ">\r":
                return
            output = output[1:-1]
            return output
        except socket.timeout:
            self._online = False

    def try_connect(self) -> None:
        """Unique 'try_connect' function for using sockets with a different option (DGRAM instead of STREAM)."""
        # Prevent trying to connect while the program is booting up
        if self.connection_tries < 1:
            self.connection_tries += 1
            return False

        # Use normal hc.base.Instrument.py try_connect() when in dummy mode
        if self._dummy:
            super().try_connect()

        # First Check current state
        if not self._online:  # If not online, try to connect
            try:
                self.device = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.device.settimeout(0.950)
                self.device.connect(self.addr)
                logger.debug(
                    f"Opened socket connection to {self.name} at"
                    f" {self.ip_addr}:{self.port_no}"
                )
                self._online = True
            except Exception as e:
                logger.error(f"During ADAM try_connect: {e}", exc_info=True)
                self._online = False
                return self._online
