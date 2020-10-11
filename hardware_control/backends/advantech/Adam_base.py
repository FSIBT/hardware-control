"""Advantac Adam backend base class


A base class for connecting to ADAM modules.

"""
import logging

from ..base import Backend

logger = logging.getLogger(__name__)


class AdamBackend(Backend):
    """Common try connect and init parts for all ADAM modules"""

    def __init__(self, instrument_name, connection_addr, default_port=1025):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=default_port,
        )

        self.termination = "\r"
        self.encoding = "ascii"
        self.bug = 200

        self.addr = (self.ip_addr, self.port_no)

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
