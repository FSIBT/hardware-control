"""Stanford Research Systems CIS200.

.. image:: /images/SRS_CIS.jpg
  :height: 200

See class definition for details.

"""

import logging

from ...base import Instrument

logger = logging.getLogger(__name__)


class SRS_CIS200(Instrument):
    """A driver for the Stanford Research Systems CIS200.

    Instrument home page: https://www.thinksrs.com/products/cis.html
    Manual: https://www.thinksrs.com/downloads/pdfs/manuals/CISm.pdf

    The instrument uses RS-232C and
    is controlled using the pyvisa library.
    """

    def __init__(
        self,
        instrument_name: str = "SRS_CIS200",
        connection_addr: str = "",
    ):

        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        self.manufacturer = "SRS"
        self.model = "CIS200"

        # Connection Specific Setting
        self._encoding = "ascii"

        # set the terminator
        self.read_termination = "\n\r"
        self.write_termination = "\r"
        self.delay = 2  # the RGA needs a long delay when setting values

        self.try_connect()
        self.config_serial(baud_rate=28800, stop_bits=20, data_bits=8, parity=0)

        # a bit of hack, this seems to work, but there seems to be some issue with already buffered data or something like this
        # Without it, the first query always got a timedout exception. For some reason adding the \r helps here, although we do
        # get a warning that the \r is already added by the driver.
        for i in range(3):
            try:
                self.device.query("ID?\r")
            except:
                pass
        # self.check_connection_commands = ["ID?", "IN0"]

        self.add_command("CALIBRATION_ALL", "CA")
        self.add_command("CALIBRATION", "CL")

        # Setting the ionizer parameters
        self.add_parameter(
            "FILAMENT_EMISSION",
            read_command="FL?",
            set_command="FL{}",
            dummy_return="0.1",
        )
        self.add_parameter(
            "EXTRACT_VOLTAGE",
            read_command="VF?",
            set_command="VF{}",
            dummy_return="50",
        )
        self.add_parameter(
            "ELECTRON_ENERGY",
            read_command="EE?",
            set_command="EE{}",
            dummy_return="70",
        )
        self.add_parameter(
            "ION_ENERGY",
            read_command="IE?",
            set_command="IE{}",
            dummy_return="8eV",
        )
        self.add_lookup(
            "ION_ENERGY",
            {
                "4eV": "0",
                "8eV": "1",
            },
        )

        # Setting up the Detectors
        self.add_parameter(
            "EM_VOLTAGE",
            read_command="HV?",
            set_command="HV{}",
            dummy_return="1400",
        )

        # Setting up the Scans
        self.add_parameter(
            "INITIAL_MASS",
            read_command="",
            set_command="MI{}",
            dummy_return="1",
        )
        self.add_parameter(
            "FINAL_MASS",
            read_command="",
            set_command="MF{}",
            dummy_return="51",
        )
        self.add_parameter(
            "SCAN_RATE",
            read_command="",
            set_command="NF{}",
            dummy_return="7",
        )  # Noise floor too
        self.add_parameter(
            "SCAN_STEPS",
            read_command="SA?",
            set_command="SA{}",
            dummy_return="10",
        )  # followed by the steps/amu
        self.add_parameter(
            "ANALOG_SCANS",
            read_command="",
            set_command="SC{}",
            dummy_return="1",
        )  # followed by the scan times
        self.add_parameter(
            "HISTOGRAM_SCANS",
            read_command="",
            set_command="HS{}",
            dummy_return="1",
        )  # followed by the Scan times
        self.add_parameter(
            "SINGLE_MEASUREMENT",
            read_command="",
            set_command="MR{}",
            dummy_return="18",
        )  # followed by the mass of the measurement
