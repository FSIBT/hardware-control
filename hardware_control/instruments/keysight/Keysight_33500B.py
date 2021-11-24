"""
.. image:: /images/Keysight33500B.png
  :height: 200

"""

import logging

from ...base import Instrument
from ...base.hooks import (
    format_float,
    max_len_converter,
    expected_input_validator,
    scaling_converter,
    substring_hook,
    uppercase,
)

logger = logging.getLogger(__name__)


class Keysight_33500B(Instrument):
    """Keysight 33500B Series Waveform Generator base instrument class.

    PARAMETERS
        * DISPLAY (*bool*)
            * Enables and disables the instrument display.
        * TIMEBASE (*float*)
            * Horizontal resolution in time per division.
        * TIME_OFFSET (*float*)
            * Time offset from trigger.
        * NUM_POINTS (*int*)
            * Number of points on the time axis.
        * LABELS_ENABLED (*bool*)
            * Enables or disables channel labels on the instrument.
        * TRIGGER_LEVEL (*float*)
            * Trigger level.
        * TRIGGER_COUPLING (*AC*, *DC*, *LFReject*)
            * Trigger coupling type.
        * TRIGGER_EDGE (*BOTH*, *NEG*, *POS*, *ALT*)
            * Edge of waveform that the oscilloscope triggers on.
        * CH<X>_ENABLE (*bool*)
            * Enables or disables channel 'X'.
        * CH<X>_VOLTS_DIV (*float*)
            * The voltage per division for channel 'X'.
        * CH<X>_OFFSET (*float*)
            * The voltage offset for channel 'X'.
        * CH<X>_IMPEDANCE (*50*, *1e6*)
            * The imedance for channel 'X'.
        * CH<X>_LABEL (*str*)
            * Label for channel 'X'.
        * CH<X>_PROBE_ATTEN (*float*)
            * Probe attenuation for channel 'X'. For example, providing the value '10' would indicate a 10x or 10:1 probe.
        * CH<X>_COUPLING (*AC*, *DC*)
            * Coupling mode for channel 'X'.
        * CH<X>_INVERT (*bool*)
            * Enables or disables inversion of the waveform from channel 'X'.
        * CH<X>_FREQUENCY (*float*)
            * Output frequency of the waveform from channel 'X'.
        * CH<X>_BW_LIM (*float*)
            * Bandwidth limit of noise function for channel 'X'.
        * CH<X>_WAVEFORM (*SINE*, *SQUARE*, *TRIANGLE*, *RAMP*, *PULSE*, *PRBS*, *NOISE*, *ARBITRARY*, *DC*)
            * Shape of the modulating waveform for channel 'X'.
        * CH<X>_POLARITY (*bool*)
            * Enables or disables inversion of waveform relative to the offset voltage of channel 'X'.
        * CH<X>_TRIGGER_DELAY (*float*)
            * Time (in seconds) from assertion of trigger to occurrence of trigger event for channel 'X'.
        * CH<X>_AMPLITUDE (*float*)
            * Voltage amplitude of waveform of channel 'X'.
        * CH<X>_TRACK (*ON*, *OFF*, *INV*)
            * Enables or disables all channels to track (or inversely track) the output of channel 'X'.
        * CH<X>_TRIGGER_CHANNEL (*INT*, *EXT*)
            * Trigger source.
        * CH<X>_ENABLE_BURST (*bool*)
            * Enables or disables burst mode for channel 'X'.
        * CH<X>_BURST_MODE (*TRIG*, *GAT*)
            * Triggers bursts internally (TRIG) or externally (GAT) for channel 'X'.
        * CH<X>_BURST_CYCLES (*float*)
            * Number of cycles per burst for channel 'X'.
        * CH<X>_BURST_PER (*float*)
            * Burst period (in seconds) for channel 'X'.

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

        self.add_parameter(
            "DISPLAY",
            read_command="CHAN:DISP?",
            set_command="CHAN:DISP {}",
            dummy_return="True",
        )
        self.add_lookup("DISPLAY", {"True": "1", "False": "0"})

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
                pre_hooks=[max_len_converter(32)],
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

            self.add_parameter(
                f"CH{ch}_TRIGGER_CHANNEL",
                read_command=f"TRIG{ch}:SOUR?",
                set_command=f"TRIG{ch}:SOUR {{}}",
                dummy_return="1",
            )

            self.add_parameter(
                f"CH{ch}_TRIGGER_LEVEL",
                read_command=f"TRIG{ch}:EDGE:LEV?",
                set_command=f"TRIG{ch}:EDGE:LEV {{}}",
                pre_hooks=[format_float(".6E")],
                dummy_return="10",
            )

            self.add_parameter(
                f"CH{ch}_TRIGGER_COUPLING",
                read_command=f"TRIG{ch}:COUP?",
                set_command=f"TRIG{ch}:COUP {{}}",
                pre_hooks=[expected_input_validator(["AC", "DC", "LFReject"], "DC")],
                dummy_return="DC",
            )

            self.add_parameter(
                f"CH{ch}_TRIGGER_EDGE",
                read_command=f"TRIG{ch}:EDGE:SLOP?",
                set_command=f"TRIG{ch}:EDGE:SLOP {{}}",
                pre_hooks=[expected_input_validator(["NEG", "POS"], "POS")],
                dummy_return="POS",
            )

            self.add_parameter(
                f"CH{ch}_ENABLE_BURST",
                read_command=f"SOUR{ch}:BURS:STAT?",
                set_command=f"SOUR{ch}:BURS:STAT {{}}",
                dummy_return="0",
            )
            self.add_lookup(f"CH{ch}_ENABLE_BURST", {"ON": "1", "OFF": "0"})

            self.add_parameter(
                f"CH{ch}_BURST_MODE",
                read_command=f"SOUR{ch}:BURS:MODE?",
                set_command=f"SOUR{ch}:BURS:MODE {{}}",
                pre_hooks=[expected_input_validator(["TRIG", "GAT"])],
                dummy_return="TRIG",
            )

            self.add_parameter(
                f"CH{ch}_BURST_CYCLES",
                read_command=f"SOUR{ch}:BURS:NCYC?",
                set_command=f"SOUR{ch}:BURS:NCYC {{}}",
                dummy_return="1",
            )

            self.add_parameter(
                f"CH{ch}_BURST_PER",
                read_command=f"SOUR{ch}:BURS:INT:PER?",
                set_command=f"SOUR{ch}:BURS:INT:PER {{}}",
                dummy_return="10",
            )

            self.add_parameter(
                f"CH{ch}_FREQUENCY",
                read_command=f"SOUR{ch}:FREQ?",
                set_command=f"SOUR{ch}:FREQ {{}}",
                pre_hooks=[scaling_converter(1e6), format_float(".6E")],
                post_hooks=[substring_hook(0, -1)],
                dummy_return="20",
            )

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
                pre_hooks=[uppercase],
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
                pre_hooks=[lambda value: "ON" if value is True else "OFF"],
                post_hooks=[lambda value: value == "1\n"],
                dummy_return="False",
            )

            self.add_parameter(
                f"CH{ch}_POLARITY",
                read_command=f"OUTP{ch}:POL?",
                set_command=f":OUTP{ch}:POL {{}}",
                dummy_return="1",
            )

            self.add_parameter(
                f"CH{ch}_TRIGGER_DELAY",
                read_command="TRIG1:DEL?",
                set_command="TRIG1:DEL {}",
                pre_hooks=[format_float(".6E")],
                dummy_return="0",
            )

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
                read_command=f"SOUR{ch}:TRAC?",
                set_command=f"SOUR{ch}:TRAC {{}}",
                dummy_return="1",
            )
