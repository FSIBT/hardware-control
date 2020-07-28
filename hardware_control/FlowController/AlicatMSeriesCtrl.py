"""Alicat M-Series gas flow meters.

See class definition for details.

"""

import logging
import random

from hardware_control.base.HC_Backend import HC_Backend
from hardware_control.utility import (
    converter_ulong_to_IEEE754,
    converter_IEEE754_to_ulong,
)

logger = logging.getLogger(__name__)


class AlicatMSeriesCtrl(HC_Backend):
    """A driver for Alicat M-Series flow controllers.

    Instrument home page: https://www.alicat.com/product/mass-flow-meters

    The instrument is controlled via modbus over ethernet.

    """

    def __init__(self, connection_addr):

        super().__init__(
            instrument_name="AlicatMSeries", connection_addr=connection_addr
        )
        self.connection_type = HC_Backend.MODBUS
        self.error_count = 0

    def update_setting(self, setting: str, value):

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            return value

        try:
            if setting == "rate":
                i = converter_IEEE754_to_ulong(float(value))
                a = i >> 16
                b = i & ((1 << 16) - 1)
                r = self.device.write_registers(address=1009, values=[a, b], unit=0)

                self.error_count = 0
                return value
            if setting == "flow":
                i = converter_IEEE754_to_ulong(float(value))
                a = i >> 16
                b = i & ((1 << 16) - 1)
                r = self.device.write_registers(address=1009, values=[a, b], unit=0)

                self.error_count = 0
                return value
        except Exception:
            logger.error(
                "An error occured in Alicat flowmeter when sending command {setting}={value} to the instrument.",
                exc_info=True,
            )
            self.error_count += 1

        if self.error_count > 4:
            self.online = False

    def check_connection(self):
        """
        Verifies that the backend is able to communicate with the instrument by
        querying the instruments name and checking for a valid return value.

        Returns true if online, false if offline, and None if unknown connection
        type.
        """
        if self.connection_type == HC_Backend.MODBUS:
            try:
                r = self.device.read_input_registers(count=2, address=1208, unit=0)
                a, b = r.registers
                flow = (a << 16) + b
                flow = converter_ulong_to_IEEE754(flow)
                self.online = True
            except Exception:  # Not connected - reconnect
                logger.warning(
                    "Device connection check failed. Setting online to false.",
                    exc_info=True,
                )
                self.online = False
            return self.online
        return None

    def command(self, cmd: str):
        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            if cmd == "rate?":
                flow = random.randint(0, 10)
                return f"rate={flow}"
            if cmd == "pressure?":
                pressure = random.randint(0, 10)
                return f"pressure={pressure}"

        try:
            # Note: usually a self.dummy check would be here, but it is taken
            # care of in get_values() for the AlicanMSeriesFlowMeter
            if cmd == "rate?":
                r = self.device.read_input_registers(count=2, address=1208, unit=0)
                a, b = r.registers
                flow = (a << 16) + b
                flow = converter_ulong_to_IEEE754(flow)
                return f"rate={flow}"
            if cmd == "pressure?":
                r = self.device.read_input_registers(count=2, address=1202, unit=0)
                a, b = r.registers
                pressure = (a << 16) + b
                pressure = converter_ulong_to_IEEE754(pressure)
                return f"pressure={pressure}"
        except Exception:
            logger.error(
                f"An error occured in {self.ID} when sending command {cmd} to the instrument.",
                exc_info=True,
            )
            self.online = False
