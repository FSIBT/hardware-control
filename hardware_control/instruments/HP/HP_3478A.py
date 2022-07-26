"""
Control class to handle HP 3478A Multimeter readouts.

.. image:: /images/HP_3478A.jpg
  :height: 200

Has been tested with HP34401A.
connection works over proprietary driver, with "tasks"
https://engineering.purdue.edu/~aae520/hp34401manual.pdf for the manual


"""

from functools import partial
import logging
import random

from ...base import Instrument

logger = logging.getLogger(__name__)


class HP_3478A(Instrument):
    """A driver for the HP 3478A Multimeter.

    Currently only a few options are supported. Mainly default 2 and 4
    wire measurements.

    PARAMETERS
        * 2WIRE_OHMS (*float*)
            * 2 wire automated resistance measurement
        * 4WIRE_OHMS (*float*)
            * 4 wire automated resistance measurement

    """

    def __init__(
        self,
        instrument_name: str = "HP_3478A",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )
        self.manufacturer = "HP"
        self.model = "3478A"

        self.add_parameter("2WIRE_OHMS", read_command="H3")
        self.add_parameter("4WIRE_OHMS", read_command="H4")
