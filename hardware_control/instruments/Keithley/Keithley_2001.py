"""
Control class to handle 2001 Keithly .

.. image:: /images/Lake_Shore_224.png
  :height: 200

"""

from functools import partial
import logging
import random

from ...base import Instrument

logger = logging.getLogger(__name__)


class Keithley_2001(Instrument):
    """
    A driver for the Keithley_2001
    Instrument home page:
    """

    def __init__(
        self,
        instrument_name: str = "Keithley_2001",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=7777,
        )

        self.manufacturer = "Keithley"
        self.model = "2001"

        self._termination = "\n"
        ## the <RMT> also include an EOI char, need to test

        self.check_connection_commands = ["*IDN?"]

        ## add some low level command
        self.add_command(f"SEND_TRIG", f"*TRG")
        self.add_command(f"FETCH", f":FETC?")
        self.add_command(f"DATA", f":DATA?")

        ## add high level measurement command for resistance
        self.add_parameter(
            "MEAS_RES", read_command=f":MEAS:RES?", post_hooks=[self.parse_resistor]
        )
        self.add_parameter("CONF_RES", read_command=f":CONF:RES?")

    def parse_resistor(self, value):
        """parse out the resistor value"""
        value = value.split(",")[0]
        value = value[:-4]  # remove NOHM
        return value

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
            status["CONF"] = self.query(f":CONF? {channel}")

        return status
