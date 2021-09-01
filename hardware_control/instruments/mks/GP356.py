"""
Control class to handle Granville Phillips 356 Series Ion gauge for preesure readout.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with GP356 Ion gauge
connection works over proprietary driver, with "tasks"
"""

import logging
import random

import numpy as np

from ...base import Instrument
from ..utility import ensure_float, get_channel_from_command

logger = logging.getLogger(__name__)


class GP_356(Instrument):
    """
    A driver for the Grandville Phillips Ion Gauge
    """

    def __init__(
        self,
        connection_addr: str,
    ):
        super().__init__(
            connection_addr,
            default_port=7777,
        )

        self.manufacturer = "MKS"
        self.model = "GP365"

        self.ins_add = "#02"  # The address setting on the instrument
        self.check_connection_commands = [self.ins_add + "IGS"]

        self.termination = "\r"

        self.add_parameter(
            "Read_State",
            read_command="{self.ins_add}IGS",
            set_command="",
            dummy_return="",
        )
        self.add_parameter(
            "Read_Pressure",
            read_command="{self.ins_add}RD",
            set_command="",
            dummy_return="",
        )

        self.add_parameter(
            "Read_Emission",
            read_command="{self.ins_add}RE",
            set_command="",
            dummy_return="",
        )

        self.add_parameter(
            "Read_Filament",
            read_command="{self.ins_add}RF",
            set_command="",
            dummy_return="",
        )

        self.add_parameter(
            "Read_Unit",
            read_command="{self.ins_add}SU",
            set_command="",
            dummy_return="",
        )
