""" Siglent SDG Series.

.. image:: /images/SDG1000X.png
  :height: 200

See class definition for details.

"""

import logging

from ...base import Instrument
from ...base.hooks import format_float

logger = logging.getLogger(__name__)


class Siglent_SDG(Instrument):
    """Siglent SDG Serie instrument class.

    Instrument home page: https://www.siglent.eu/waveform-generators

    """

    def __init__(
        self,
        instrument_name: str = "SIGLENT-SDG",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        self.number_of_channels = 2

        for ch in range(self.number_of_channels):

            # might need a readback hook to parse to True/False
            self.add_parameter(
                f"CH{ch}_ENABLED",
                read_command=f"C{ch}:OUTP?",
                set_command=f"C{ch}:OUTP {{}}",
            )
            self.add_lookup(f"CH{ch}_ENABLED", {"True": "ON", "False": "OFF"})

            self.add_parameter(
                f"CH{ch}_WAVEFORM",
                read_command=f"C{ch}:BSWV?",
                set_command=f"C{ch}:BSWV WVTP,{{}}",
            )
            self.add_lookup(
                f"CH{ch}_WAVEFORM",
                {
                    "SINE": "SINE",
                    "SQUARE": "SQUARE",
                    "RAMP": "RAMP",
                    "PULSE": "PULSE",
                    "PRBS": "PRBS",
                    "NOISE": "NOISE",
                    "DC": "DC",
                    "TRIANGLE": "RAMP",
                    "ARBITRARY": "ARB",
                },
            )
            self.add_parameter(
                f"CH{ch}_FREQUENCY",
                read_command=f"C{ch}:BSWV?",
                set_command=f"C{ch}:BSWV FRQ,{{}}",
                pre_hooks=[format_float(".6E")],
            )

            self.add_parameter(
                f"CH{ch}_AMPLITUDE",
                read_command=f"C{ch}:BSWV?",
                set_command=f"C{ch}:BSWV AMP,{{}}",
                pre_hooks=[format_float(".6E")],
            )

            self.add_parameter(
                f"CH{ch}_OFFSET",
                read_command=f"C{ch}:BSWV?",
                set_command=f"C{ch}:BSWV OFST,{{}}",
                pre_hooks=[format_float(".6E")],
            )

            self.add_parameter(
                f"CH{ch}_IMPEDANCE",
                read_command=f"C{ch}:OUTP?",
                set_command=f"C{ch}:OUTP LOAD,{{}}",
            )
            self.add_lookup(
                f"CH{ch}_IMPEDANCE",
                {
                    "50": "50",
                    "HiZ": "HZ",
                },
            )
