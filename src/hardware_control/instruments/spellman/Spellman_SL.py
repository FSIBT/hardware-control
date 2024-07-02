"""
.. image:: /images/SpellmanSL120P300.png
  :height: 200

"""
from dataclasses import dataclass
import logging
from typing import Union
import numpy as np


from ...base import Instrument
from ...base.hooks import(
    call_hooks,
)


logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Command:
    command: str

def _parse_instrument_response(value: str) -> Union[str, None]:
    value=value[1:-1].split(',')
    data_size=len(value)
    if data_size==1:
        if value[0]==1:
            string_return+="Error, check log"
            logging.ERROR("Wrong number of parameters or parameter out of range")
        else:
            string_return+="Error, check log"
            logging.ERROR("Parsing error or invalid command code.")
        return None
    return value


def _create_parse_status(pos):
    """Create a function that parses the Spellman status."""
    def parse_status(value: str) -> str:
        value = _parse_instrument_response(value)
        if value is None:
            return None
        return value[pos]

    return parse_status

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
            instrument_name=instrument_name, 
            connection_addr=connection_addr
        )

        self.max_V = 120
        self.max_I = 2.5

        self.status = {
            "INTERLOCK": 1,
            "HV_ON": 2,
            "OVER_VOLTAGE": 3,
            "OVER_CURRENT": 4,
            "OVER_POWER": 5,
            "REGULATOR_ERROR": 6,
            "ARC_FAULT": 7,
            "OVER_TEMP": 8,
            "ADJUSTABLE_OVERLOAD": 9,
            "SYSTEM_FAULT": 10,
            "REMOTE_LOCAL": 11,
        }

        READ_ONLY_COMMANDS = {
            "READ_VOLTAGE": Command(f"{chr(2)}14,{chr(3)}"),
            "READ_CURRENT": Command(f"{chr(2)}15,{chr(3)}"),
        }

        for k, v in READ_ONLY_COMMANDS.items():
            self.add_parameter(k, v)

        COMMANDS = {
            "CH0_HV_ON":  Command(f"{chr(2)}99,{chr(3)}"),
            "CH0_HV_OFF":  Command(f"{chr(2)}98,{chr(3)}"),
        }
        for k, v in COMMANDS.items():
            self.add_command(k, v)

        self.add_parameter(
            "CH0_V_SET",
            set_command=f"{chr(2)}10,{{}},{chr(3)}",
            pre_hooks=[
                self.voltage_validator(self.max_V),
            ],
            post_hooks=[
                _parse_instrument_response,
                lambda x: str(int(x))
            ],
            dummy_return="15.0",
        )
        self.add_parameter(
            "CH0_I_SET",
            set_command=f"{chr(2)}11,{{}},{chr(3)}",
            pre_hooks=[
                self.current_validator(self.max_I),
            ],
            post_hooks=[
                _parse_instrument_response,
                lambda x: str(int(x))
            ],
            dummy_return="1.0",
        )
        
        self.add_parameter(
            "CH0_STATUS",
            read_command=f"{chr(2)}32,{chr(3)}",
            post_hooks=[
                _parse_instrument_response,
                self._return_status,
            ],
            dummy_return="",
        )

        for param_name, pos in self.status.items():
            self.add_parameter(
                f"CH0_{param_name}",
                read_command=f"{chr(2)}32,{chr(3)}",
                post_hooks=[_create_parse_status(pos)],
                dummy_return=self.dummy_status_return,
            )

    def voltage_validator(self):
        def validator(value):
            value = int(value)
            if value < 0:
                return 0
            return min(value, 120)

        return validator
    
    def current_validator(self):
        def validator(value):
            value = float(value)
            if value < 0:
                return 0
            return min(value, 2.5)

        return validator
        

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
            string_return=""
            with open(self.device) as header:
                #read 'start of message' character first (ASCII 0x02)
                header.read(1)
                msg=header.read()
                #read the rest until end of message character (ASCII 0X03)
                msg=str(msg)[::-1].split(',')
                if msg[0]=='1':
                        logging.ERROR("Wrong number of parameters or parameter out of range")
                        return "Error, check log"
                if msg[0]=='2':
                        logging.ERROR("Parsing error or invalid command code.")
                        return "Error, check log"
                for ii in range(0, len(msg)):
                    if msg[ii]=='$':
                        msg+=" Successful: "
                    else:
                        msg+=ii+" "

            #remove extra space after last character
            return msg[0:len(msg)-1]

    def write_package(self, command: str):
        """Formats string to write to data to instrument.
        """
        package = command
        self.device.write_raw(package)


    def write(self, command):
        self.write_package(command.command)
        self.read_package()

    def _return_status(self, value):
        value = int(value)
        status = {
            "INTERLOCK": value & 1,
            "HV_ON": value & 2,
            "OVER_VOLTAGE": value & 3,
            "OVER_CURRENT": value & 4,
            "OVER_POWER": value & 5,
            "REGULATOR_ERROR": value & 6,
            "ARC_FAULT": value & 7,
            "OVER_TEMP": value & 8,
            "ADJUSTABLE_OVERLOAD": value & 9,
            "SYSTEM_FAULT": value & 10,
            "REMOTE_LOCAL": value & 11,
        }

        return status
