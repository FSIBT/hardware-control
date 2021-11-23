"""
.. image:: /images/ADAM-6024.jpg
  :height: 200

"""

import logging

from ...base.hooks import range_validator, format_float

from .Adam_base import AdamBase

logger = logging.getLogger(__name__)


def _create_channel_parser(channel):
    def parse_channel(value):
        start_idx = (channel) * 7
        end_idx = (channel + 1) * 7
        rval = float(value[start_idx:end_idx])
        return rval

    return parse_channel


class Adam_6024(AdamBase):
    """Adam 6024 input/output module instrument class.

    Note: Read commands correspond to the analog input
    and set commands to analog output. Both starting at
    channel number 0!

    PARAMETERS
        * CH<X>_READ_VOLTAGE (*float*)
            * Current voltage of channel 'X'.
        * CH<X>_SET_VOLTAGE (*float*)
            * New voltage to set for channel 'X'.
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
        self.n_input_channels = 7
        self.n_output_channels = 2

        for channel in range(self.n_input_channels):
            self.add_parameter(
                f"CH{channel}_READ_VOLTAGE",
                read_command="#01",
                post_hooks=[_create_channel_parser(channel)],
                dummy_return="10.",
            )

        for channel in range(self.n_output_channels):
            self.add_parameter(
                f"CH{channel}_SET_VOLTAGE",
                set_command=f"#01{channel:02d}{{}}",
                pre_hooks=[range_validator(0, 10), format_float("06.3f")],
            )
