"""R14xxET CAEN Power Supply

.. image:: /images/CAENR14xxET.jpg
  :height: 200

.. image:: /images/CAENR803x.jpg
  :height: 200


See class definition for details.

"""

import logging

from ...base import Instrument

logger = logging.getLogger(__name__)


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
        self.chan_nums = range(1, 9)
        self.max_V = [None] * len(self.num_channels)
        self.max_I = [None] * len(self.num_channels)

        logger.info(
            f"CAEN u_s received {setting}, {value} and interpreted chan={channel}, setting_X={setting_X}, value={value}"
        )

        for channel in self.chan_nums:

            def set_V_max():
                def setter(value):
                    self.max_V[channel - 1] = float(value)

            self.add_parameter(
                f"CH{channel}_V_MAX",
                read_command=None,
                set_command=None,
                post_hooks=[set_V_max()],
                dummy_return="",
            )

            def set_I_max():
                def setter(value):
                    self.max_I[channel - 1] = float(value)

            self.add_parameter(
                f"CH{channel}_I_MAX",
                read_command=None,
                set_command=None,
                post_hooks=[set_I_max()],
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
                    lambda value: value[value.find("VAL:") + 4 :],
                    lambda value: value.strip("\\nr"),
                ],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_I_OUT",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:IMON",
                post_hook=[
                    lambda value: value[value.find("VAL:") + 4 :],
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
                    lambda value: value[value.find("VAL:") + 4 :],
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
                    lambda value: value[value.find("VAL:") + 4 :],
                    lambda value: value.strip("\\nr"),
                ],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_STATUS",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_ON_OFF",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 1,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_RAMPING_UP",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 2,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_RAMPING_DOWN",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 4,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_OVER_CURRENT",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 8,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_OVER_VOLTAGE",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 16,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_UNDER_VOLTAGE",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 32,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_MAX_VOLTAGE",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 64,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_TRIPPED",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 128,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_OVER_POWER",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 256,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_OVER_TEMPERATURE",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 512,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_DISABLED",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 1024,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_KILL",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 2048,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_INTERLOCKED",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 4096,
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_CALIBRATION_ERROR",
                read_command=f"$BD:00,CMD:MON,CH:{channel},PAR:STAT",
                post_hook=[
                    lambda value: value.strip(r"\r"),
                    lambda value: None if value.endswith("CMD:OK") else value,
                    lambda value: value[value.find("VAL:") + 4 :],
                    format_int(),
                    lambda value: self.return_status(value),
                    lambda value: value & 8192,
                ],
                dummy_return="",
            )

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
