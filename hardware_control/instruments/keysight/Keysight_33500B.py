"""Keysight 33500 waveform and function generator.

.. image:: /images/Keysight33500B.png
  :height: 200

See class definition for deails.

"""

import logging

from ...base import Instrument
from ...base.hooks import (
    floater,
    create_return_value,
    min_len_converter,
    expected_input_validator,
    scaling_converter,
    parse_converter,
    uppercase,
)

logger = logging.getLogger(__name__)


class Keysight_33500B(Instrument):
    """Backend for Keysight 33500B arbitrary waveform generator.

    Instrument home page: https://www.keysight.com/us/en/products/waveform-and-function-generators/trueform-series-waveform-and-function-generators.html


    Parameters
    ----------
    connection_addr : str
        Address of instrument. Can use Visa address or socket and port.
    """

    def __init__(self, name, connection_addr):
        super().__init__(name, connection_addr, 5025)

        self.num_vert_divisions = 8
        self.check_connection_commands = "*IDN?"

        self.add_parameter(
            "CH1_VOLTS_DIV",
            read_command=":CHAN1:SCAL?",
            set_command=":CHAN1:SCAL {}",
            pre_hooks=[floater("6E")],
            post_hooks=[create_return_value("CH1_VOLTS_DIV")],
            dummy_return="",
        )
        self.add_lookup("CH1_VOLTS_DIV", {"POSITIVE": "1", "NEGATIVE": "0"})

        self.add_parameter(
            "TIMEBASE",
            read_command=":TIM:SCAL?",
            set_command=":TIM:SCAL {}",
            pre_hooks=[floater("6E")],
            post_hooks=[create_return_value("TIMEBASE")],
            dummy_return="",
        )

        self.add_parameter(
            "TIME_OFFSET",
            read_command=":TIM:POS?",
            set_command=":TIM:POS {}",
            pre_hooks=[floater("6E")],
            post_hooks=[create_return_value("TIME_OFFSET")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_LABEL",
            read_command="CHAN1:LAB?",
            set_command="CHAN1:LAB {}",
            pre_hooks=[min_len_converter(32)],
            post_hooks=[create_return_value("CH1_LABEL")],
            dummy_return="",
        )

        self.add_parameter(
            "LABELS_ENABLED",
            read_command="DISP:LAB?",
            set_command="DISP:LAB {}",
            post_hooks=[create_return_value("LABELS_ENABLED")],
            dummy_return="",
        )
        self.add_lookup("LABELS_ENABLED", {"True": "1", "False": "0"})

        self.add_parameter(
            "CH1_INVERT",
            read_command="CHAN1:INV?",
            set_command="CHAN1:INV {}",
            post_hooks=[create_return_value("CH1_INVERT")],
            dummy_return="",
        )
        self.add_lookup("CH1_INVERT", {"True": "1", "False": "0"})

        self.add_parameter(
            "CH1_PROBE_ATTEN",
            read_command="CHAN1:PROB?",
            set_command="CHAN1:PROB {}",
            pre_hooks=[floater("6E")],
            post_hooks=[create_return_value("CH1_PROBE_ATTEN")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_COUPLING",
            read_command="CHAN1:COUP?",
            set_command="CHAN1:COUP {}",
            pre_hooks=[expected_input_validator(["AC", "DC"], "DC")],
            post_hooks=[create_return_value("CH1_COUPLING")],
            dummy_return="",
        )

        """    BURSt Subsystem    """
        self.add_parameter(
            "CH1_BURS_MODE",
            read_command="SOUR1:BURS:MODE?",
            set_command="SOUR1:BURS:MODE {}",
            post_hooks=[create_return_value("CH1_BURS_MODE")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_BURS_STAT",
            read_command="SOUR1:BURS:STAT?",
            set_command="SOUR1:BURS:STAT {}",
            post_hooks=[create_return_value("CH1_BURS_STAT")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_BURS_NCYC",
            read_command="SOUR1:BURS:NCYC?",
            set_command="SOUR1:BURS:NCYC {}",
            post_hooks=[create_return_value("CH1_BURS_NCYC")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_BURS_PER",
            read_command="SOUR1:BURS:INT:PER?",
            set_command="SOUR1:BURS:INT:PER {}",
            post_hooks=[create_return_value("CH1_BURS_PER")],
            dummy_return="",
        )

        """    DISPlay Subsystem    """
        self.add_parameter(
            "CH1_ACTIVE",
            read_command="CHAN1:DISP?",
            set_command="CHAN1:DISP {}",
            post_hooks=[create_return_value("CH1_ACTIVE")],
            dummy_return="",
        )
        self.add_lookup("CH1_ACTIVE", {"True": "1", "False": "0"})

        """    FREQuency Subsystem    """
        self.add_parameter(
            "CH1_FREQUENCY",
            read_command="SOUR1:FREQ?",
            set_command="SOUR1:FREQ {}",
            pre_hooks=[scaling_converter(1e6), floater("6E")],
            post_hooks=[
                parse_converter(0, -1),
                create_return_value("CH1_FREQUENCY", "Hz"),
            ],
            dummy_return="",
        )

        """    FUNCtion Subsystem    """
        # FUNCtion:NOISe:BANDwidth - bandwidth for NOISe waveform
        self.add_parameter(
            "CH1_BW_LIM",
            read_command="CHAN1:BWL?",
            set_command="CHAN1:BWL {}",
            post_hooks=[create_return_value("CH1_BW_LIM")],
            dummy_return="",
        )
        self.add_lookup("CH1_BW_LIM", {"True": "1", "False": "0"})

        self.add_parameter(
            "CH1_WAVEFORM",
            read_command=":SOUR1:FUNC?",
            set_command=":SOUR1:FUNC {}",
            pre_hooks=[uppercase()],
            post_hooks=[create_return_value("CH1_WAVEFORM")],
            dummy_return="",
        )
        self.add_lookup(
            "CH1_WAVEFORM",
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
            "CH1_IMPEDANCE",
            read_command="OUTP1:LOAD?",
            set_command="OUTP1:LOAD {}",
            pre_hooks=[lambda x: "50" if value == "50 (OHM)" else "INF"],
            post_hooks=[create_return_value("CH1_IMPEDANCE")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_ENABLE",
            read_command=":OUTP1?",
            set_command=":OUTP1 {}",
            pre_hooks=[lambda x: "ON" if value == True else "OFF"],
            post_hooks=[
                lambda x: True if value == "1\n" else False,
                create_return_value("CH1_ENABLE"),
            ],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_POLARITY",
            read_command="OUTP1:POL?",
            set_command=":OUTP1:POL {}",
            post_hooks=[create_return_value("CH1_POLARITY")],
            dummy_return="",
        )

        """    TRIGger Subsystem    """
        self.add_parameter(
            "TRIGGER_LEVEL",
            read_command="TRIG:EDGE:LEV?",
            set_command="TRIG:EDGE:LEV {}",
            pre_hooks=[floater("6E")],
            post_hooks=[create_return_value("TRIGGER_LEVEL")],
            dummy_return="",
        )

        self.add_parameter(
            "TRIGGER_COUPLING",
            read_command="TRIG:COUP?",
            set_command="TRIG:COUP {}",
            pre_hooks=[expected_input_validator(["AC", "DC", "LFReject"], "DC")],
            post_hooks=[create_return_value("TRIGGER_COUPLING")],
            dummy_return="",
        )

        self.add_parameter(
            "TRIGGER_EDGE",
            read_command="TRIG:EDGE:SLOP?",
            set_command="TRIG:EDGE:SLOP {}",
            pre_hooks=[expected_input_validator(["BOTH", "NEG", "POS", "ALT"], "POS")],
            post_hooks=[create_return_value("TRIGGER_EDGE")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_TRIGGER_CHANNEL",
            read_command="TRIG1:SOUR?",
            set_command="TRIG1:SOUR {}",
            post_hooks=[create_return_value("CH1_TRIGGER_CHANNEL")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_TRIGGER_DELAY",
            read_command="TRIG1:DEL?",
            set_command="TRIG1:DEL {}",
            pre_hooks=[floater("6E")],
            post_hooks=[create_return_value("CH1_TRIGGER_DELAY")],
            dummy_return="",
        )

        """    VOLT Subsystem    """
        self.add_parameter(
            "CH1_AMPLITUDE",
            read_command=":VOLT?",
            set_command="SOUR1:VOLT {}",
            pre_hooks=[floater("6E")],
            post_hooks=[parse_converter(0, -1), create_return_value("CH1_AMPLITUDE")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_OFFSET",
            read_command=":VOLT?",
            set_command="SOUR1:VOLT:OFFS {}",
            pre_hooks=[floater("6E")],
            post_hooks=[parse_converter(0, -1), create_return_value("CH1_OFFSET")],
            dummy_return="",
        )

        self.add_parameter(
            "CH1_TRACK",
            read_command="TRAC?",
            set_command="SOUR1:TRAC {}",
            post_hooks=[create_return_value("CH1_TRACK")],
            dummy_return="",
        )
