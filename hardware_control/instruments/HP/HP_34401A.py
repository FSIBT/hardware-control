"""
Control class to handle HP 34401A Multimeter readouts.

.. image:: /images/HP-34401A.jpg
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


class HP_33401A(Instrument):
    """A driver for the HP 34401A.

    Currently only a few options are supported. Mainly default 2 and 4
    wire measurements.

    PARAMETERS
        * MEAS_RES (*float*)
            * 2 wire automated resistance measurement
        * MEAS_4RES (*float*)
            * 4 wire automated resistance measurement

    """

    def __init__(
        self,
        instrument_name: str = "HP_34401A",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        self.manufacturer = "HP"
        self.model = "34401A"

        self.check_connection_commands = ["*IDN?"]

        ## add some low level command
        self.add_command("SET_TRIG_EXT", "TRIG:SOUR EXT")
        self.add_command("SET_TRIG_INT", "TRIG:SOUR INT")
        self.add_command("INIT", "INIT")
        self.add_command("FETCH", "FETC?")

        ## add high level measurement command for resistance
        self.add_parameter("MEAS_RES", read_command="MEAS:RES?")
        self.add_parameter("MEAS_4RES", read_command="MEAS:FRES?")
        self.add_parameter("CONF_RES", read_command="CONF:RES?")
        self.add_parameter("CONF_4RES", read_command="CONF:FRES?")
