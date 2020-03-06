import re

from hardware_control.HC_Backend import HC_Backend, VISA


def str_NR3(x: str):
    x_float = float(x)
    return f" {x_float:.6E}"


def str_to_bool(x: str):
    if x == "True":
        return True
    else:
        return False


def regex_compare(pattern: str, comp: str):
    regex = re.compile(pattern)
    return bool(re.match(regex, comp))


class SigSDGCtrl(HC_Backend):
    def __init__(self, connection_addr, dummy: bool = False, debug: bool = False):

        super().__init__()
        self.ID = "SIGLENT-SDG"

        self.connection_addr = connection_addr
        self.online = False
        self.dummy = dummy
        self.debug = debug

        self.connection_type = VISA

        self.check()

    def update_setting(self, setting: str, value):

        try:
            if self.dummy:
                return value
            else:

                # Note: We ignore channel number because there is only
                # one channel on this model of AWG
                if regex_compare("CH._enabled", setting):

                    chan = setting[2]

                    if str_to_bool(value):
                        self.write(f"C{chan}:OUTP ON")
                    else:
                        self.write(f"C{chan}:OUTP OFF")
                    rval = self.query(f"C{chan}:OUTP?")
                    return str(rval[8:10] == "ON")

                elif regex_compare("CH._waveform", setting):

                    chan = setting[2]

                    wvfm = "SIN"
                    if value == "Sine":
                        wvfm = "SINE"
                    elif value == "Square":
                        wvfm = "SQUARE"
                    elif value == "Triangle":
                        wvfm = "RAMP"
                    elif value == "Ramp":
                        wvfm = "RAMP"
                    elif value == "Pulse":
                        wvfm = "PULSE"
                    elif value == "PRBS":  # Pseudo-random binary sequence
                        wvfm = "PRBS"
                    elif value == "Noise":
                        wvfm = "NOISE"
                    elif value == "Arbitrary":
                        wvfm = "ARB"
                    elif value == "DC":
                        wvfm = "DC"

                    self.write(f"C{chan}:BSWV WVTP,{wvfm}")
                    rval = self.query(f":C{chan}:BSWV?")
                    return rval[:-1]  # Trim newline character

                elif regex_compare("CH._frequency", setting):

                    chan = setting[2]

                    self.write(f"C{chan}:BSWV FRQ,{str_NR3(value.upper())}")
                    rval = self.query(f"C{chan}:BSWV?")
                    return rval[:-1]

                elif regex_compare("CH._amplitude", setting):

                    chan = setting[2]

                    self.write(f"C{chan}:BSWV AMP,{str_NR3(value)}")
                    rval = self.query(f"C{chan}:BSWV?")
                    return rval[:-1]

                elif regex_compare("CH._offset", setting):

                    chan = setting[2]

                    self.write(f"C{chan}:BSWV OFST,{str_NR3(value)}")
                    rval = self.query(f"C{chan}:BSWV?")
                    return rval[:-1]

                elif regex_compare("CH._impedance", setting):

                    chan = setting[2]

                    if value == "50":
                        self.write(f"C{chan}:OUTP LOAD,50")
                    else:
                        self.write(f"C{chan}:OUTP LOAD,HZ")
                    rval = self.query(f"C{chan}:OUTP?")
                    return rval[:-1]

        except Exception as e:
            self.pDebug(
                "An error occured in SigSDGCtrl.py when sending SCPI commands to the instrument."
            )
            self.pDebug(str(e))

    def command(self, cmd: str):
        pass
