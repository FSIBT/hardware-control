from hardware_control.HC_Backend import HC_Backend, VISA
from hardware_control.utility import (
    regex_compare,
    to_NR3,
    str_NR3,
    str_NR1,
    boolstr_NR1,
    str_to_bool,
)
import logging

logger = logging.getLogger(__name__)


class Key33500BCtrl(HC_Backend):
    def __init__(
        self, connection_addr: str,
    ):
        super().__init__()
        self.ID = "KEYSIGHT-33500B"

        self.connection_addr = connection_addr
        self.online = False
        self.dummy = False
        self.num_vert_divisions = 8

        self.parse_connection_addr()

        if self.connection_type == "socket":
            try:
                tokens = self.connection_addr.split(":", 1)
                self.ip_addr = tokens[0]
                self.port_no = int(tokens[1])
            except:
                logger.warning(
                    f"Failed to get address, port from {self.connection_addr}",
                    exc_info=True,
                )

        self.check()

    def update_setting(self, setting: str, value):

        try:
            if self.dummy:
                return value
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of AWG
                if regex_compare("CH._enable", setting):
                    if str_to_bool(value):
                        self.write(":OUTP ON")
                    else:
                        self.write(":OUTP OFF")
                    rval = self.query(":OUTP?")
                    return str(rval == "1\n")
                elif regex_compare("CH._waveform", setting):
                    wvfm = "SIN"
                    if value == "Sine":
                        wvfm = "SIN"
                    elif value == "Square":
                        wvfm = "SQU"
                    elif value == "Triangle":
                        wvfm = "TRI"
                    elif value == "Ramp":
                        wvfm = "RAMP"
                    elif value == "Pulse":
                        wvfm = "PULS"
                    elif value == "PRBS":  # Pseudo-random binary sequence
                        wvfm = "PRBS"
                    elif value == "Noise":
                        wvfm = "NOIS"
                    elif value == "Arbitrary":
                        wvfm = "ARB"
                    elif value == "DC":
                        wvfm = "DC"
                    self.write(f":SOUR:FUNC {wvfm}")
                    rval = self.query(":SOUR:FUNC?")
                    return rval[:-1]  # Trim newline character
                elif regex_compare("CH._frequency", setting):
                    self.write(f":FREQ {str_NR3(value)}")
                    rval = self.query(":FREQ?")
                    return rval[:-1]
                elif regex_compare("CH._amplitude", setting):
                    self.write(f":VOLT {str_NR3(value)}")
                    rval = self.query(":VOLT?")
                    return rval[:-1]
                elif regex_compare("CH._offset", setting):
                    self.write(f":VOLT:OFFS {str_NR3(value)}")
                    rval = self.query(":VOLT:OFFS?")
                    return rval[:-1]

                if regex_compare("CH._volts_div", setting):
                    chan = setting[2]
                    self.write(f":CHAN{chan}:SCAL {str_NR3(value)}")
                    return self.query(f":CHAN{chan}:SCAL?")

                elif setting == "timebase":
                    self.write(f":TIM:SCAL {str_NR3(value)}")
                    return self.query(":TIM:SCAL?")

                elif setting == "time_offset":
                    self.write(f":TIM:POS {str_NR3(value)}")
                    return self.query(":TIM:POS?")

                elif regex_compare("CH._offset", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:OFFS {to_NR3(-1.0 * float(value))}")
                    return self.query(f"CHAN{chan}:OFFS?")

                elif regex_compare("CH._BW_lim", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:BWL {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:BWL?")

                elif regex_compare("CH._active", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:DISP {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:DISP?")

                elif regex_compare("CH._impedance", setting):
                    chan = setting[2]
                    if value == "50":
                        self.write(f"CHAN{chan}:IMP FIFT")
                    else:
                        self.write(f"CHAN{chan}:IMP ONEM")
                    return self.query(f"CHAN{chan}:IMP?")

                elif regex_compare("CH._label", setting):

                    # Length is capped at 32 characters
                    if len(value) > 32:
                        value = value[0:32]

                    chan = setting[2]
                    self.write(f"CHAN{chan}:LAB {value}")
                    return self.query(f"CHAN{chan}:LAB?")

                elif setting == "labels_enabled":
                    self.write(f"DISP:LAB {boolstr_NR1(value)}")
                    return self.query(f"DISP:LAB?")

                elif regex_compare("CH._invert", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:INV {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:INV?")

                elif regex_compare("CH._probe_atten", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:PROB {str_NR3(value)}")
                    return self.query(
                        f"CHAN{chan}:PROB?"
                    )  # ie. 10 gives x10 or 10:1 probe

                elif regex_compare("CH._coupling", setting):
                    chan = setting[2]

                    # Make sure valid value provided
                    if value != "AC" and value != "DC":
                        value = "DC"

                    self.write(f"CHAN{chan}:COUP {value}")
                    return self.query(f"CHAN{chan}:COUP?")

                elif setting == "trigger_level":
                    self.write(f"TRIG:EDGE:LEV {str_NR3(value)}")
                    return self.query(f"TRIG:EDGE:LEV?")

                elif setting == "trigger_coupling":

                    # Make sure valid option given
                    if value != "AC" and value != "DC" and value != "LFReject":
                        value = "DC"

                    self.write(f"TRIG:COUP {value}")
                    return self.query(f"TRIG:COUP?")

                elif setting == "trigger_edge":

                    # Make sure valid option given
                    if (
                        value != "BOTH"
                        and value != "NEG"
                        and value != "POS"
                        and value != "ALT"
                    ):
                        value = "POS"

                    self.write(f"TRIG:EDGE:SLOP {value}")
                    return self.query(f"TRIG:EDGE:SLOP?")

                elif setting == "trigger_channel":

                    self.write(f"TRIG:SOUR CHAN{str_NR1(value)}")
                    return self.query(f"TRIG:SOUR?")
        except Exception as e:
            logger.error(
                "An error occured in Key33500BCtrl.py when sending SCPI commands to the instrument.",
                exc_info=True,
            )

    def command(self, cmd: str):
        pass
