"""
Control class to handle vortran Stradus lasers.
"""

import logging
import random
import vortran_lbl as vortran

from ...base import Instrument

logger = logging.getLogger(__name__)


class Stradus(Instrument):
    """Stradus laser diode module class.

    Instrument home page: https://vortranlaser.com/product/stradus-laser-diode-modules/stradus-laser-diode-modules-blue/
    The instrument uses USB-A and is controlled using the pyusb library.

    """

    def __init__(
        self,
        instrument_name: str = "Stradus",
        connection_addr: str = "None",  # Communicate over USB
        laser_id: int = 0,
    ) -> None:
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )
        self.manufacturer = "Vortran"
        self.laser_id = laser_id

        # What about commands like ?C or on/off?

        self.add_command(
            command_name="ENABLE_POWER_CONTROL_MODE",
            command=lambda: self.device.enable_power_control_mode(),
        )

        self.add_command(
            command_name="ENABLE_CURRENT_CONTROL_MODE",
            command=lambda: self.device.enable_current_control_mode(),
        )

        self.add_parameter(
            parameter="CONTROL_MODE",
            read_command=lambda: str(getattr(self.device, "control_mode")),
            dummy_return="",
        )

        self.add_command(
            command_name="ENABLE_DELAY",
            command=lambda: self.device.enable_delay(),
        )

        self.add_command(
            command_name="DISABLE_DELAY",
            command=lambda: self.device.disable_delay(),
        )

        self.add_parameter(
            parameter="CURRENT",
            read_command=lambda: str(getattr(self.device, "current")),
            set_command=lambda x: setattr(self.device, "current", float(x)),
            dummy_return=lambda: str(random.randint(0, 1000)),
        )

        self.add_parameter(
            parameter="ON_OFF",
            read_command=lambda: str(getattr(self.device, "on_off")),
            dummy_return="0",
        )

        self.add_command(
            command_name="ON",
            command=lambda: self.device.on(),
        )

        self.add_command(
            command_name="OFF",
            command=lambda: self.device.off(),
        )

        self.add_parameter(
            parameter="POWER",
            read_command=lambda: str(getattr(self.device, "power")),
            set_command=lambda x: setattr(self.device, "power", float(x)),
            dummy_return="0",
        )

        self.add_parameter(
            parameter="PULSE_POWER",
            read_command=lambda: str(getattr(self.device, "pulse_power")),
            set_command=lambda x: setattr(self.device, "pulse_power", float(x)),
            dummy_return="0",
        )

        self.add_parameter(
            parameter="PULSED_POWER",
            read_command=lambda: str(getattr(self.device, "pulsed_power")),
            dummy_return="0",
        )

        self.add_command(
            command_name="DISABLE_PULSED_POWER",
            command=lambda: self.device.disable_pulsed_power(),
        )

        self.add_command(
            command_name="ENABLE_PULSED_POWER",
            command=lambda: self.device.enable_pulsed_power(),
        )

        self.add_parameter(
            parameter="BASE_PLATE_TEMPERATURE",
            read_command=lambda: str(getattr(self.device, "base_plate_temperature")),
            dummy_return="0",
        )

        self.add_parameter(
            parameter="COMPUTER_CONTROL",
            read_command=lambda: str(getattr(self.device, "computer_control")),
            dummy_return="1",
        )

        self.add_parameter(
            parameter="FAULT_CODE",
            read_command=lambda: getattr(self.device, "fault_code")[0],
            dummy_return="0",
        )

        self.add_parameter(
            parameter="FAULT_TEXT",
            read_command=lambda: " ".join(getattr(self.device, "fault_text")),
            dummy_return="DUMMY",
        )

        self.add_parameter(
            parameter="FIRMWARE_PROTOCAL",
            read_command=lambda: getattr(self.device, "firmware_protocol")[0],
            dummy_return="0.00.00",
        )

        self.add_parameter(
            parameter="FIRMWARE_VERSION",
            read_command=lambda: getattr(self.device, "firmware_version")[0],
            dummy_return="0.00.00",
        )

        self.add_parameter(
            parameter="INTERLOCK_STATUS",
            read_command=lambda: getattr(self.device, "interlock_status")[0],
            dummy_return="1",
        )

        self.add_parameter(
            parameter="LASER_HOURS",
            read_command=lambda: str(getattr(self.device, "laser_hours")),
            dummy_return="0",
        )

        self.add_parameter(
            parameter="LASER_ID",
            read_command=lambda: " ".join(getattr(self.device, "laser_id")),
            dummy_return="",
        )

        self.add_parameter(
            parameter="LASER_POWER_SETTING",
            read_command=lambda: str(getattr(self.device, "laser_power_setting")),
            dummy_return="0",
        )

        self.add_parameter(
            parameter="LASER_STATUS",
            read_command=lambda: " ".join(getattr(self.device, "laser_status")),
            dummy_return="",
        )

        self.add_parameter(
            parameter="LASER_WAVELENGTH",
            read_command=lambda: str(getattr(self.device, "laser_wavelength")),
            dummy_return="000",
        )

        self.add_parameter(
            parameter="LASER_MAX_POWER",
            read_command=lambda: str(getattr(self.device, "laser_max_power")),
            dummy_return="0.0",
        )

        self.add_parameter(
            parameter="OPTICAL_BLOCK_TEMPERATURE",
            read_command=lambda: getattr(self.device, "optical_block_temperature")[0],
            dummy_return="0.0",
        )

        self.add_parameter(
            parameter="RATED_POWER",
            read_command=lambda: getattr(self.device, "rated_power")[0],
            dummy_return="000",
        )

    def establish_connection(self):
        """Establish connection to Vortran Stradus laser via USB."""
        self.device = vortran.get_lasers()[self.laser_id]

        if self.device is None:
            raise ValueError(f"Laser at ID {self.laser_id} is not available")

        connection_result = self.device.open_connection()

        if connection_result:
            logger.info(
                f"Connection to Vortran Stradus ID {self.laser_id} was successful"
            )
        else:
            logger.error(
                f"Connection to Vortran Stradus ID {self.laser_id} was unsuccessful"
            )

        return connection_result
