"""Keysight 33500 waveform and function generator.

.. image:: /images/Keysight33500B.png
  :height: 200

See class definition for deails.

"""

import logging

from ...base import Instrument
from ...base.hooks import (
    format_float,
    min_len_converter,
    expected_input_validator,
    scaling_converter,
    parse_converter,
    uppercase,
)

logger = logging.getLogger(__name__)


class Keysight_33500B(Instrument):
    """Keysight 33500B Series Waveform Generator base instrument class.

    Instrument home page: https://www.keysight.com/us/en/products/waveform-and-function-generators/trueform-series-waveform-and-function-generators.html

    Parameters
    ----------
    connection_addr : str
    Address of instrument. Can use Visa address or socket and port.

    """

    def __init__(
        self,
        instrument_name: str = "KEYSIGHT-33500B",
        connection_addr: str = "",
        number_of_channels=1,
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=5025,
        )

        self.num_vert_divisions = 8
        self.check_connection_commands = "*IDN?"

        for ch in range(1, number_of_channels + 1):
            self.add_parameter(
                f"CH{ch}_VOLTS_DIV",
                read_command="f:CHAN{ch}:SCAL?",
                set_command=f":CHAN{ch}:SCAL {{}}",
                pre_hooks=[format_float(".6E")],
                dummy_return="1",
            )
            self.add_lookup(f"CH{ch}_VOLTS_DIV", {"POSITIVE": "1", "NEGATIVE": "0"})
            self.add_parameter(
                f"CH{ch}_LABEL",
                read_command=f"CHAN{ch}:LAB?",
                set_command=f"CHAN{ch}:LAB {{}}",
                pre_hooks=[min_len_converter(32)],
                dummy_return="NA",
            )
            self.add_parameter(
                f"CH{ch}_INVERT",
                read_command=f"CHAN{ch}:INV?",
                set_command=f"CHAN{ch}:INV {{}}",
                dummy_return="False",
            )
            self.add_lookup(f"CH{ch}_INVERT", {"True": "1", "False": "0"})

            self.add_parameter(
                f"CH{ch}_PROBE_ATTEN",
                read_command=f"CHAN{ch}:PROB?",
                set_command=f"CHAN{ch}:PROB {{}}",
                pre_hooks=[format_float(".6E")],
                dummy_return="1",
            )

            self.add_parameter(
                f"CH{ch}_COUPLING",
                read_command=f"CHAN{ch}:COUP?",
                set_command=f"CHAN{ch}:COUP {{}}",
                pre_hooks=[expected_input_validator(["AC", "DC"], "DC")],
                dummy_return="DC",
            )

            """    Burst Subsystem    """
            self.add_parameter(
                f"CH{ch}_BURS_MODE",
                read_command=f"SOUR{ch}:BURS:MODE?",
                set_command=f"SOUR{ch}:BURS:MODE {{}}",
                dummy_return="False",
            )
            self.add_lookup(f"CH{ch}_BURS_MODE", {"True": "1", "False": "0"})

            self.add_parameter(
                f"CH{ch}_BURS_STAT",
                read_command=f"SOUR{ch}:BURS:STAT?",
                set_command=f"SOUR{ch}:BURS:STAT {{}}",
                dummy_return="1",
            )

            self.add_parameter(
                f"CH{ch}_BURS_NCYC",
                read_command=f"SOUR{ch}:BURS:NCYC?",
                set_command=f"SOUR{ch}:BURS:NCYC {{}}",
                dummy_return="1",
            )

            self.add_parameter(
                f"CH{ch}_BURS_PER",
                read_command=f"SOUR{ch}:BURS:INT:PER?",
                set_command=f"SOUR{ch}:BURS:INT:PER {{}}",
                dummy_return="10",
            )

            """    Display Subsystem    """
            self.add_parameter(
                f"CH{ch}_ACTIVE",
                read_command=f"CHAN{ch}:DISP?",
                set_command=f"CHAN{ch}:DISP {{}}",
                dummy_return="True",
            )
            self.add_lookup(f"CH{ch}_ACTIVE", {"True": "1", "False": "0"})

            """    Frequency Subsystem    """
            self.add_parameter(
                f"CH{ch}_FREQUENCY",
                read_command=f"SOUR{ch}:FREQ?",
                set_command=f"SOUR{ch}:FREQ {{}}",
                pre_hooks=[scaling_converter(1e6), format_float(".6E")],
                post_hooks=[
                    parse_converter(0, -1),
                ],
                dummy_return="20",
            )

            """    Function Subsystem    """
            # FUNCtion:NOISe:BANDwidth - bandwidth for NOISe waveform
            self.add_parameter(
                f"CH{ch}_BW_LIM",
                read_command=f"CHAN{ch}:BWL?",
                set_command=f"CHAN{ch}:BWL {{}}",
                dummy_return="False",
            )
            self.add_lookup(f"CH{ch}_BW_LIM", {"True": "1", "False": "0"})

            self.add_parameter(
                f"CH{ch}_WAVEFORM",
                read_command=f":SOUR{ch}:FUNC?",
                set_command=f":SOUR{ch}:FUNC {{}}",
                pre_hooks=[uppercase()],
                dummy_return="DC",
            )
            self.add_lookup(
                f"CH{ch}_WAVEFORM",
                {
                    "SINE": "SIN",
                    "SQUARE": "SQU",
                    "TRIANGLE": "TRI",
                    "RAMP": "RAMP",
                    "PULSE": "PULS",
                    "PRBS": "PRBS",
                    "NOISE": "NOIS",
                    "ARBITRARY": "ARB",
                    "DC": "DC",
                },
            )

            """    OUTPut Subsystem    """
            self.add_parameter(
                f"CH{ch}_IMPEDANCE",
                read_command=f"OUTP{ch}:LOAD?",
                set_command=f"OUTP{ch}:LOAD {{}}",
                pre_hooks=[lambda value: "50" if value == "50-OHM" else "INF"],
                dummy_return="50-OHM",
            )

            self.add_parameter(
                f"CH{ch}_ENABLE",
                read_command=f":OUTP{ch}?",
                set_command=f":OUTP{ch} {{}}",
                pre_hooks=[lambda value: "ON" if value == True else "OFF"],
                post_hooks=[lambda value: True if value == "1\n" else False],
                dummy_return="False",
            )

            self.add_parameter(
                f"CH{ch}_POLARITY",
                read_command=f"OUTP{ch}:POL?",
                set_command=f":OUTP{ch}:POL {{}}",
                dummy_return="1",
            )
            self.add_parameter(
                f"CH{ch}_TRIGGER_CHANNEL",
                read_command=f"TRIG{ch}:SOUR?",
                set_command=f"TRIG{ch}:SOUR {{}}",
                dummy_return="1",
            )

            self.add_parameter(
                f"CH{ch}_TRIGGER_DELAY",
                read_command="TRIG1:DEL?",
                set_command="TRIG1:DEL {}",
                pre_hooks=[format_float(".6E")],
                dummy_return="0",
            )

            """    VOLT Subsystem    """
            self.add_parameter(
                f"CH{ch}_AMPLITUDE",
                read_command=f"SOUR{ch}:VOLT?",
                set_command=f"SOUR{ch}:VOLT {{}}",
                pre_hooks=[format_float(".6E")],
                dummy_return="10",
            )

            self.add_parameter(
                f"CH{ch}_OFFSET",
                read_command=f"SOUR{ch}:VOLT?",
                set_command=f"SOUR{ch}:VOLT:OFFS {{}}",
                pre_hooks=[format_float(".6E")],
                dummy_return="0",
            )

            self.add_parameter(
                f"CH{ch}_TRACK",
                read_command="TRAC?",
                set_command="SOUR1:TRAC {}",
                dummy_return="1",
            )

        self.add_parameter(
            "TIMEBASE",
            read_command=":TIM:SCAL?",
            set_command=":TIM:SCAL {}",
            pre_hooks=[format_float(".6E")],
            dummy_return="1",
        )

        self.add_parameter(
            "TIME_OFFSET",
            read_command=":TIM:POS?",
            set_command=":TIM:POS {}",
            pre_hooks=[format_float(".6E")],
            dummy_return="0",
        )

        self.add_parameter(
            "LABELS_ENABLED",
            read_command="DISP:LAB?",
            set_command="DISP:LAB {}",
            dummy_return="True",
        )
        self.add_lookup("LABELS_ENABLED", {"True": "1", "False": "0"})

        """    Trigger Subsystem    """
        self.add_parameter(
            "TRIGGER_LEVEL",
            read_command="TRIG:EDGE:LEV?",
            set_command="TRIG:EDGE:LEV {}",
            pre_hooks=[format_float(".6E")],
            dummy_return="10",
        )

        self.add_parameter(
            "TRIGGER_COUPLING",
            read_command="TRIG:COUP?",
            set_command="TRIG:COUP {}",
            pre_hooks=[expected_input_validator(["AC", "DC", "LFReject"], "DC")],
            dummy_return="DC",
        )

        self.add_parameter(
            "TRIGGER_EDGE",
            read_command="TRIG:EDGE:SLOP?",
            set_command="TRIG:EDGE:SLOP {}",
            pre_hooks=[expected_input_validator(["BOTH", "NEG", "POS", "ALT"], "POS")],
            dummy_return="POS",
        )
