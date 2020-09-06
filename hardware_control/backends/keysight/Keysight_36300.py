"""KeysightE36300 Series Triple Output Power Supply

.. image:: /images/Keysight_E36312A.png
  :height: 200

See class definition for deails.

"""

import logging
import random

from ..base import Backend
from ..utility import ensure_float, get_channel_from_command


logger = logging.getLogger(__name__)


class Keysight_36300(Backend):
    """Control the KeysightE36300 Series Triple Output Power Supply.

    """

    def __init__(self, connection_addr: str):
        super().__init__(instrument_name="Key36300", connection_addr=connection_addr)

        # This specifies the max number of channels the user can request
        self.num_channels = 3

        self.max_V = [None] * self.num_channels
        self.max_I = [None] * self.num_channels

    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)

        value_orig = value
        value = ensure_float(value)

        if setting_X == "CHX_V_MAX":
            self.max_V[channel - 1] = value
            return str(value)

        if setting_X == "CHX_I_MAX":
            self.max_I[channel - 1] = value
            return str(value)

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            return str(value)

        if setting_X == "CHX_ENABLE":
            if value_orig == "True":
                # self.write(f"OUTPUT ON (@{channel})")
                self.write("OUTPUT ON")
            else:
                # self.write(f"OUTPUT OFF (@{channel})")
                self.write("OUTPUT OFF")
            out = self.query("OUTPUT:STATE?")
            out = out == "1"
            return f"{setting}={out}"

        if setting_X == "CHX_I_SET":
            if self.max_I[channel - 1] is not None:
                value = min(value, self.max_I[channel - 1])

            self.write(f"SOURCE:CURR {value}, (@{channel})")
            rval = self.query(f":SOURCE:CURR? (@{channel})")
            return f"{setting}={rval}"

        if setting_X == "CHX_V_SET":
            if self.max_V[channel - 1] is not None:
                value = min(value, self.max_V[channel - 1])

            self.write(f"SOURCE:VOLT {value}, (@{channel})")
            rval = self.query(f":SOURCE:VOLT? (@{channel})")
            return f"{setting}={rval}"

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
            rval = self.query(f"MEAS:VOLT? (@{channel})")
        elif command_X == "CHX_I_OUT?":
            rval = self.query(f"MEAS:CURR? (@{channel})")
        elif command_X == "CHX_I_SET?":
            rval = self.query(f":SOURCE:CURR? (@{channel})")
        elif command_X == "CHX_V_SET?":
            rval = self.query(f":SOURCE:VOLT? (@{channel})")
        elif command_X == "CHX_ENABLE?":
            rval = self.query(f":OUTPUT:STATE? (@{channel})")
            rval = rval == "1"
        else:
            logger.error(f"Error: {command_X} in {self.ID} not known")
            rval = "Error"

        # remove question mark from return statement
        return f"{cmd[:-1]}={rval}"
