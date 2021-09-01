"""TDKL GenH AC-DC power systems.

.. image:: /images/TDKLGenH.jpg
  :height: 200

See class definition for details.

"""

import logging
from ...base import Instrument

logger = logging.getLogger(__name__)


class TDKL_GenH(Instrument):
    def __init__(self, instrument_name: str, connection_addr: str):
        super().__init__(
            instrument_name=instrument_name, connection_addr=connection_addr
        )

        self.add_parameter(
            "ENABLE",
            read_command=":OUTP:STAT?",
            set_command=":OUTP:STAT {}",
            pre_hook=[lambda value: "ON" if value == True else "OFF"],
            post_hook=[lambda value: True if value == "1\n" else False],
            dummy_return="",
        )

        self.add_parameter(
            "I_SET",
            read_command=":SOUR:CURR:LEV:IMM:AMPL?",
            set_command=f":SOUR:CURR:LEV:IMM:AMPL {{}}",
            dummy_return="",
        )

        self.add_parameter(
            "V_SET",
            read_command=":SOUR:VOLT:LEV:IMM:AMPL?",
            set_command=f":SOUR:VOLT:LEV:IMM:AMPL {{}}",
            dummy_return="",
        )

        self.add_command("READ_V_OUT", ":MEAS:VOLT?")
        self.add_command("READ_V_SET", ":SOUR:VOLT:LEV:IMM:AMPL?")
        self.add_command("READ_I_OUT", ":MEAS:CURR?")
        self.add_command("READ_I_SET", ":SOUR:CURR:LEV:IMM:AMPL?")
