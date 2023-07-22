"""
Base class for Lake Shore temperature measurement instruments.

"""

from functools import partial
import logging
import random

from ...base import Instrument

logger = logging.getLogger(__name__)


class LakeshoreBase(Instrument):
    """
    Most Lake Shore instrument seem to use the same basic commands and differ mostly in channel
    numbers, etc.
    """

    def __init__(
        self,
        instrument_name: str = "LAKESHORE_224",
        connection_addr: str = "",
        default_port: int = 7777,
        num_channels: int = 0,
        active_channels=None,
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=7777,
        )

        self.manufacturer = "Lakeshore"
        self.model = "not set"

        self.num_channels = num_channels
        self.active_channels = active_channels
        self._termination = "\r\n"

        self.check_connection_commands = ["*IDN?"]

        for channel in self.active_channels:
            self.add_command(f"SET_CH{channel}_OFF", f"INCRV {channel} 0")
            self.add_command(
                f"READ_CH{channel}_STATUS", partial(self.read_status, channel)
            )

            self.add_parameter(
                f"CH{channel}_CURVE",
                read_command=f"INCRV? {channel}",
                set_command=f"INCRV {channel} {{}}",
                post_hooks=[lambda value: value if value != "00" else None],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_READ_TEMP",
                read_command=f"KRDG? {channel}",
                set_command="",
                post_hooks=[lambda value: value if value != "00" else None],
                dummy_return=lambda: random.random() * 200 + 200,
            )

            self.add_parameter(
                f"CH{channel}_ON-OFF",
                read_command=f"INCRV? {channel}",
                set_command=f"INCRV {channel} {{}}",
                post_hooks=[lambda value: value if value != "00" else None],
                dummy_return="",
            )

    def read_status(self, channel):
        """
        Read all settings of the instrument

        """
        if self._dummy:
            status = {}
            status["CURVE"] = "1"
            status["NAME"] = "dummy"
        else:
            status = {}
            status["CURVE"] = self.query(f"INCRV? {channel}")
            status["NAME"] = self.query(f"INNAME? {channel}")

        return status
