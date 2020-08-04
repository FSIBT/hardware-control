"""Keysight 33500 waveform and function generator.

See class definition for deails.

"""

import logging

from ..base import Backend, ensure_online
from ..utility import get_channel_from_command

logger = logging.getLogger(__name__)

# a lookup table to convert from pulse shape to the correct Keysight
# command
waveform_lookup = {
    "Sine": "SIN",
    "Square": "SQU",
    "Triangle": "TRI",
    "Ramp": "RAMP",
    "Pulse": "PULS",
    "PRBS": "PRBS",
    "Noise": "NOIS",
    "Arbitrary": "ARB",
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

        if setting_X == "CHX_enable":
            if value == "True":
                self.write(":OUTP ON")
            else:
                self.write(":OUTP OFF")
            rval = self.query(":OUTP?")
            return str(rval == "1\n")
        if setting_X == "CHX_waveform":
            wvfm = waveform_lookup[value]
            self.write(f":SOUR:FUNC {wvfm}")
            rval = self.query(":SOUR:FUNC?")
            return rval[:-1]  # Trim newline character
        if setting_X == "CHX_frequency":
            self.write(f":FREQ {float(value):.6E}")
            rval = self.query(":FREQ?")
            return rval[:-1]
        if setting_X == "CHX_amplitude":
            self.write(f":VOLT {float(value):.6E}")
            rval = self.query(":VOLT?")
            return rval[:-1]
        if setting_X == "CHX_offset":
            self.write(f":VOLT:OFFS {float(value):.6E}")
            rval = self.query(":VOLT:OFFS?")
            return rval[:-1]
        if setting_X == "CHX_volts_div":
            self.write(f":CHAN{channel}:SCAL {float(value):.6E}")
            return self.query(f":CHAN{channel}:SCAL?")
        if setting == "timebase":
            self.write(f":TIM:SCAL {float(value):.6E}")
            return self.query(":TIM:SCAL?")
        if setting == "time_offset":
            self.write(f":TIM:POS {float(value):.6E}")
            return self.query(":TIM:POS?")
        if setting_X == "CHX_offset":
            self.write(f"CHAN{channel}:OFFS {-float(value):.6E}")
            return self.query(f"CHAN{channel}:OFFS?")
        if setting_X == "CHX_BW_lim":
            self.write(f"CHAN{channel}:BWL {int(value=='True')}")
            return self.query(f"CHAN{channel}:BWL?")
        if setting_X == "CHX_active":
            self.write(f"CHAN{channel}:DISP {int(value=='True')}")
            return self.query(f"CHAN{channel}:DISP?")
        if setting_X == "CHX_impedance":
            if value == "50":
                self.write(f"CHAN{channel}:IMP FIFT")
            else:
                self.write(f"CHAN{channel}:IMP ONEM")
            return self.query(f"CHAN{channel}:IMP?")
        if setting_X == "CHX_label":
            # Length is capped at 32 characters
            if len(value) > 32:
                value = value[0:32]
            self.write(f"CHAN{channel}:LAB {value}")
            return self.query(f"CHAN{channel}:LAB?")
        if setting == "labels_enabled":
            self.write(f"DISP:LAB {int(value=='True')}")
            return self.query("DISP:LAB?")
        if setting_X == "CHX_invert":
            self.write(f"CHAN{channel}:INV {int(value=='True')}")
            return self.query(f"CHAN{channel}:INV?")
        if setting_X == "CHX_probe_atten":
            self.write(f"CHAN{channel}:PROB {float(value):.6E}")
            return self.query(f"CHAN{channel}:PROB?")  # ie. 10 gives x10 or 10:1 probe
        if setting_X == "CHX_coupling":
            # Make sure valid value provided
            if value not in ["AC", "DC"]:
                value = "DC"
            self.write(f"CHAN{channel}:COUP {value}")
            return self.query(f"CHAN{channel}:COUP?")
        if setting == "trigger_level":
            self.write(f"TRIG:EDGE:LEV {float(value):.6E}")
            return self.query("TRIG:EDGE:LEV?")
        if setting == "trigger_coupling":
            # Make sure valid option given
            if value not in ["AC", "DC", "LFReject"]:
                value = "DC"
            self.write(f"TRIG:COUP {value}")
            return self.query("TRIG:COUP?")
        if setting == "trigger_edge":
            # Make sure valid option given
            if value not in ["BOTH", "NEG", "POS", "ALT"]:
                value = "POS"
            self.write(f"TRIG:EDGE:SLOP {value}")
            return self.query("TRIG:EDGE:SLOP?")
        if setting == "trigger_channel":
            self.write(f"TRIG:SOUR CHAN{int(value)}")
            return self.query("TRIG:SOUR?")

    @ensure_online
    def command(self, cmd: str):
        pass
