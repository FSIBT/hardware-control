"""
.. image:: /images/CAENR14xxET.jpg
  :height: 200

.. image:: /images/CAENR803x.jpg
  :height: 200

"""

import logging
import numpy as np


from ...base import Instrument
from ...base.hooks import (
    format_float,
    scaling_converter,
    format_int,
)

logger = logging.getLogger(__name__)


def _parse_instrument_response(value: str) -> str | None:
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
        return value & bitmask > 0

    return parse_status


class Caen_RSeries(Instrument):
    """CAEN R Series high voltage power supply instrument class.

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
        instrument_name: str = "Caen_RSeries",
        connection_addr: str = "",
        num_channels: int = 16,
    ):
        super().__init__(
            instrument_name=instrument_name, connection_addr=connection_addr
        )

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

        for channel in range(num_channels):
            self.add_parameter(
                f"CH{channel}_ENABLE",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:{{}}",
                post_hooks=[
                    _create_parse_status(1),
                    lambda value: "ON" if value == 1 else "OFF",
                ],
                dummy_return="False",
            )
            self.add_lookup(f"CH{channel}_ENABLE", {"True": "ON", "False": "OFF"})

            self.add_parameter(
                f"CH{channel}_V_MAX",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:MAXV",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:MAXV,VAL:{{}}",
                post_hooks=[
                    _parse_instrument_response,
                ],
                dummy_return="20.0",
            )

            self.add_parameter(
                f"CH{channel}_I_MAX",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:ISET",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:ISET,VAL:{{}}",
                dummy_return="25.0",
            )

            self.add_parameter(
                f"CH{channel}_RAMP_UP",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:RUP",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:RUP,VAL:{{}}",
                dummy_return="13.0",
            )

            self.add_parameter(
                f"CH{channel}_RAMP_DOWN",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:RDW",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:RDW,VAL:{{}}",
                dummy_return="13.0",
            )

            self.add_parameter(
                f"CH{channel}_RAMP_UPDOWN",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:RUP",  # not sure what the best to do here is
                set_command=self._set_ramp_up_down(channel),
                dummy_return="13.0",
            )

            self.add_parameter(
                f"CH{channel}_V_OUT",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:VMON",
                post_hooks=[
                    _parse_instrument_response,
                ],
                dummy_return="10.0",
            )

            self.add_parameter(
                f"CH{channel}_I_OUT",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:IMON",
                post_hooks=[
                    _parse_instrument_response,
                    format_float(),
                    scaling_converter(1e-6),
                ],
                dummy_return="15.0",
            )

            self.add_parameter(
                f"CH{channel}_V_SET",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:VSET",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:VSET,VAL:{{}}",
                post_hooks=[_parse_instrument_response, format_float(".3e")],
                dummy_return="10.0",
            )

            self.add_parameter(
                f"CH{channel}_I_SET",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:ISET",
                set_command=f"$BD:00,CMD:SET,CH:{channel},PAR:ISET,VAL:{{}}",
                pre_hooks=[
                    scaling_converter(1e6),
                ],
                post_hooks=[
                    _parse_instrument_response,
                    scaling_converter(1e-6),
                ],
                dummy_return="15.0",
            )

            self.add_parameter(
                f"CH{channel}_STATUS",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hooks=[
                    _parse_instrument_response,
                    format_int,
                    self._return_status,
                ],
                dummy_return="",
            )

            for bit_name, bit in self.status.items():
                self.add_parameter(
                    f"CH{channel}_{bit_name}",
                    read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                    post_hooks=[_create_parse_status(bit)],
                    dummy_return=self.dummy_status_return,
                )

    def dummy_status_return(self):
        value = bool(np.random.randint(10))
        return "True" if value != 1 else "False"

    def _set_ramp_up_down(self, channel):
        """Set both up and down ramp values.

        In Volts/second
        """

        def set_ramp_value(value):
            self.set_value(f"CH{channel}_RAMP_UP", value)
            self.set_value(f"CH{channel}_RAMP_DOWN", value)

        return set_ramp_value

    def _return_status(self, value):
        value = int(value)
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

    def write(self, command: str):
        """The write commands on the CAEN always send back a '#CMD:OK' that needs to be read back."""
        self.query(command)
