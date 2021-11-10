"""
Control class to handle Granville Phillips 356 Series Ion gauge for preesure readout.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with VQM835s
connection works over proprietary driver, with "tasks"
"""

import logging

from ...base import Instrument

logger = logging.getLogger(__name__)


class VQM835(Instrument):
    """Grandville Phillips Ion Gauge instrument class.

    Instrument home page: https://www.mksinst.com/f/835-vacuum-quality-monitor
    The instrument uses USB-A and is controlled using the pyvisa library.
    """

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

        self._termination = "\r"

        self.add_command("ENTRY_PLATE", "INST ENTR")
        self.add_command("FILAMENT", "INST FIL")
        self.add_command("MSPECTROMETRY", "INST MSP")
        self.add_command("EMULTIPLIER", "INST EMUL")
        self.add_command("ELECTRON_METER", "INST EMEL")
        self.add_command("CLEAN_ALL", "*CLS")

        ## get the total pressure from the external source (Ion Gauge)
        self.add_command("TOTAL_PRESSURE", "INST ETPR;OUTP ON;MEAS:PRES?")

        ## Setting the ionizer parameters
        self.add_parameter(
            "FILAMENT_EMISSION",
            read_command="INST FIL;MEAS:CURR?",
            set_command="INST FIL;SOUR:MOD ADJ;SOUR:CURR",
            dummy_return="",
        )

        ## Setting up the Detectors
        self.add_parameter(
            "EM_VOLTAGE",
            read_command="INST EMUL;MEAS:VOLT",
            set_command="INST EMUL;SOUR:VOLT",
            dummy_return="",
        )

        ## Setting up the Scans
        self.add_command("SINGLE_MEASUREMENT", "INST MSP;OUTP ON;INIT;FETC?")

        ## Store and load the trap settings
        self.add_command("STORE_SETTINGS", "MEM:STOR;SYST:ERR:ALL?")
        self.add_command("LOAD_SETTINGS", "MEM:LOAD;SYST:ERR:ALL?")
        self.add_command("FACTORY_SETTINGS", "MEM:LOAD FACT;SYST:ERR:ALL?")
