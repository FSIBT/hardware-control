import random

from hardware_control.HC_Backend import HC_Backend, VISA
from hardware_control.utility import regex_compare, str_to_bool


class TDKLGenHCtrl(HC_Backend):
    def __init__(
        self, connection_addr: str,
    ):

        super().__init__()

        self.ID = "TDKL-GenH"

        self.connection_addr = connection_addr
        self.online = False
        self.dummy = False

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
                    if str_to_bool(value):
                        self.write(":OUTP:STAT ON")
                    else:
                        self.write(":OUTP:STAT OFF")
                    rval = self.query(":OUTP:STAT?")
                    return str(rval == "1\n")
                elif regex_compare("CH._I_set", setting):
                    self.write(f":SOUR:CURR:LEV:IMM:AMPL {value}")
                    rval = self.query(":SOUR:CURR:LEV:IMM:AMPL?")
                    return rval
                elif regex_compare("CH._V_set", setting):
                    self.write(f":SOUR:VOLT:LEV:IMM:AMPL {value}")
                    rval = self.query(":SOUR:VOLT:LEV:IMM:AMPL?")
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
                    rval = self.query(":MEAS:VOLT?")
                    chstr = cmd[0:3]
                    return f"{cmd}={rval}"
                elif regex_compare("CH._I_out?", cmd):
                    rval = self.query(":MEAS:CURR?")
                    chstr = cmd[0:3]
                    return f"{cmd}={rval}"
                elif regex_compare("CH._I_set?", cmd):
                    chstr = cmd[0:3]
                    rval = self.query(":SOUR:CURR:LEV:IMM:AMPL?")
                    return f"{cmd}={rval}"
                elif regex_compare("CH._V_set?", cmd):
                    chstr = cmd[0:3]
                    rval = self.query(":SOUR:VOLT:LEV:IMM:AMPL?")
                    return f"{cmd}={rval}"
        except Exception as e:
            logger.error(
                "An error occured in CAEN14xxETCtrl.py when sending SCPI commands to the instrument.",
                exc_info=True,
            )
