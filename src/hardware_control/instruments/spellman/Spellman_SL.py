"""
.. image:: /images/SpellmanSL120P300.png
  :height: 200

"""

import logging
from typing import Union
import numpy as np


from ...base import Instrument
from ...base.hooks import scaling_converter, format_int

logger = logging.getLogger(__name__)

"""Reads out: HV, current, interlock status and Sets the HV"""


class Spellman_SL(Instrument):
    """Spellman SL 120KV 300W high voltage power supply instrument class.

    PARAMETERS
        * CH0_V_OUT (*string*)
            * Current voltage of channel 0.
        * CH0_I_OUT (*string*)
            * Current current of channel 0.
        * CH0_V_SET (*string*)
            * New voltage to set for channel 0.
        * CH0_I_SET (*string*)
            * New current to set for channel 0.
        * CH0_STATUS (*dict*)
            * Dictionary of channel 0 status parameters.
        * CH0_<bit> (*INTERLOCK*, *HV_ON*, *OVER_VOLTAGE*, *OVER_CURRENT*, *OVER_POWER*, *REGULATOR_ERROR*, *ARC_FAULT*, *OVER_TEMP*, *ADJUSTABLE_OVERLOAD*, *SYSTEM_FAULT*, REMOTE_LOCAL*)
            * Individual status parameter for channel 0.

    """

    """ip address: 192.168.10.61"""

    def __init__(
        self,
        instrument_name: str = "Spellman_SL",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name, connection_addr=connection_addr
        )

        self.max_V = 120
        self.max_I = 2.5

        self.status = {
            "INTERLOCK_CLOSED": 1,
            "HV_ON": 2,
            "OVER_VOLTAGE": 3,
            "OVER_CURRENT": 4,
            "OVER_POWER": 5,
            "REGULATOR_ERROR": 6,
            "ARC_FAULT": 7,
            "OVER_TEMP": 8,
            "ADJUSTABLE_OVERLOAD": 9,
            "SYSTEM_FAULT": 10,
            "REMOTE_MODE": 11,
        }

        COMMANDS = {
            "CH0_HV_ON": f"{chr(2)}99,{chr(3)}",
            "CH0_HV_OFF": f"{chr(2)}98,{chr(3)}",
        }
        for k, v in COMMANDS.items():
            self.add_command(k, v)

        self.add_parameter(
            "CH0_V_READ",
            read_command=f"{chr(2)}14,{chr(3)}",
            post_hooks=[scaling_converter(120 / 4095), format_int],
            dummy_return="20",
        )

        self.add_parameter(
            "CH0_I_READ",
            read_command=f"{chr(2)}15,{chr(3)}",
            post_hooks=[scaling_converter(2.5 / 4095)],
            dummy_return="1",
        )

        # spellman needs to be in remote mode to set voltage/current
        # can be changed using front dials
        # voltage has to be int
        self.add_parameter(
            "CH0_V_SET",
            set_command=f"{chr(2)}10,{{}},{chr(3)}",
            pre_hooks=[
                self.voltage_validator(self.max_V),
                scaling_converter(4095 / 120),
                format_int,
            ],
        )

        self.add_parameter(
            "CH0_I_SET",
            set_command=f"{chr(2)}11,{{}},{chr(3)}",
            pre_hooks=[
                self.current_validator(self.max_I),
                scaling_converter(4095 / 2.5),
                format_int,
            ],
        )

        self.add_parameter(
            "CH0_STATUS",
            read_command=f"{chr(2)}32,{chr(3)}",
            post_hooks=[
                self.return_status(),
            ],
            dummy_return="",
        )

        for param_name, pos in self.status.items():
            self.add_parameter(
                f"CH0_{param_name}",
                read_command=f"{chr(2)}32,{chr(3)}",
                post_hooks=[
                    self.create_parse_status(pos),
                    lambda value: "TRUE" if value == "1" else "FALSE",
                ],
                dummy_return=self.dummy_status_return,
            )

    def voltage_validator(self, value_max):
        def validator(value):
            value = float(value)
            if value < 0:
                return 0
            return min(value, value_max)

        return validator

    def current_validator(self, value_curr):
        def validator(value):
            value = float(value)
            if value < 0:
                return 0
            return min(value, value_curr)

        return validator

    def create_parse_status(self, pos):
        def status_value(value):
            return value[pos]

        return status_value

    def dummy_status_return(self):
        value = bool(np.random.randint(10))
        return "True" if value != 1 else "False"

    def read_package(self):
        """Read a string from the instrument.

        This string consists of:
        ASCII STX (Start of message)
        2 ASCII numbers for command
        , SCII 0x2C character
            One or more ASCII data strings separated by commas
            and possible ,$ indicating message was received successfully
            or EC error 1: Wrong number of parameters or parameter out of range
                        2: Parsing error or invalid command code.
        ASCII ETX (0x03) End of message

        Example: set KV to 1024: <STX>10,1024,<ETX>

        """
        # read power supply's return value from after start char to before end char
        value = self.device.recv(200)
        value = str(value)[6:-6].split(",")
        # response message has comma after STX only if error
        if value[0] == "":
            if value[0] == "1":
                logger.error("Wrong number of parameters or parameter out of range")
                return "Error, check log"
            else:
                logger.error("Parsing error or invalid command code.")
                return value
        # voltage or current reads only have one value, return as float to scale
        if value[0] == "14" or value[0] == "15":
            return float(value[1])
        # only other option is status read so return list
        return value

    def write(self, command):
        self.device.send(command.encode())
        x = self.read_package()
        return x

    def query(self, command):
        x = self.write(command)
        return x

    def return_status(self):
        def status_dict(value):
            # first index is get status command (32), ignore
            # Arguments: 1: HV on 0: HV off
            status = {
                # Interlock closed : 1 Interlock open : 0
                "INTERLOCK_CLOSED": value[1],
                # HV on: 1 HV off: 0
                "HV_ON": value[2],
                "OVER_VOLTAGE": value[3],
                "OVER_CURRENT": value[4],
                "OVER_POWER": value[5],
                "REGULATOR_ERROR": value[6],
                "ARC_FAULT": value[7],
                "OVER_TEMP": value[8],
                "ADJUSTABLE_OVERLOAD": value[9],
                "SYSTEM_FAULT": value[10],
                # Remote mode : 1 Local mode : 0
                "REMOTE_MODE": value[11],
            }
            return status

        return status_dict