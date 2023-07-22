"""DP800 Series Power Supply

.. image:: /images/RigolDP800.png
  :height: 200

See class definition for details.

"""
from functools import partial
import logging

from ...base import Instrument

logger = logging.getLogger(__name__)


class Rigol_DP832(Instrument):
    def __init__(
        self,
        instrument_name: str = "RIGOL_DP832",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        # The instrument has 3 channels
        self.chan_nums = list(range(1, 4))

        self.max_V = [None] * len(self.chan_nums)
        self.max_I = [None] * len(self.chan_nums)

        for channel in self.chan_nums:
            self.add_parameter(
                f"CH{channel}_V_MAX",
                read_command=partial(self.read_V_max, channel),
                set_command=partial(self.set_V_max, channel),
                dummy_return="20.0",
            )

            self.add_parameter(
                f"CH{channel}_I_MAX",
                read_command=partial(self.read_I_max, channel),
                set_command=partial(self.set_I_max, channel),
                dummy_return="25.0",
            )

            self.add_parameter(
                f"CH{channel}_ENABLE",
                read_command=f"OUTPUT:STATE? CH{channel}",
                set_command=f"OUTPUT:STATE CH{channel},{{}}",
                dummy_return="False",
            )
            self.add_lookup(f"CH{channel}_ENABLE", {"True": "ON", "False": "OFF"})

            self.add_parameter(
                f"CH{channel}_V_SET",
                read_command=f"SOUR{channel}:VOLT?",
                set_command=f"SOUR{channel}:VOLT {{}}",
                dummy_return="10.0",
            )
            self.add_parameter(
                f"CH{channel}_V_OUT",
                read_command=f"MEAS:VOLT? CH{channel}",
                dummy_return="10.0",
            )

            self.add_parameter(
                f"CH{channel}_I_SET",
                read_command=f"SOUR{channel}:CURR?",
                set_command=f"SOUR{channel}:CURR {{}}",
                dummy_return="15.0",
            )
            self.add_parameter(
                f"CH{channel}_I_OUT",
                read_command=f"MESS:CURR? CH{channel}",
                dummy_return="15.0",
            )

    def read_V_max(self, channel):
        return self.max_V[channel - 1]

    def set_V_max(self, channel, value):
        self.max_V[channel - 1] = float(value)

    def read_I_max(self, channel):
        return self.max_I[channel - 1]

    def set_I_max(self, channel, value):
        self.max_I[channel - 1] = float(value)
