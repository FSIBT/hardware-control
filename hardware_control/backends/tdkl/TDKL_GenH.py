"""TDKL GenH AC-DC power systems.

.. image:: /images/TDKLGenH.jpg
  :height: 200

See class definition for details.

"""

import logging
import random

from ..base import Backend, ensure_online
from ..utility import regex_compare


logger = logging.getLogger(__name__)


class TDKL_GenH(Backend):
    def __init__(self, connection_addr: str):
        super().__init__(instrument_name="TDKL-GenH", connection_addr=connection_addr)

        # This specifies the max number of channels the user can request
        self.num_channels = 1

    @ensure_online
    def update_setting(self, setting: str, value):

        if self.dummy:
            return value

        # Note: We ignore channel number because there is only
        # one channel on this model of PSU
        if regex_compare("CH._enable", setting):
            if value == "True":
                self.write(":OUTP:STAT ON")
            else:
                self.write(":OUTP:STAT OFF")
            rval = self.query(":OUTP:STAT?")
            return str(rval == "1\n")
        if regex_compare("CH._I_set", setting):
            self.write(f":SOUR:CURR:LEV:IMM:AMPL {value}")
            rval = self.query(":SOUR:CURR:LEV:IMM:AMPL?")
            return rval
        if regex_compare("CH._V_set", setting):
            self.write(f":SOUR:VOLT:LEV:IMM:AMPL {value}")
            rval = self.query(":SOUR:VOLT:LEV:IMM:AMPL?")
            return rval

    @ensure_online
    def command(self, cmd: str):

        if self.dummy:
            num = random.random() * 10
            return f"{cmd.strip('?')}={num}"

        # Note: We ignore channel number because there is only
        # one channel on this model of PSU
        if regex_compare("CH._V_out?", cmd):
            rval = self.query(":MEAS:VOLT?")
            chstr = cmd[0:3]
            return f"{cmd}={rval}"
        if regex_compare("CH._I_out?", cmd):
            rval = self.query(":MEAS:CURR?")
            chstr = cmd[0:3]
            return f"{cmd}={rval}"
        if regex_compare("CH._I_set?", cmd):
            chstr = cmd[0:3]
            rval = self.query(":SOUR:CURR:LEV:IMM:AMPL?")
            return f"{cmd}={rval}"
        if regex_compare("CH._V_set?", cmd):
            chstr = cmd[0:3]
            rval = self.query(":SOUR:VOLT:LEV:IMM:AMPL?")
            return f"{cmd}={rval}"
