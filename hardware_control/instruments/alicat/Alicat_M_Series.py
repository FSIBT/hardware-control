"""Alicat M-Series gas flow meters.

.. image:: /images/Alicat_M-Series.jpg
  :height: 200

See class definition for details.

"""

import random

from ...base import Instrument
from ..utility import (
    converter_ulong_to_IEEE754,
    converter_IEEE754_to_ulong,
)


def IEEE754_converter_to_ulong_pair(value):
    i = converter_IEEE754_to_ulong(float(value))
    a = i >> 16
    b = i & ((1 << 16) - 1)
    return [a, b]


def modbus_registers_to_float(r):
    a, b = r.registers
    value = (a << 16) + b
    value = converter_ulong_to_IEEE754(value)
    return value


class Alicat_M_Series(Instrument):
    """A driver for Alicat M-Series flow controllers.

    Instrument home page: https://www.alicat.com/product/mass-flow-meters

    The instrument is controlled via modbus over ethernet.

    """

    def __init__(
        self,
        instrument_name: str = "ALICAT_M",
        connection_addr: str = "",
    ):

        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=0,  # modbus instrument need to set a default_port to an integer
        )
        self.connection_type = Instrument.MODBUS
        self.error_count = 0
        self.unit = 0

        self.add_parameter(
            "RATE",
            read_command=f"read_input_registers:1208:2:{self.unit}",
            set_command=f"write_coil:1009:{{}}:{self.unit}",
            pre_hooks=[IEEE754_converter_to_ulong_pair],
            post_hooks=[modbus_registers_to_float],
            dummy_return=lambda: random.randint(0, 10),
        )
        self.add_parameter(
            "PRESSURE",
            read_command=f"read_input_registers:1202:2:{self.unit}",
            post_hooks=[modbus_registers_to_float],
            dummy_return=lambda: random.randint(0, 10),
        )
