"""Keysight 33500 waveform and function generator.

.. image:: /images/Keysight33500B.png
  :height: 200

See class definition for deails.

"""

import logging

from ..base import Backend, ensure_online
from ..utility import get_channel_from_command

logger = logging.getLogger(__name__)

# a lookup table to convert from pulse shape to the correct Keysight
# command
waveform_lookup = {
    "SINE": "SIN",
    "SQUARE": "SQU",
    "TRIANGLE": "TRI",
    "RAMP": "RAMP",
    "PULSE": "PULS",
    "PRBS": "PRBS",
    "NOISE": "NOIS",
    "ARBITRARY": "ARB",
    "DC": "DC",
}


class Keysight_33500B(Backend):
    """ Backend for Keysight 33500B arbitrary waveform generator.

    Instrument home page: https://www.keysight.com/us/en/products/waveform-and-function-generators/trueform-series-waveform-and-function-generators.html


    Parameters
    ----------
    connection_addr : str
        Address of instrument. Can use Visa address or socket and port.
    """

    def __init__(self, connection_addr: str):
        super().__init__(
            instrument_name="KEYSIGHT-33500B",
            connection_addr=connection_addr,
            default_port=5025,
        )
        self.num_vert_divisions = 8

        self.check_connection_commands = "*IDN?"

    @ensure_online
    def update_setting(self, setting: str, value):
        """ Called by hc.Comm object. Updates a setting in the instrument.

        Parameters
        ----------
        setting : str
            Name of setting to modify
        vale : str
            New value for setting

        Returns
        -------
        str
            Returns a string suggesting if the operation was successful.

        Note
        ----

        We ignore channel number because there is only one channel on
        this model of AWG

        """
        if self.dummy:
            return value

        channel, setting_X = get_channel_from_command(setting)

        if setting_X == "CHX_ENABLE":
            if value == "True":
                self.write(":OUTP ON")
            else:
                self.write(":OUTP OFF")
            rval = self.query(":OUTP?")
            rval = rval == "1\n"
            return f"{setting}={rval}"
        if setting_X == "CHX_WAVEFORM":
            wvfm = waveform_lookup[value]
            self.write(f":SOUR:FUNC {wvfm}")
            rval = self.query(":SOUR:FUNC?")
            rval = rval[:-1]  # Trim newline character
            return f"{setting}={rval}"
        if setting_X == "CHX_FREQUENCY":
            self.write(f":FREQ {float(value):.6E}")
            rval = self.query(":FREQ?")
            rval = rval[:-1]
            return f"{setting}={rval}"
        if setting_X == "CHX_AMPLITUDE":
            self.write(f":VOLT {float(value):.6E}")
            rval = self.query(":VOLT?")
            rval = rval[:-1]
            return f"{setting}={rval}"
        if setting_X == "CHX_OFFSET":
            self.write(f":VOLT:OFFS {float(value):.6E}")
            rval = self.query(":VOLT:OFFS?")
            rval = rval[:-1]
            return f"{setting}={rval}"
        if setting_X == "CHX_VOLTS_DIV":
            self.write(f":CHAN{channel}:SCAL {float(value):.6E}")
            rval = self.query(f":CHAN{channel}:SCAL?")
            return f"{setting}={rval}"
        if setting == "TIMEBASE":
            self.write(f":TIM:SCAL {float(value):.6E}")
            rval = self.query(":TIM:SCAL?")
            return f"{setting}={rval}"
        if setting == "TIME_OFFSET":
            self.write(f":TIM:POS {float(value):.6E}")
            rval = self.query(":TIM:POS?")
            return f"{setting}={rval}"
        if setting_X == "CHX_OFFSET":
            self.write(f"CHAN{channel}:OFFS {-float(value):.6E}")
            rval = self.query(f"CHAN{channel}:OFFS?")
            return f"{setting}={rval}"
        if setting_X == "CHX_BW_LIM":
            self.write(f"CHAN{channel}:BWL {int(value=='True')}")
            rval = self.query(f"CHAN{channel}:BWL?")
            return f"{setting}={rval}"
        if setting_X == "CHX_ACTIVE":
            self.write(f"CHAN{channel}:DISP {int(value=='True')}")
            rval = self.query(f"CHAN{channel}:DISP?")
            return f"{setting}={rval}"
        if setting_X == "CHX_IMPEDANCE":
            if value == "50":
                self.write(f"CHAN{channel}:IMP FIFT")
            else:
                self.write(f"CHAN{channel}:IMP ONEM")
            rval = self.query(f"CHAN{channel}:IMP?")
            return f"{setting}={rval}"
        if setting_X == "CHX_LABEL":
            # Length is capped at 32 characters
            if len(value) > 32:
                value = value[0:32]
            self.write(f"CHAN{channel}:LAB {value}")
            rval = self.query(f"CHAN{channel}:LAB?")
            return f"{setting}={rval}"
        if setting == "LABELS_ENABLED":
            self.write(f"DISP:LAB {int(value=='True')}")
            rval = self.query("DISP:LAB?")
            return f"{setting}={rval}"
        if setting_X == "CHX_INVERT":
            self.write(f"CHAN{channel}:INV {int(value=='True')}")
            rval = self.query(f"CHAN{channel}:INV?")
            return f"{setting}={rval}"
        if setting_X == "CHX_PROBE_ATTEN":
            self.write(f"CHAN{channel}:PROB {float(value):.6E}")
            rval = self.query(f"CHAN{channel}:PROB?")  # ie. 10 gives x10 or 10:1 probe
            return f"{setting}={rval}"
        if setting_X == "CHX_COUPLING":
            # Make sure valid value provided
            if value not in ["AC", "DC"]:
                value = "DC"
            self.write(f"CHAN{channel}:COUP {value}")
            rval = self.query(f"CHAN{channel}:COUP?")
            return f"{setting}={rval}"
        if setting == "TRIGGER_LEVEL":
            self.write(f"TRIG:EDGE:LEV {float(value):.6E}")
            rval = self.query("TRIG:EDGE:LEV?")
            return f"{setting}={rval}"
        if setting == "TRIGGER_COUPLING":
            # Make sure valid option given
            if value not in ["AC", "DC", "LFReject"]:
                value = "DC"
            self.write(f"TRIG:COUP {value}")
            rval = self.query("TRIG:COUP?")
            return f"{setting}={rval}"
        if setting == "TRIGGER_EDGE":
            # Make sure valid option given
            if value not in ["BOTH", "NEG", "POS", "ALT"]:
                value = "POS"
            self.write(f"TRIG:EDGE:SLOP {value}")
            rval = self.query("TRIG:EDGE:SLOP?")
            return f"{setting}={rval}"
        if setting == "TRIGGER_CHANNEL":
            self.write(f"TRIG:SOUR CHAN{int(value)}")
            rval = self.query("TRIG:SOUR?")
            return f"{setting}={rval}"

    @ensure_online
    def command(self, cmd: str):
        pass
