"""Tenma 72-2710 Power supply

.. image:: /images/Tenma-ps-72-2710.png
  :height: 200

See class definition for details.

"""

import logging

from ...base import Instrument

logger = logging.getLogger(__name__)


class TENMA_72_2710(Instrument):
    """Driver for Tenma power supply 72-2710

    The manual can be found here: https://www.farnell.com/datasheets/2578054.pdf

    One windows, the correct driver needs to be installed. The system uses pyvsia's serial driver.
    """

    def __init__(
        self,
        instrument_name: str = "TENMA-72-2710",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        self.manufacturer = "TENMA"
        self.model = "72-2710"

        # Connection Specific Setting
        self._encoding = "ascii"

        # set the terminator
        self.read_termination = "\n"
        self.write_termination = "\n"
        self.delay = 0.5

        self.add_command("CH1_ON", "OUT1")
        self.add_command("CH1_OFF", "OUT0")

        self.add_parameter(
            "CH1_V_OUT",
            read_command="VOUT1?",
            dummy_return="1",
        )
        self.add_parameter(
            "CH1_V_SET",
            read_command="VSET1?",
            set_command="VSET1:{}",
            dummy_return="1",
        )
        self.add_parameter(
            "CH1_I_OUT",
            read_command="IOUT1?",
            dummy_return="1",
        )
        self.add_parameter(
            "CH1_I_SET",
            read_command="ISET1?",
            set_command="ISET1:{}",
            dummy_return="1",
        )
        self.add_parameter(
            "CH1_STATUS",
            read_command="STATUS?",
            post_hooks=[
                self._return_status,
            ],
        )
        self.add_parameter("SAVE", set_command="SAV{}")
        self.add_parameter("RECALL", set_command="RCL{}")

    def _return_status(self, value):
        value = int(value)
        status = {"CONTROL_MODE": value & 1, "ON_OFF": value & 64}

    def on_connect(self):
        self.config_serial(baud_rate=9600, stop_bits=10, data_bits=8, parity=0)
