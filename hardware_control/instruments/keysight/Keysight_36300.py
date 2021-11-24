"""
.. image:: /images/Keysight_E36312A.png
  :height: 200

"""

from functools import partial
import logging

from ...base import Instrument

logger = logging.getLogger(__name__)


class Keysight_36300(Instrument):
    """Keysight E36300 Series Triple Output Power Supply base instrument class.

    PARAMETERS
        * VERSION
            * Present SCPI version and version year.
        * ERRORS
            * The last 20 instrument errors.
        * CH<X>_ENABLE (*bool*)
            * Enable and disable the instrument.
        * CH<X>_V_SET (*float*)
            * Instrument voltage for channel 'X'.
        * CH<X>_I_SET (*float*)
            * Instrument current for channel 'X'.
        * CH<X>_V_OUT
            * Output voltage for channel 'X'.
        * CH<X>_I_OUT
            * Output current for channel 'X'.
        * CH<X>_V_PROT (*float*)
            * Level at which overvoltage protection trips for channel 'X'.

    COMMANDS
        * CLEAR
            * Clear the internal instrument errors.
        * ALLOW_NEG_OUTPUT
            * Allow negative outputs.

    """

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

        self.add_parameter(
            "VERSION",
            read_command="SYST:VERS?",
            dummy_return="YYYY.V",
        )

        self.add_parameter(
            "ERRORS",
            read_command="SYST:ERR?",
            dummy_return="",
        )

        for channel in self.chan_nums:
            self.add_parameter(
                f"CH{channel}_ENABLE",
                read_command=f"OUTPUT:STATE? (@{channel})",
                set_command=f"OUTP {{}}, (@{channel})",
                pre_hooks=[lambda value: "ON" if value == "True" else "OFF"],
                post_hooks=[lambda value: "True" if value == "1" else "False"],
                dummy_return="True",
            )

            self.add_parameter(
                f"CH{channel}_V_SET",
                read_command=f":SOURCE:VOLT? (@{channel})",
                set_command=f"SOURCE:VOLT {{}}, (@{channel})",
                pre_hooks=[partial(self.check_Vmax, channel)],
                dummy_return="5",
            )

            self.add_parameter(
                f"CH{channel}_I_SET",
                read_command=f":SOURCE:CURR? (@{channel})",
                set_command=f"SOURCE:CURR {{}}, (@{channel})",
                pre_hooks=[partial(self.check_Imax, channel)],
                dummy_return="6",
            )

            self.add_parameter(
                f"CH{channel}_V_OUT",
                read_command=f"MEAS:VOLT? (@{channel})",
                dummy_return="4.99",
            )

            self.add_parameter(
                f"CH{channel}_I_OUT",
                read_command=f"MEAS:CURR? (@{channel})",
                dummy_return="5.99",
            )

            self.add_parameter(
                f"CH{channel}_V_PROT",
                read_command=None,
                set_command=f"SOURCE:VOlTAGE:PROTECTION {{}} (@{channel})",
                dummy_return="6",
            )

            self.add_parameter(
                f"CH{channel}_I_PROT",
                read_command=None,
                set_command=f"SOURCE:CURRENT:PROTECTION {{}} (@{channel})",
                dummy_return="7",
            )

        self.add_command("CLEAR", "*CLS")
        self.add_command("ALLOW_NEG_OUTPUT", "SYST:PERS:MOD E3631A")

    def check_Imax(self, channel, value):
        """check if a maximum has been set and enforce it"""

        Imax = self.max_I[channel - 1]
        if Imax is not None:
            return min(value, Imax)
        return value

    def check_Vmax(self, channel, value):
        """check if a maximum has been set and enforce it"""

        Imax = self.max_V[channel - 1]
        if Imax is not None:
            return min(value, Imax)
        return value
