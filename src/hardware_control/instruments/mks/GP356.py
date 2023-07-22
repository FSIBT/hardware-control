"""
Instrument driver class to handle Granville Phillips 356 Series Ion gauge for pressure readout.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with GP356 Ion gauge
connection works over proprietary driver, with "tasks"
"""

import logging

from ...base import Instrument

logger = logging.getLogger(__name__)


class GP_356(Instrument):
    """Grandville Phillips Ion Gauge instrument class."""

    def __init__(
        self,
        instrument_name: str = "GP_356",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=7777,
        )

        self.manufacturer = "MKS"
        self.model = "GP365"

        self.ins_add = "#02"  # The address setting on the instrument
        self.check_connection_commands = [self.ins_add + "IGS"]

        self._termination = "\r"

        self.add_parameter(
            "READ_STATE",
            read_command="{self.ins_add}IGS",
            set_command="",
            dummy_return="",
        )
        self.add_parameter(
            "READ_PRESSURE",
            read_command="{self.ins_add}RD",
            set_command="",
            dummy_return="",
        )

        self.add_parameter(
            "READ_EMISSION",
            read_command="{self.ins_add}RE",
            set_command="",
            dummy_return="",
        )

        self.add_parameter(
            "READ_FILAMENT",
            read_command="{self.ins_add}RF",
            set_command="",
            dummy_return="",
        )

        self.add_parameter(
            "READ_UNIT",
            read_command="{self.ins_add}SU",
            set_command="",
            dummy_return="",
        )

        logger.warning("The GP_356 driver class is still under development.")
