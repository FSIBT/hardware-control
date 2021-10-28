"""
.. image:: /images/CAENR14xxET.jpg
  :height: 200

.. image:: /images/CAENR803x.jpg
  :height: 200

"""

import logging
from typing import Union
from numpy import Infinity

from ...base import Instrument
from ...base.hooks import (
    format_float,
    scaling_converter,
    format_int,
    last_n_values_converter,
    range_validator,
)

logger = logging.getLogger(__name__)


def _parse_instrument_response(value: str) -> Union[str, None]:
    value = value.strip(r"\r")
    if value.endswith("CMD:OK"):
        return None
    return value[value.find("VAL:") + 4 :]


def _create_parse_status(bitmask):
    """Create a function that parses the CAEN status."""

    def parse_status(value: str) -> int:
        value = _parse_instrument_response(value)
        if value is None:
            return None
        value = int(float(value))
        return value & bitmask

    return parse_status


class Caen_14xxET(Instrument):
    """CAEN R14xxET high voltage power supply instrument class.

    PARAMETERS
        * CH<X>_ENABLE (*bool*)
            * On/off status of channel 'X'.
        * CH<X>_V_MAX (*float*)
            * Maximum voltage for channel 'X'.
        * CH<X>_I_MAX (*float*)
            * Maximum current for channel 'X'.
        * CH<X>_V_OUT (*float*)
            * Current voltage of channel 'X'.
        * CH<X>_I_OUT (*float*)
            * Current current of channel 'X'.
        * CH<X>_V_SET (*float*)
            * New voltage to set for channel 'X'.
        * CH<X>_I_SET (*float*)
            * New current to set for channel 'X'.
        * CH<X>_STATUS (*dict*)
            * Dictionary of channel 'X' status parameters.
        * CH<X>_<bit> (*ON_OFF*, *RAMPING_UP*, *RAMPING_DOWN*, *OVER_CURRENT*, *OVER_VOLTAGE*, *UNDER_VOLTAGE*, *MAX_VOLTAGE*, *TRIPPED*, *OVER_POWER*, *OVER_TEMPERATURE*, *DISABLED*, *KILL*, *INTERLOCKED*, *CALIBRATION_ERROR*)
            * Individual status parameter for channel 'X'.

    """

    def __init__(
        self,
        instrument_name: str = "CAEN_14xxET",
        connection_addr: str = "",
    ):

        super().__init__(
            instrument_name=instrument_name, connection_addr=connection_addr
        )

        # The instrument has channels 1-8
        self.chan_nums = list(range(1, 9))
        self.max_V = [None] * len(self.chan_nums)
        self.max_I = [None] * len(self.chan_nums)

        self.status = {
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
                f"CH{channel}_ENABLE",
                read_command=f"CH{channel}_ENABLE?",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:{{}}",
                dummy_return="False",
            )
            self.add_lookup(f"CH{channel}_ENABLE", {"True": "ON", "False": "OFF"})

            self.add_parameter(
                f"CH{channel}_V_MAX",
                read_command=lambda: self._read_V_max(channel),
                set_command=lambda x: self._set_V_max(channel, x),
                dummy_return="20.0",
            )

            self.add_parameter(
                f"CH{channel}_I_MAX",
                read_command=lambda: self._read_I_max(channel),
                set_command=lambda x: self._set_I_max(channel, x),
                dummy_return="25.0",
            )

            self.add_parameter(
                f"CH{channel}_V_OUT",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:VMON",
                post_hooks=[
                    _parse_instrument_response,
                    lambda value: value.strip("\\nr"),
                ],
                dummy_return="10.0",
            )

            self.add_parameter(
                f"CH{channel}_I_OUT",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:IMON",
                post_hooks=[
                    _parse_instrument_response,
                    lambda value: value.strip("\\nr"),
                    format_float(),
                    scaling_converter(1e6),
                ],
                dummy_return="15.0",
            )

            self.add_parameter(
                f"CH{channel}_V_SET",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:VSET",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:VSET,VAL:{{}}",
                pre_hooks=[range_validator(-Infinity, self._read_V_max(channel))],
                post_hooks=[
                    _parse_instrument_response,
                    lambda value: value.strip("\\nr"),
                    last_n_values_converter(6),
                ],
                dummy_return="10.0",
            )

            self.add_parameter(
                f"CH{channel}_I_SET",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:ISET",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:ISET,VAL:{{}}",
                pre_hooks=[range_validator(-Infinity, self._read_I_max(channel))],
                post_hooks=[
                    _parse_instrument_response,
                    lambda value: value.strip("\\nr"),
                    last_n_values_converter(7),
                    format_float(),
                    scaling_converter(1e6),
                ],
                dummy_return="15.0",
            )

            self.add_parameter(
                f"CH{channel}_STATUS",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hooks=[
                    _parse_instrument_response,
                    format_int,
                    lambda value: self._return_status(value),
                ],
                dummy_return="",
            )

            for bit_name, bit in self.status.items():
                self.add_parameter(
                    f"CH{channel}_{bit_name}",
                    read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                    post_hooks=[_create_parse_status(bit)],
                    dummy_return="",
                )

    def _read_V_max(self, channel):
        return self.max_V[channel - 1]

    def _set_V_max(self, channel, value):
        self.max_V[channel - 1] = float(value)

    def _read_I_max(self, channel):
        return self.max_I[channel - 1]

    def _set_I_max(self, channel, value):
        self.max_I[channel - 1] = float(value)

    def _return_status(value):
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
