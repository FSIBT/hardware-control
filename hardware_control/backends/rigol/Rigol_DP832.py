"""DP800 Series Power Supply

.. image:: /images/RigolDP800.png
  :height: 200

See class definition for details.

"""
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

        if setting_X == "CHX_I_MAX":
            value = ensure_float(value)
            self.max_I[channel - 1] = float(value)
            return f"{setting}={value}"

        if setting_X == "CHX_V_MAX":
            value = ensure_float(value)
            self.max_V[channel - 1] = float(value)
            return f"{setting}={value}"

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            return f"{setting}={value}"

        if setting_X == "CHX_ENABLE":
            if value == "True":
                self.write(f"OUTPUT:STATE CH{channel},ON")
            else:
                self.write(f"OUTPUT:STATE CH{channel},OFF")
            return f"{setting}={value}"

        value = ensure_float(value)
        if setting_X == "CHX_I_SET":
            logger.debug(f"Iset called with value {value}")

            if self.max_I[channel - 1] is not None:
                value = min(value, self.max_I[channel - 1])

                logger.debug(f"Iset value changed to {value} because it exceeded limit")

            self.write(f"SOUR{channel}:CURR {value}")
            return f"{setting}={value}"

        if setting_X == "CHX_V_SET":
            logger.debug(f"Vset called with value {value}")

            if self.max_V[channel - 1] is not None:
                value = min(value, self.max_V[channel - 1])

                logger.debug(f"Vset value changed to {value} because it exceeded limit")

            self.write(f"SOUR{channel}:VOLT {value}")
            return f"{setting}={value}"

    def command(self, cmd: str):

        # overwrite channel number for easier comparison
        channel, command_X = get_channel_from_command(cmd)

        if command_X == "CHX_I_MAX?":
            rval = self.max_I[channel - 1]
            return f"{cmd[:-1]}={rval}"
        elif command_X == "CHX_V_MAX?":
            rval = self.max_V[channel - 1]
            return f"{cmd[:-1]}={rval}"

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            num = random.random() * 10
            if command_X == "CHX_ENABLE?":
                if num > 5:
                    return "True"
                else:
                    return "False"

            return f"{cmd.strip('?')}={num}"

        if command_X == "CHX_V_OUT?":
            rval = self.query(f"MEAS:VOLT? CH{channel}")
        elif command_X == "CHX_I_OUT?":
            rval = self.query(f"MEAS:CURR? CH{channel}")
        elif command_X == "CHX_I_SET?":
            rval = self.query(f"SOUR{channel}:CURR?")
        elif command_X == "CHX_V_SET?":
            rval = self.query(f"SOUR{channel}:VOLT?")
        elif command_X == "CHX_ENABLE?":
            rval = self.query(f"OUTP:STAT? CH{channel}")
            rval = "ON" in rval
        else:
            logger.error(f"Error: {command_X} in {self.ID} not known")
            rval = "Error"

        # remove question mark from return statement
        return f"{cmd[:-1]}={rval}"
