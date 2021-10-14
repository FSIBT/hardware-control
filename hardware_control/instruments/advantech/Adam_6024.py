"""Advantac ADAM 6024

.. image:: /images/ADAM-6024.jpg
  :height: 200

See class definition for details.

"""

import logging
import random

from .Adam_base import AdamBackend

logger = logging.getLogger(__name__)


def create_channel_parser(channel):
    def parse_channel(value):
        start_idx = (channel - 1) * 7
        end_idx = channel * 7
        rval = float(value[start_idx:end_idx])
        return rval

    return parse_channel


class Adam_6024(AdamBackend):
    """A driver for the Adam 6024 input/output module.

    Instrument home page: https://www.advantech.com/products/a67f7853-013a-4b50-9b20-01798c56b090/adam-6024/mod_99d243cd-2f38-48a3-a82c-eeb5e0f4e278

    """

    def __init__(
        self,
        instrument_name: str = "ADAM_6024",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )
        self.manufacturer = "Advantech"
        self.model = "Adam 6024"

        # This specifies the max number of channels the user can request
        self.n_input_channels = 8
        self.n_output_channels = 4

        for i in range(1, self.n_input_channels + 1):
            self.add_parameter(
                f"CH{i}_READ_VOLTAGE",
                read_command="#01",
                post_hooks=[create_channel_parser(i)],
            )

        for i in range(1, self.n_output_channels + 1):
            self.add_parameter(
                f"CH{i}_SET_VOLTAGE",
                set_command=f"#01{i:02d}{{:06.3f}}",
                pre_hooks=[range_validator(0, 10)],
            )
