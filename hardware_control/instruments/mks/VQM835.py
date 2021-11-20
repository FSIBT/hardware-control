"""
Instrument driver class to handle Granville Phillips 356 Series Ion gauge for pressure readout.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with VQM835s
connection works over proprietary driver, with "tasks"
"""

import logging
import numpy as np

from ...base import Instrument

logger = logging.getLogger(__name__)


class VQM835(Instrument):
    """Grandville Phillips Ion Gauge instrument class.

    Instrument home page: https://www.mksinst.com/f/835-vacuum-quality-monitor
    The instrument uses USB-A and is controlled using the pyvisa library.

    The MKS 835VQM show as a virtual port device and invisible for list_resources
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

        # define the readout data type
        self.dt16 = np.dtype(np.uint16)
        self.dt16 = self.dt16.newbyteorder("<")
        self.dt32 = np.dtype(np.float32)
        self.dt32 = self.dt32.newbyteorder("<")

        self.add_command("ENTRY_PLATE", "INST ENTR")
        self.add_command("FILAMENT", "INST FIL")
        self.add_command("MSPECTROMETRY", "INST MSP")
        self.add_command("EMULTIPLIER", "INST EMUL")
        self.add_command("ELECTRON_METER", "INST EMEL")
        self.add_command("CLEAN_ALL", "*CLS")

        ## get the total pressure from the external source (Ion Gauge)
        self.add_command("TOTAL_PRESSURE", "INST ETPR\rOUTP ON\rMEAS:PRES?")

        ## Setting the ionizer parameters
        self.add_parameter(
            "FILAMENT_EMISSION",
            read_command="INST FIL\rMEAS:CURR?",
            set_command="INST FIL\rSOUR:MOD ADJ\rSOUR:CURR",
            dummy_return="",
        )

        ## Setting up the mass filiter
        self.add_parameter(
            "REPELLER",
            read_command="INST REP\rMEAS:VOLT?",
            set_command="INST REP\rSOUR:VOLT",
            dummy_return="",
        )

        self.add_parameter(
            "RF_APM",
            read_command="INST CUPS\rMEAS:VOLT?",
            set_command="INST CUPS\rSOUR:VOLT",
            dummy_return="",
        )

        self.add_parameter(
            "EXIT_PLATE",
            read_command="INST EXIT\rMEAS:VOLT?",
            set_command="INST EXIT\rSOUR:VOLT",
            dummy_return="",
        )

        ## Setting up the Detectors
        self.add_parameter(
            "EM_VOLTAGE",
            read_command="INST EMUL\rMEAS:VOLT?",
            set_command="INST EMUL\rSOUR:VOLT",
            dummy_return="",
        )

        self.add_parameter(
            "MASS_RANGE",
            read_command="INST MSP\rCONF:AMU?",
            set_command="INST MSP\rCONF:AMU",
            dummy_return="",
        )

        ## Setting up the Scans
        self.add_command("READOUT_SET", "FORM 1,1\rFORM?")
        self.add_command("SINGLE_MEASUREMENT", "INST MSP\rOUTP ON\rINIT\rFETC?")

        ## Store and load the trap settings
        self.add_command("STORE_SETTINGS", "MEM:STOR\rSYST:ERR:ALL?")
        self.add_command("LOAD_SETTINGS", "MEM:LOAD\rSYST:ERR:ALL?")
        self.add_command("FACTORY_SETTINGS", "MEM:LOAD FACT\rSYST:ERR:ALL?")

        ## Turn On/Off the MSP
        self.add_command("ON", "INST MSP\rOUTP ON\rSYST:ERR:ALL?")
        self.add_command("CLEAR_OFF", "INST MSP\rOUTP OFF\rSYST:ERR:ALL?")

        logger.warning("The VQM835 driver class is still under development.")

    def read_binary_chunk(self, nr_data, spaces):
        L = int(nr_data.decode("ascii"))
        nr = int(self.device.read_bytes(L).decode("ascii"))
        space = self.device.read_bytes(spaces)
        assert space == b" " * spaces
        data = self.device.read_bytes(nr)
        return data

    def read_binary_data(self):
        tmp = []
        for nr_bytes, nr_spaces in [(845, 2), (314, 2), (443, 1)]:
            data = self.device.read_bytes(nr_bytes)
            data = self.read_binary_chunk(data[-1:], nr_spaces)
            tmp.append(data)
        # read rest
        data = self.device.read_raw()
        assert data.endswith(b")))\r")

        noise = np.frombuffer(tmp[0], dtype=self.dt16, count=len(tmp[0]) // 2)
        counts = np.frombuffer(tmp[1], dtype=self.dt16, count=len(tmp[1]) // 2)
        amu = np.frombuffer(tmp[2], dtype=self.dt32, count=len(tmp[2]) // 4)
        return noise, counts, amu
