"""KeysightE36300 Series Triple Output Power Supply

.. image:: /images/Keysight_E36312A.png
  :height: 200

See class definition for deails.

"""

import logging
import random

from ...base import Instrument

logger = logging.getLogger(__name__)


class Keysight_36300(Instrument):
    """Keysight E36300 Series Triple Output Power Supply base instrument class."""

    def __init__(
        self,
        instrument_name: str = "Keysight_36300",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        # The instrument has channels 1, 2, and 3
        self.chan_nums = list(range(1, 4))
        self.max_V = [None] * len(self.chan_nums)
        self.max_I = [None] * len(self.chan_nums)

        for channel in self.chan_nums:

            self.add_parameter(
                f"CH{channel}_V_MAX",
                read_command=None,
                set_command=[lambda x: set_V_max(channel, x)],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_I_MAX",
                read_command=None,
                set_command=[lambda x: set_I_max(channel, x)],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_ENABLE",
                read_command="OUTPUT:STATE?",
                set_command="OUTPUT {}",
                pre_hooks=[lambda x: "ON" if value == True else "OFF"],
                post_hooks=[lambda x: True if value == "1" else False],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_I_SET",
                read_command=f":SOURCE:CURR? (@{channel})",
                set_command=f"SOURCE:CURR {{}}, (@{channel})",
                pre_hooks=[
                    lambda x: min(value, self.max_I[channel - 1])
                    if self.max_I[channel - 1] is not None
                    else None
                ],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_V_SET",
                read_command=f":SOURCE:VOLT? (@{channel})",
                set_command=f"SOURCE:VOLT {{}}, (@{channel})",
                pre_hooks=[
                    lambda x: min(value, self.max_V[channel - 1])
                    if self.max_V[channel - 1] is not None
                    else None
                ],
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_V_OUT",
                read_command=f"MEAS:VOLT? (@{channel})",
                dummy_return="",
            )

            self.add_parameter(
                "CH{channel}_I_OUT",
                read_command=f"MEAS:CURR? (@{channel})",
                dummy_return="",
            )

    def set_V_max(self, channel, value):
        self.max_V[channel - 1] = float(value)

    def set_I_max(self, channel, value):
        self.max_I[channel - 1] = float(value)
