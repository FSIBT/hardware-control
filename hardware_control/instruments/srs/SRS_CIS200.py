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

        self.add_command("CA", "CL")

        # Setting the ionizer parameters
        self.add_parameter(
            "Filament_Emission",
            read_command="FL?",
            set_command="FL{}",
            dummy_return="",
        )
        self.add_parameter(
            "Extract_Voltage",
            read_command="VF?",
            set_command="VF{}",
            dummy_return="",
        )
        self.add_parameter(
            "Electron_Energy",
            read_command="EE?",
            set_command="EE{}",
            dummy_return="",
        )
        self.add_parameter(
            "Ion_Energy",
            read_command="IE?",
            set_command="IE{}",
            dummy_return="",
        )

        # Setting up the Detectors
        self.add_parameter(
            "EM_voltage",
            read_command="HV?",
            set_command="HV{}",
            dummy_return="",
        )

        # Setting up the Scans
        self.add_parameter(
            "Initial_Mass",
            read_command="",
            set_command="MI{}",
            dummy_return="",
        )
        self.add_parameter(
            "Final_Mass",
            read_command="",
            set_command="MF{}",
            dummy_return="",
        )
        self.add_parameter(
            "Scan_Rate",
            read_command="",
            set_command="NF{}",
            dummy_return="",
        )  # Noise floor too
        self.add_parameter(
            "Scan_Steps",
            read_command="SA?",
            set_command="SA{}",
            dummy_return="",
        )  # followed by the steps/amu
        self.add_parameter(
            "Analog_Scans",
            read_command="",
            set_command="SC{}",
            dummy_return="",
        )  # followed by the scan times
        self.add_parameter(
            "Histogram_Scans",
            read_command="",
            set_command="HS{}",
            dummy_return="",
        )  # followed by the Scan times
        self.add_parameter(
            "Single_Measurement",
            read_command="",
            set_command="MR{}",
            dummy_return="",
        )  # followed by the mass of the measurement
