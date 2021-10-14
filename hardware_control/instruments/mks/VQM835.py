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


class VQM835(Instrument):
    """Grandville Phillips Ion Gauge instrument class."""

    def __init__(
        self,
        instrument_name: str = "VQM835",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=7777,
        )

        self.manufacturer = "MKS"
        self.model = "VQM835"

        self.check_connection_commands = ["*IDN?"]

        self.termination = "\r"

        self.add_command("ENTRY_PLATE", "INST ENTR")
        self.add_command("FILAMENT", "INST FIL")
        self.add_command("MSPECTROMETRY", "INST MSP")
        self.add_command("EMULTIPLIER", "INST EMUL")
        self.add_command("ELECTRON_METER", "INST EMEL")
