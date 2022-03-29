""" Siglent SDG Series.

.. image:: /images/SDG1000X.png
  :height: 200

See class definition for details.

"""

import logging

from ...base import Instrument
from ...base.hooks import splitter, substring_hook, format_float

logger = logging.getLogger(__name__)


class Siglent_SDG(Instrument):
    """Siglent SDG Series instrument class.

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

        for ch in range(1, self.number_of_channels + 1):
            self.add_parameter(
                f"CH{ch}_ENABLE",
                read_command=f"C{ch}:OUTP?",
                set_command=f"C{ch}:OUTP {{}}",
                post_hooks=[splitter([0]), splitter([-1], delimiter=" ")],
                dummy_return="True",
            )
            self.add_lookup(f"CH{ch}_ENABLE", {"True": "ON", "False": "OFF"})

            self.add_parameter(
                f"CH{ch}_WAVEFORM",
                read_command=f"C{ch}:BSWV?",
                set_command=f"C{ch}:BSWV WVTP,{{}}",
                post_hooks=[splitter([1])],
                dummy_return="SQUARE",
            )
            self.add_lookup(
                f"CH{ch}_WAVEFORM",
                {
                    "Sine": "SINE",
                    "Square": "SQUARE",
                    "Ramp": "RAMP",
                    "Pulse": "PULSE",
                    "PRBS": "PRBS",
                    "Noise": "NOISE",
                    "DC": "DC",
                    "Triangle": "RAMP",
                    "Arbitrary": "ARB",
                },
            )
            self.add_parameter(
                f"CH{ch}_FREQUENCY",
                read_command=f"C{ch}:BSWV?",
                set_command=f"C{ch}:BSWV FRQ,{{}}",
                pre_hooks=[format_float(".6E")],
                post_hooks=[splitter([3]), substring_hook(max_char=3)],
                dummy_return="100",
            )

            self.add_parameter(
                f"CH{ch}_AMPLITUDE",
                read_command=f"C{ch}:BSWV?",
                set_command=f"C{ch}:BSWV AMP,{{}}",
                pre_hooks=[format_float(".6E")],
                post_hooks=[splitter([7]), substring_hook(max_char=1)],
                dummy_return="2",
            )

            self.add_parameter(
                f"CH{ch}_OFFSET",
                read_command=f"C{ch}:BSWV?",
                set_command=f"C{ch}:BSWV OFST,{{}}",
                pre_hooks=[format_float(".6E")],
                post_hooks=[splitter([9]), substring_hook(max_char=1)],
                dummy_return="0",
            )

            self.add_parameter(
                f"CH{ch}_IMPEDANCE",
                read_command=f"C{ch}:OUTP?",
                set_command=f"C{ch}:OUTP LOAD,{{}}",
                post_hooks=[splitter([2])],
                dummy_return="HZ",
            )
            self.add_lookup(
                f"CH{ch}_IMPEDANCE",
                {
                    "50-OHM": "50",
                    "Hi-Z": "HZ",
                },
            )
