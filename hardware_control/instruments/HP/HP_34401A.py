"""
Control class to handle HP34401A Multimeter readouts.

.. image:: /images/Lake_Shore_224.png
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
    """
    A driver for the Lakeshore 224 Temp Monitor
    Instrument home page:
    https://www.keysight.com/us/en/product/34401A/digital-multimeter-6-digit.html
    """

    def __init__(
        self,
        instrument_name: str = "HP_34401A",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=7777,
        )

        self.manufacturer = "HP"
        self.model = "34401A"

        self._termination = "\r\n"

        self.check_connection_commands = ["*IDN?"]

        ## add some low level command
        self.add_command(f"SET_TRIG_EXT", f"TRIG:SOUR EXT")
        self.add_command(f"SET_TRIG_INT", f"TRIG:SOUR INT")
        self.add_command(f"INIT", f"INIT")
        self.add_command(f"FETCH", f"FETC?")

        ## add high level measurement command for resistance
        self.add_parameter(
            f"MEAS_RES",
            read_command=f"MEAS:RES? {{}}",
            set_command=f"",
            post_hooks="",
            dummy_return="",
        )

        self.add_parameter(
            f"MEAS_4RES",
            read_command=f"MEAS:FRES? {{}}",
            set_command="",
            post_hooks="",
            dummy_return="",
        )

        self.add_parameter(
            f"CONF_RES",
            read_command=f"CONF:RES? {{}}",
            set_command=f"",
            post_hooks="",
            dummy_return="",
        )

        self.add_parameter(
            f"CONF_4RES",
            read_command=f"CONF:FRES? {{}}",
            set_command="",
            post_hooks="",
            dummy_return="",
        )

    def read_status(self, channel):
        """
        Read all settings of the instrument

        """
        if self._dummy:
            status = {}
            status["CONF"] = "1"
            status["NAME"] = "dummy"
        else:
            status = {}
            status["CONF"] = self.query(f"CONF?")

        return status
