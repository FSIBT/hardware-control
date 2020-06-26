import logging
import random

from hardware_control.HC_Backend import (
    HC_Backend,
    ensure_online,
    get_channel_from_command,
)
from hardware_control.utility import ensure_float

logger = logging.getLogger(__name__)


class Key36300Ctrl(HC_Backend):
    """Class to control the KeysightE36300 Series Triple Output Power Supply

    """

    def __init__(self, connection_addr: str):

        super().__init__()

        self.ID = "Key36300"
        self.connection_addr = connection_addr
        self.parse_connection_addr()

        # This specifies the max number of channels the user can request
        self.num_channels = 3

        self.max_V = [None] * self.num_channels
        self.max_I = [None] * self.num_channels

    # @ensure_online
    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)

        value_orig = value
        value = ensure_float(value)

        if setting_X == "CHX_V_max":
            self.max_V[channel - 1] = value
            return str(value)

        if setting_X == "CHX_I_max":
            self.max_I[channel - 1] = value
            return str(value)

        if not self.online:
            return "Offline"

        if self.dummy:
            return str(value)

        if setting_X == "CHX_enable":
            if value_orig == "True":
                # self.write(f"OUTPUT ON (@{channel})")
                self.write(f"OUTPUT ON")
            else:
                # self.write(f"OUTPUT OFF (@{channel})")
                self.write(f"OUTPUT OFF")
            out = self.query("OUTPUT:STATE?")
            return str(out == "1")

        if setting_X == "CHX_I_set":
            if self.max_I[channel - 1] is not None:
                value = min(value, self.max_I[channel - 1])

            self.write(f"SOURCE:CURR {value}, (@{channel})")
            return self.query(f":SOURCE:CURR? (@{channel})")

        if setting_X == "CHX_V_set":
            if self.max_V[channel - 1] is not None:
                value = min(value, self.max_V[channel - 1])

            self.write(f"SOURCE:VOLT {value}, (@{channel})")
            return self.query(f":SOURCE:VOLT? (@{channel})")

    # @ensure_online
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
            return "Offline"

        if self.dummy:

            num = random.random() * 10

            if command_X == "CHX_enable?":
                if num > 5:
                    return "True"
                else:
                    return "False"

            return f"{cmd.strip('?')}={num}"

        if command_X == "CHX_V_out?":
            rval = self.query(f"MEAS:VOLT? (@{channel})")
        elif command_X == "CHX_I_out?":
            rval = self.query(f"MEAS:CURR? (@{channel})")
        elif command_X == "CHX_I_set?":
            rval = self.query(f":SOURCE:CURR? (@{channel})")
        elif command_X == "CHX_V_set?":
            rval = self.query(f":SOURCE:VOLT? (@{channel})")
        elif command_X == "CHX_enable?":
            rval = self.query(f":OUTPUT:STATE? (@{channel})")
            rval = rval == "1"
        else:
            logger.error(f"Error: {command_X} in {self.ID} not known")
            rval = "Error"

        # remove question mark from return statement
        return f"{cmd[:-1]}={rval}"
