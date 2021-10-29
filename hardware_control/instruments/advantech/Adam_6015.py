"""
.. image:: /images/ADAM-6015.jpg
  :height: 200

"""

import logging

from .Adam_base import AdamBase

logger = logging.getLogger(__name__)


def _create_channel_parser(channel):
    """The instruments responds with information for all channels.

    We need to pick the correct one.

    The answer is something like >+0025.9237+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000+0150.0000-0050.0000

    """

    def parse_channel(value):
        # remove ">"
        value = value.decode("ascii")[1:]
        # pick channel
        value = value[channel * 10 : channel * 10 + 10]
        return value

    return parse_channel


class Adam_6015(AdamBase):
    """Adam 6015 (4 thermocouple readouts) instrument class.

    PARAMETERS
        * CH<X>_READ_TEMPERATURE (*float*)
            * Current temperature readout of channel 'X'.

    """

    def __init__(
        self,
        instrument_name: str = "ADAM_6015",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )
        self.manufacturer = "Advantech"
        self.model = "Adam 6015"

        for channel in range(1, 6 + 1):
            self.add_parameter(
                f"CH{channel}_READ_TEMPERATURE",
                read_command="#01",
                post_hooks=[_create_channel_parser(channel)],
            )

    def query(self, cmd: str):
        """Unique 'query' function for querying an Adam 6015."""
        self.device.sendall(b"#01\r")
        value = self.device.recv(self.buffer_length)
        return value
