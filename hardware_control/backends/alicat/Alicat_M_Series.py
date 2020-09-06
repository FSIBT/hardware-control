"""Alicat M-Series gas flow meters.

.. image:: /images/Alicat_M-Series.jpg
  :height: 200

See class definition for details.

"""

import logging
import random

from ..base import Backend, ensure_online
from ..utility import (
    converter_ulong_to_IEEE754,
    converter_IEEE754_to_ulong,
)

logger = logging.getLogger(__name__)


class Alicat_M_Series(Backend):
    """A driver for Alicat M-Series flow controllers.

    Instrument home page: https://www.alicat.com/product/mass-flow-meters

    The instrument is controlled via modbus over ethernet.

    """

    def __init__(self, connection_addr):

        super().__init__(
            instrument_name="AlicatMSeries",
            connection_addr=connection_addr,
            default_port=0,  # modbus instrument need to set a default_port to an integer
        )
        self.connection_type = Backend.MODBUS
        self.error_count = 0

    @ensure_online
    def update_setting(self, setting: str, value):

        if self.dummy:
            return f"{setting}={value}"

        try:
            if setting in ["RATE", "FLOW"]:
                i = converter_IEEE754_to_ulong(float(value))
                a = i >> 16
                b = i & ((1 << 16) - 1)
                r = self.device.write_registers(address=1009, values=[a, b], unit=0)

                self.error_count = 0
                return f"{setting}={value}"
        except Exception:
            logger.error(
                f"An error occured in Alicat flowmeter when sending command"
                f" {setting}={value} to the instrument.",
                exc_info=True,
            )
            self.error_count += 1

        if self.error_count > 4:
            self.online = False

    def command(self, cmd: str):
        if cmd == "RATE?":
            flow = self.query(address=1208)
            return f"RATE={flow}"
        if cmd == "PRESSURE?":
            pressure = self.query(address=1202)
            return f"PRESSURE={pressure}"

    @ensure_online
    def query(self, address: int):
        if self.dummy:
            return random.randint(0, 10)

        try:
            r = self.device.read_input_registers(count=2, address=address, unit=0)
            a, b = r.registers
            value = (a << 16) + b
            value = converter_ulong_to_IEEE754(value)
            return value
        except Exception:
            logger.error(
                f"An error occured in {self.ID} when querying the modbus addres {address}.",
                exc_info=True,
            )
            self.online = False
