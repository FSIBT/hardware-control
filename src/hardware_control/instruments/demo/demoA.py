"""An instrument driver for a dummy instrument that can be used for debugging and development.

The QT instrument frontend for this virtual instrument can be found in hardware_control/debug/demoA.py



"""


import logging
import random

from ...base import Instrument

logger = logging.getLogger(__name__)


class DemoA(Instrument):
    """An example instrument class.

    PARAMETERS
        * CH<X>_ENABLE (*bool*)
            * On/off status of channel 'X'.
        * CH<X>_VALUE (*float*)
            * Random value stored in channel 'X'.

    """

    def __init__(self, instrument_name: str = "DemoA", connection_addr: str = ""):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=7123,
        )
        self._encoding = "ascii"

        self.channels = [1, 2, 3]

        for ch in self.channels:
            self.add_parameter(
                f"CH{ch}_ENABLE",
                read_command=None,
                set_command=None,
                dummy_return=lambda: random.random() > 0.5,
            )

            self.add_parameter(
                f"CH{ch}_VALUE",
                read_command=None,
                set_command=None,
                dummy_return=lambda: random.random() * 5,
            )
