"""TDKL GenH AC-DC power systems.

.. image:: /images/TDKLGenH.jpg
  :height: 200

See class definition for details.

"""

import logging
from ...base import Instrument

logger = logging.getLogger(__name__)


class TDKL_GenH(Instrument):
    def __init__(self, instrument_name: str = "tdkl", connection_addr: str = ""):
        super().__init__(
            instrument_name=instrument_name, connection_addr=connection_addr
        )

        self.add_parameter(
            "CH1_ENABLE",
            read_command=":OUTP:STAT?",
            set_command=":OUTP:STAT {}",
            pre_hooks=[lambda value: "ON" if value == True else "OFF"],
            post_hooks=[lambda value: True if value == "1\n" else False],
            dummy_return="False",
        )

        self.add_parameter(
            "CH1_V_SET",
            read_command=":SOUR:VOLT:LEV:IMM:AMPL?",
            set_command=":SOUR:VOLT:LEV:IMM:AMPL {}",
            dummy_return="10.0",
        )
        self.add_parameter(
            "CH1_I_SET",
            read_command=":SOUR:CURR:LEV:IMM:AMPL?",
            set_command=":SOUR:CURR:LEV:IMM:AMPL {}",
            dummy_return="15.0",
        )
        self.add_parameter(
            "CH1_V_OUT",
            read_command=":MEAS:VOLT?",
            dummy_return="10.0",
        )
        self.add_parameter(
            "CH1_I_OUT",
            read_command=":MEAS:CURR?",
            dummy_return="15.0",
        )
