"""Advantac ADAM 6015 (4 thermo couple readouts)

.. image:: /images/ADAM-6015.jpg
  :height: 200

See class definition for details.

"""

import logging
from .Adam_base import AdamBackend

logger = logging.getLogger(__name__)


def create_channel_parser(channel):
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


class Adam_6015(AdamBackend):
    """A driver for the Adam 6015.

    Instrument home page: https://www.advantech.com/products/a67f7853-013a-4b50-9b20-01798c56b090/adam-6015/mod_9c835a28-5c91-49fc-9de1-ec7f1dd3a82d

    """

    def __init__(self, name, connection_addr):
        super().__init__(
            instrument_name=name, connection_addr=connection_addr,
        )
        self.manufacturer = "Advantech"
        self.model = "Adam 6015"

        for i in range(1, 6 + 1):
            self.add_parameter(
                f"CH{i}_READ_TEMPERATURE",
                read_command="#01",
                post_hooks=[create_channel_parser(i)],
            )

    def query(self, cmd: str):
        self.device.sendall(b"#01\r")
        value = self.device.recv(self.buffer_length)
        return value
