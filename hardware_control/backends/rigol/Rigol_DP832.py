import logging
import random

import pyvisa

from ..base import Backend
from ..utility import (
    ensure_float,
    get_channel_from_command,
)

logger = logging.getLogger(__name__)


class Rigol_DP832(Backend):
    def __init__(self, connection_addr):
        super().__init__(instrument_name="RigolDP832", connection_addr=connection_addr)

        # This specifies the max number of channels the user can request
        self.num_channels = 3

        self.max_V = [None] * self.num_channels
        self.max_I = [None] * self.num_channels

    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)

        if setting_X == "CHX_I_max":
            value = ensure_float(value)
            self.max_I[channel - 1] = float(value)
            return str(value)
        elif setting_X == "CHX_V_max":
            value = ensure_float(value)
            self.max_V[channel - 1] = float(value)
            return str(value)

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            return str(value)

        if setting_X == "CHX_enable":
            if value == "True":
                self.write(f"OUTPUT:STATE CH{channel},ON")
            else:
                self.write(f"OUTPUT:STATE CH{channel},OFF")

            return str(value)

        value = ensure_float(value)
        if setting_X == "CHX_I_set":
            logger.debug(f"Iset called with value {value}")

            if self.max_I[channel - 1] is not None:
                value = min(value, self.max_I[channel - 1])

                logger.debug(f"Iset value changed to {value} because it exceeded limit")

            self.write(f"SOUR{channel}:CURR {value}")

            return str(value)

        if setting_X == "CHX_V_set":
            logger.debug(f"Vset called with value {value}")

            if self.max_V[channel - 1] is not None:
                value = min(value, self.max_V[channel - 1])

                logger.debug(f"Vset value changed to {value} because it exceeded limit")

            self.write(f"SOUR{channel}:VOLT {value}")

            return str(value)

    def command(self, cmd: str):

        # overwrite channel number for easier comparison
        channel, command_X = get_channel_from_command(cmd)

        if command_X == "CHX_I_max?":
            rval = self.max_I[channel - 1]
            return f"{cmd[:-1]}={rval}"
        elif command_X == "CHX_V_max?":
            rval = self.max_V[channel - 1]
            return f"{cmd[:-1]}={rval}"

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            num = random.random() * 10
            if command_X == "CHX_enable?":
                if num > 5:
                    return "True"
                else:
                    return "False"

            return f"{cmd.strip('?')}={num}"

        if command_X == "CHX_V_out?":
            rval = self.query(f"MEAS:VOLT? CH{channel}")
        elif command_X == "CHX_I_out?":
            rval = self.query(f"MEAS:CURR? CH{channel}")
        elif command_X == "CHX_I_set?":
            rval = self.query(f"SOUR{channel}:CURR?")
        elif command_X == "CHX_V_set?":
            rval = self.query(f"SOUR{channel}:VOLT?")
        elif command_X == "CHX_enable?":
            rval = self.query(f"OUTP:STAT? CH{channel}")
            rval = "ON" in rval
        else:
            logger.error(f"Error: {command_X} in {self.ID} not known")
            rval = "Error"

        # remove question mark from return statement
        return f"{cmd[:-1]}={rval}"

    def read_status(self, channel):
        """See table on page 24 of manual"""
        if self.dummy:
            outputs = [1 + 128 + 1024, 128, 1, 1024]
            value = random.choice(outputs)
        else:
            result = self.query(f"$BD:00,CMD:MON,CH:{channel},PAR:STAT")
            if result is None:
                return None
            result = result.strip(r"\r")
            value = int(result[-5:])

        status = {
            "on_off": value & 1,
            "ramping_up": value & 2,
            "ramping_down": value & 4,
            "over_current": value & 8,
            "over_voltage": value & 16,
            "under_voltage": value & 32,
            "max_voltage": value & 64,
            "tripped": value & 128,
            "over_power": value & 256,
            "over_temperature": value & 512,
            "disabled": value & 1024,
            "kill": value & 2048,
            "interlocked": value & 4096,
            "calibration_error": value & 8192,
        }
        return status
