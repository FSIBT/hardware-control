"""
Control class to handle Granville Phillips 356 Series Ion gauge for preesure readout.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with VQM835s
connection works over proprietary driver, with "tasks"
"""

import logging
import random

import numpy as np

from ...base import Instrument

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
        self.add_command("CLEAN_ALL", "*CLS")

        # Setting the ionizer parameters
        self.add_parameter(
            "FILAMENT_EMISSION",
            read_command="FL?",
            set_command="FL{}",
            dummy_return="",
        )
        self.add_parameter(
            "EXTRACT_VOLTAGE",
            read_command="VF?",
            set_command="VF{}",
            dummy_return="",
        )
        self.add_parameter(
            "ELECTRON_ENERGY",
            read_command="EE?",
            set_command="EE{}",
            dummy_return="",
        )
        self.add_parameter(
            "ION_ENERGY",
            read_command="IE?",
            set_command="IE{}",
            dummy_return="",
        )

        # Setting up the Detectors
        self.add_parameter(
            "EM_VOLTAGE",
            read_command="HV?",
            set_command="HV{}",
            dummy_return="",
        )

        # Setting up the Scans
        self.add_parameter(
            "INITIAL_MASS",
            read_command="",
            set_command="MI{}",
            dummy_return="",
        )
        self.add_parameter(
            "FINAL_MASS",
            read_command="",
            set_command="MF{}",
            dummy_return="",
        )
        self.add_parameter(
            "SCAN_RATE",
            read_command="",
            set_command="NF{}",
            dummy_return="",
        )  # Noise floor too
        self.add_parameter(
            "SCAN_STEPS",
            read_command="SA?",
            set_command="SA{}",
            dummy_return="",
        )  # followed by the steps/amu
        self.add_parameter(
            "ANALOG_SCANS",
            read_command="",
            set_command="SC{}",
            dummy_return="",
        )  # followed by the scan times
        self.add_parameter(
            "HISTOGRAM_SCANS",
            read_command="",
            set_command="HS{}",
            dummy_return="",
        )  # followed by the Scan times
        self.add_parameter(
            "SINGLE_MEASUREMENT",
            read_command="",
            set_command="MR{}",
            dummy_return="",
        )
