"""Stanford Research Systems DG535.

.. image:: /images/DG535.jpg
  :height: 200

See class definition for details.

"""

import logging, pyvisa

from ...base import Instrument, hooks

logger = logging.getLogger(__name__)


class SRS_CIS200(Instrument):
    """A driver for the Stanford Research Systems CIS200.

    Instrument home page: https://www.thinksrs.com/products/cis.html
    Manual: https://www.thinksrs.com/downloads/pdfs/manuals/CISm.pdf

    The instrument uses RS-232C and
    is controlled using the pyvisa library.
    """

    def __init__(self, name, connection_addr):

        super().__init__(name, connection_addr)

        self.manufacturer = "SRS"
        self.model = "CIS200"

        # Connection Specific Setting
        # self.config_serial(baud_rate=28800, stop_bits=20,data_bits=8,parity=0)
        self.baud_rate = 28800
        self.stop_bits = 20
        self.data_bits = 8
        self.parity = 0

        # set the terminator
        self.read_termination = "\n\r"
        self.write_termination = "\r"

        self.command_str = ""  # string used to trigger
        #   Device Specific Values

        self.channels_relative = {}
        self.channels_ampl = {}

        self.check_connection_commands = ["ID?", "IN0"]

        self.add_command("SINGLE_TRIGGER", "SS")
        self.add_parameter(
            "TRIGGER_MODE",
            read_command="TM",
            set_command="TM{}",
            dummy_return="",
        )

        self.add_parameter(
            "PULSES_PER_BURST", read_command="BC", set_command="BC{}", dummy_return=""
        )
        self.add_parameter(
            "TRIGGER_LEVEL", read_command="TL", set_command="TL{}", dummy_return=""
        )
        self.add_parameter(
            "TRIGGER_PERIOD", read_command="BP", set_command="BP{}", dummy_return=""
        )
