"""TDKL GenH AC-DC power systems.

.. image:: /images/TDKLGenH.jpg
  :height: 200

See class definition for details.

"""

import logging
import random

from ..base import Backend, ensure_online
from ..utility import get_channel_from_command


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

        channel, setting_X = get_channel_from_command(setting)

        # Note: We ignore channel number because there is only
        # one channel on this model of PSU
        if setting_X == "CHX_enable":
            if value == "True":
                self.write(":OUTP:STAT ON")
            else:
                self.write(":OUTP:STAT OFF")
            rval = self.query(":OUTP:STAT?")
            rval = rval == "1\n"
            return f"{setting}=={rval}"
        if setting_X == "CHX_I_set":
            self.write(f":SOUR:CURR:LEV:IMM:AMPL {value}")
            rval = self.query(":SOUR:CURR:LEV:IMM:AMPL?")
            return f"{setting}={rval}"
        if setting_X == "CHX_V_set":
            self.write(f":SOUR:VOLT:LEV:IMM:AMPL {value}")
            rval = self.query(":SOUR:VOLT:LEV:IMM:AMPL?")
            return f"{setting}={rval}"

    @ensure_online
    def command(self, cmd: str):

        if self.dummy:
            num = random.random() * 10
            return f"{cmd.strip('?')}={num}"

        # Note: We ignore channel number because there is only
        # one channel on this model of PSU
        channel, cmd_X = get_channel_from_command(cmd)

        command_map = {
            "CHX_V_out?": ":MEAS:VOLT?",
            "CHX_I_out?": ":MEAS:CURR?",
            "CHX_I_set?": ":SOUR:CURR:LEV:IMM:AMPL?",
            "CHX_V_set?": ":SOUR:VOLT:LEV:IMM:AMPL?",
        }

        command = command_map.get(cmd_X, None)
        if command is not None:
            rval = self.query(command)
            return f"{cmd}={rval}"

        logger.errro(f"Unknown command: {cmd}")
        return f"Unknown command"
