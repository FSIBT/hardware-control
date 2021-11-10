"""
.. image:: /images/TDKLGenH.jpg
  :height: 200

"""

import logging
from ...base import Instrument

logger = logging.getLogger(__name__)


class TDKL_GenH(Instrument):
    """
    TDKL GenH AC-DC power systems instrument class.

    PARAMETERS
        * CH1_ENABLE (*bool*)
            * On/off status.
        * CH1_V_OUT (*float*)
            * Current voltage.
        * CH1_I_OUT (*float*)
            * Current current.
        * CH1_V_SET (*float*)
            * Output voltage limit.
        * CH1_I_SET (*float*)
            * Output current limit.

    """

    def __init__(
        self,
        instrument_name: str = "TDKL_GENH",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        # Instrument only returns first letter of the words ON and OFF
        # But to set the instrument, one must use full words
        self.add_parameter(
            "CH1_ENABLE",
            read_command=":OUTP:STAT?",
            set_command=":OUTP:STAT {}",
            pre_hooks=[lambda x: "ON" if x == "True" else "OFF"],
            post_hooks=[lambda x: "True" if x == "O" else "False"],
            dummy_return="False",
        )

        # Voltage on instrument front panel when "prev" is pressed
        self.add_parameter(
            "CH1_V_SET",
            read_command=":SOUR:VOLT:LEV:IMM:AMPL?",
            set_command=":SOUR:VOLT:LEV:IMM:AMPL {}",
            dummy_return="10.0",
        )
        # Current on instrument front panel when "prev" is pressed
        self.add_parameter(
            "CH1_I_SET",
            read_command=":SOUR:CURR:LEV:IMM:AMPL?",
            set_command=":SOUR:CURR:LEV:IMM:AMPL {}",
            dummy_return="15.0",
        )
        # Voltage on instrument front panel
        self.add_parameter(
            "CH1_V_OUT",
            read_command=":MEAS:VOLT?",
            dummy_return="10.0",
        )
        # Current on instrument front panel
        self.add_parameter(
            "CH1_I_OUT",
            read_command=":MEAS:CURR?",
            dummy_return="15.0",
        )
