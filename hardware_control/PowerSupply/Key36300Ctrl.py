import random

from hardware_control.HC_Backend import HC_Backend, VISA
from hardware_control.utility import regex_compare, str_to_bool


class Key36300Ctrl(HC_Backend):
    def __init__(
        self,
        connection_addr,
        connection_type: str = VISA,
        ip_addr: str = "",
        port_no=5025,
    ):

        super().__init__()

        self.ID = "Key36300"

        self.online = False
        self.dummy = False

        self.connection_addr = connection_addr
        self.parse_connection_addr()

        self.num_channels = 1
        # This specifies the max number of channels the user can request

    def update_setting(self, setting: str, value):

        if not self.online:
            return f"{self.ID}-Offline"

        try:
            if self.dummy:
                return value
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of PSU
                if regex_compare("CH._enable", setting):
                    c = setting[2]
                    if str_to_bool(value):
                        self.write(f"OUTPUT ON (@{c})")
                    else:
                        self.write(f"OUTPUT OFF (@{c})")
                    out = self.query("output:state?")
                    return str(rval == "1")
                elif regex_compare("CH._I_set", setting):
                    c = setting[2]
                    self.write(f"SOURCE:CURR {value}, (@{c})")
                    rval = self.query(f":SOURCE:CURR? (@{c})")
                    return rval
                elif regex_compare("CH._V_set", setting):
                    c = setting[2]
                    self.write(f"SOURCE:VOLT {value}, (@{c})")
                    rval = self.query(f":SOURCE:VOLT? (@{c})")
                    return rval
        except Exception as e:
            logger.error(
                f"An error occured in {self.ID} when sending SCPI commands to the instrument.",
                exc_info=True,
            )

    def command(self, cmd: str):

        if not self.online:
            return f"{self.ID}-Offline"

        try:
            if self.dummy:
                num = random.random() * 10
                return f"{cmd.strip('?')}={num}"
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of PSU
                if regex_compare("CH._V_out?", cmd):
                    c = setting[2]
                    rval = self.query("MEAS:VOLT? (@{c})")
                    return f"{cmd}={rval}"
                elif regex_compare("CH._I_out?", cmd):
                    c = setting[2]
                    rval = self.query("MEAS:CURR? (@{c})")
                    return f"{cmd}={rval}"
                elif regex_compare("CH._I_set?", cmd):
                    c = setting[2]
                    rval = self.query(f":SOURCE:CURR? (@{c})")
                    return f"{cmd}={rval}"
                elif regex_compare("CH._V_set?", cmd):
                    c = setting[2]
                    rval = self.query(f":SOURCE:VOLT? (@{c})")
                    return f"{cmd}={rval}"
        except Exception as e:
            logger.error(
                "An error occured in Key36300.py when sending SCPI commands to the instrument.",
                exc_info=True,
            )
