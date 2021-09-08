"""R14xxET CAEN Power Supply

.. image:: /images/CAENR14xxET.jpg
  :height: 200

.. image:: /images/CAENR803x.jpg
  :height: 200


See class definition for details.

"""

import logging
from typing import Union

from ...base import Instrument

logger = logging.getLogger(__name__)


def parse_instrument_response(value: str) -> Union[str, None]:
    value = value.strip(r"\r")
    if value.endswith("CMD:OK"):
        return None
    return value[value.find("VAL:") + 4 :]


def create_parse_status(bitmask):
    """Create a function that parses the CAEN status."""

    def parse_status(value: str) -> int:
        value = parse_instrument_response(value)
        if value is None:
            return None
        value = int(float(value))
        return value & bitmask

    return parse_status


class Caen_14xxET(Instrument):
    """CAEN high voltage power supplies.

    This backend provides controls for CAEN power supplies.
    Tested instruments include: .

    """

    def __init__(
        self,
        instrument_name,
        connection_addr,
    ):

        super().__init__(
            instrument_name=instrument_name, connection_addr=connection_addr
        )

        # The instrument has channels 1-8
        self.chan_nums = list(range(1, 9))
        self.max_V = [None] * len(self.chan_nums)
        self.max_I = [None] * len(self.chan_nums)

        self.status_bits = {
            "ON_OFF": 1,
            "RAMPING_UP": 2,
            "RAMPING_DOWN": 4,
            "OVER_CURRENT": 8,
            "OVER_VOLTAGE": 16,
            "UNDER_VOLTAGE": 32,
            "MAX_VOLTAGE": 64,
            "TRIPPED": 128,
            "OVER_POWER": 256,
            "OVER_TEMPERATURE": 512,
            "DISABLED": 1024,
            "KILL": 2048,
            "INTERLOCKED": 4096,
            "CALIBRATION_ERROR": 8192,
        }

        for channel in self.chan_nums:
            self.add_parameter(
                f"CH{channel}_V_MAX",
                read_command=None,
                set_command=None,
                post_hooks=[lambda x: self.set_V_max(channel, x)],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_I_MAX",
                read_command=None,
                set_command=None,
                post_hooks=[lambda x: self.set_I_max(channel, x)],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_ENABLE",
                read_command=f"CH{channel}_ENABLE?",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:{{}}",
                dummy_return="",
            )
            self.add_lookup(f"CH{channel}_ENABLE", {"True": "ON", "False": "OFF"})

            self.add_parameter(
                f"CH{channel}_I_SET",
                read_command=f"$BD:00,CMD:SET,CH:{channel},PAR:ISET,VAL:{{}}",
                pre_hook=[
                    write_to_log(f"Iset called with value {value}"),
                    lambda value: min(value, self.max_I[channel - 1])
                    if self.max_I[channel - 1] is not None
                    else None,
                    format_float(),
                    scaling_converter(1e6),
                ],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_V_SET",
                read_command=f"$BD:00,CMD:SET,CH:{channel},PAR:VSET,VAL:{{}}",
                pre_hook=[
                    write_to_log(f"Vset called with value {value}"),
                    lambda value: min(value, self.max_V[channel - 1])
                    if self.max_V[channel - 1] is not None
                    else None,
                ],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_V_OUT",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:VMON",
                post_hook=[
                    parse_instrument_response,
                    lambda value: value.strip("\\nr"),
                ],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_I_OUT",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:IMON",
                post_hook=[
                    parse_instrument_response,
                    lambda value: value.strip("\\nr"),
                    format_float(),
                    scaling_converter(1e6),
                ],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_I_SET",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:ISET",
                post_hook=[
                    parse_instrument_response,
                    lambda value: value.strip("\\nr"),
                    format_float(),
                    scaling_converter(1e6),
                ],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_V_SET",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:VSET",
                post_hook=[
                    parse_instrument_response,
                    lambda value: value.strip("\\nr"),
                ],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_STATUS",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    parse_instrument_response,
                    format_int(),
                    lambda value: self.return_status(value),
                ],
                dummy_return="",
            )

            for bit_name, bit in self.status.items():
                self.add_parameter(
                    "CH{channel}_{bit_name}",
                    read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                    post_hook=[create_parse_status(bit)],
                    dummy_return="",
                )

    def set_V_max(self, channel, value):
        self.max_V[channel - 1] = float(value)

    def set_I_max(self, channel, value):
        self.max_I[channel - 1] = float(value)

    def return_status(value):
        status = {
            "ON_OFF": value & 1,
            "RAMPING_UP": value & 2,
            "RAMPING_DOWN": value & 4,
            "OVER_CURRENT": value & 8,
            "OVER_VOLTAGE": value & 16,
            "UNDER_VOLTAGE": value & 32,
            "MAX_VOLTAGE": value & 64,
            "TRIPPED": value & 128,
            "OVER_POWER": value & 256,
            "OVER_TEMPERATURE": value & 512,
            "DISABLED": value & 1024,
            "KILL": value & 2048,
            "INTERLOCKED": value & 4096,
            "CALIBRATION_ERROR": value & 8192,
        }

        return status
