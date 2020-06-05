import random

from hardware_control.HC_Backend import HC_Backend, ensure_online
from hardware_control.utility import ensure_float


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

    @ensure_online
    def update_setting(self, setting: str, value):

        if self.dummy:
            return value

        if len(setting) >= 3:
            channel = int(setting[2])

        # overwrite channel number for easier comparison
        setting_X = setting[:2] + "X" + setting[3:]

        if setting_X == "CHX_enable":
            if value == "True":
                self.write(f"OUTPUT ON (@{channel})")
            else:
                self.write(f"OUTPUT OFF (@{channel})")
            out = self.query("OUTPUT:STATE?")
            return str(out == "1")

        value = ensure_float(value)

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

        if setting == "CHX_V_max":
            self.max_V[channel - 1] = value
            return value

        if setting == "CHX_I_max":
            self.max_I[channel - 1] = value
            return value

    @ensure_online
    def command(self, cmd: str):

        if self.dummy:
            num = random.random() * 10
            return f"{cmd.strip('?')}={num}"

        channel = int(cmd[2])
        cmd = cmd[:-1]

        # overwrite channel number for easier comparison
        cmd_X = cmd[:2] + "X" + cmd[3:]

        if cmd_X == "CHX_V_out?":
            rval = self.query("MEAS:VOLT? (@{channel})")
        elif cmd_X == "CHX_I_out?":
            rval = self.query("MEAS:CURR? (@{channel})")
        elif cmd_X == "CHX_I_set?":
            rval = self.query(f":SOURCE:CURR? (@{channel})")
        elif cmd_X == "CHX_V_set?":
            rval = self.query(f":SOURCE:VOLT? (@{channel})")
        elif cmd_X == "CHX_I_max?":
            rval = self.max_I[channel - 1]
        elif cmd_X == "CHX_V_max?":
            rval = self.max_V[channel - 1]

        return f"{cmd}={rval}"
