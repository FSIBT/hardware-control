# >>> scope.write("MEAS:STAT:ITEM VRMS,CHAN2")
# >>> scope.query("MEAS:ITEM? VRMS,CHAN2")
from hardware_control.HC_Backend import HC_Backend, VISA
from hardware_control.utility import returnChannelNumber
from hardware_control.utility import (
    regex_compare,
    to_NR3,
    str_NR3,
    str_NR1,
    boolstr_NR1,
)
import numpy as np
import logging

logger = logging.getLogger(__name__)


class RigDS1000ZCtrl(HC_Backend):

    # sigReturnWaves = pyqtSignal(int, list, list)

    def __init__(
        self, connection_addr,
    ):
        super().__init__()
        self.ID = "RIGOL-DS1000Z"

        self.connection_addr = connection_addr
        self.parse_connection_addr()

        self.online = False
        self.dummy = False
        self.num_vert_divisions = 8

        self.use_avg = False

        self.measurements = ["", "", "", "", ""]
        self.check()

    def update_setting(self, setting: str, value):

        if not self.online:
            return "Offline"

        try:
            if self.dummy:
                return value
            else:
                if regex_compare("CH._volts_div", setting):
                    chan = setting[2]
                    self.write(f":CHAN{chan}:SCAL {str_NR3(value)}")
                    return self.query(f":CHAN{chan}:SCAL?")

                elif setting == "timebase":
                    self.write(f":TIM:MAIN:SCAL {str_NR3(value)}")
                    return self.query(":TIM:MAIN:SCAL?")

                elif setting == "time_offset":
                    self.write(f":TIM:MAIN:OFFS {str_NR3(value)}")
                    return self.query(":TIM:MAIN:OFFS?")

                elif regex_compare("CH._offset", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:OFFS {to_NR3(-1.0 * float(value))}")
                    return self.query(f"CHAN{chan}:OFFS?")

                elif regex_compare("CH._BW_lim", setting):
                    chan = setting[2]
                    if value == "True":
                        self.write(f"CHAN{chan}:BWL 20M")
                    else:
                        self.write(f"CHAN{chan}:BWL OFF")
                    return self.query(f"CHAN{chan}:BWL?")

                elif regex_compare("CH._active", setting):
                    chan = setting[2]
                    self.write(f"CHAN{chan}:DISP {boolstr_NR1(value)}")
                    return self.query(f"CHAN{chan}:DISP?")

                elif regex_compare("CH._impedance", setting):

                    # This feature is not available on this model
                    pass

                elif regex_compare("CH._label", setting):  # TODO

                    # Length is capped at 32 characters
                    if len(value) > 32:
                        value = value[0:32]

                    chan = setting[2]
                    self.write(f"CHAN{chan}:LAB {value}")
                    return self.query(f"CHAN{chan}:LAB?")

                elif setting == "labels_enabled":  # TODO
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
                    if (
                        value != "AC"
                        and value != "DC"
                        and value != "LFReject"
                        and value != "HFReject"
                    ):
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

                    # This model does not support BOTH mode
                    if value == "BOTH":
                        value = "POS"

                    # This model calls altermating mode 'RFALI'
                    if value == "ALT":
                        value = "RFALI"

                    self.write(f"TRIG:EDGE:SLOP {value}")
                    return self.query(f"TRIG:EDGE:SLOP?")

                elif setting == "trigger_channel":

                    self.write(f"TRIG:EDG:SOUR CHAN{str_NR1(value)}")
                    return self.query(f"TRIG:EDG:SOUR?")
                elif regex_compare(
                    "meas_slot.", setting
                ):  # Value must follow pattern 'meas_parameter','source_channel'

                    # Get slot number
                    slot = int(setting[9])
                    if slot > 5 or slot < 0:
                        return "Bad setting"

                    # Update slot value
                    self.measurements[slot - 1] = value

                    # Write all slots
                    for slot, meas in enumerate(self.measurements):
                        if meas != "":
                            self.write(f":MEAS:STAT:ITEM {meas}")
                elif regex_compare("use_meas_avg", setting):

                    self.use_avg = boolstr_NR1(value)
                    return f"Use avg.: {value}"

                elif setting == "meas_stat_enabled":

                    self.write(f":MEAS:STAT:DISP {boolstr_NR1(value)}")
                    return self.query(":MEAS:STAT:DISP?")

        except Exception as e:
            logger.error(
                "An error occured in RigDS1000ZCtrl.py sending SCPI commands.",
                exc_info=True,
            )

    def command(self, cmd: str):

        ret_str = ""

        add_asterisk = False
        if cmd[-1] == "*":
            add_asterisk = True
            cmd = cmd[0:-1]

        if not self.online:
            return "Offline"

        if cmd == "SINGLE_TRIGGER":
            self.write(":SING")
            ret_str = "SINGLE_TRIGGER"
        elif cmd == "RUN":
            self.write(":RUN")
            ret_str = "RUN"
        elif cmd == "STOP":
            self.write(":STOP")
            ret_str = "STOP"
        elif cmd == "CLEAR_MEAS":
            self.write("MEAS:CLEAR ALL")
            ret_str = "CLEAR_MEAS"
        elif regex_compare("meas_slot.", cmd):

            logger.debug(f"Reading slot w/ '{cmd}'")

            # Get slot number
            slot = int(cmd[9])
            if slot > 5 or slot < 0:
                ret_str = "Bad command. Slot index out of range"
                if add_asterisk:  # Don't let Macro get locked indefinitely add asterisk
                    ret_str = ret_str + "*="
                return ret_str

            # Get measurement command for specified slot

            try:
                meas = self.measurements[slot - 1]
            except:
                ret_str = "Bad command. Slot index out of range"
                if add_asterisk:  # Don't let Macro get locked indefinitely add asterisk
                    ret_str = ret_str + "*="
                return ret_str

            # Read measurement
            if meas != "":
                try:

                    meas_mode = "CURR"
                    if self.use_avg:
                        meas_mode = "AVG"

                    ret_str = self.query(f":MEAS:STAT:ITEM? {meas_mode},{meas}")
                    if ret_str == None:
                        ret_str = f"Measurement_failure_{meas_mode},{meas}"
                except:
                    ret_str = ""
            else:
                ret_str = ""

            # Add description to return
            if add_asterisk:
                ret_str = cmd + "*=" + ret_str
            else:
                ret_str = cmd + "=" + ret_str
            logger.debug(f"Returning slot read w/ '{ret_str}'")
        elif cmd == "RESET_MEAS_STAT":

            self.write(f":MEAS:STAT:DISP OFF")
            self.write(f":MEAS:STAT:DISP ON")

            ret_str = cmd

        return ret_str

    def command_listdata(self, cmd: str):

        if not self.online:
            return "", [], []

        if regex_compare("CH.+_WVFM?", cmd):
            c = returnChannelNumber(cmd)
            return self.read_waveform(c)  # Returns a tuple (str, list, list)
        if regex_compare("CH.+_CLEAR", cmd):
            c = returnChannelNumber(cmd)
            return f"CH{c}_WVFM", [], []
        else:
            return "", [], []

    def single_trigger(self):
        """Tells oscilloscope to run with trigger mode set to single trigger"""
        if not self.dummy:
            self.write(":SING")

    def norm_trigger(self):
        """Tell oscilloscope to run with trigger mode set to normal"""
        if not self.dummy:
            self.write(":RUN")

    def set_measurement(self, parameter: str, avg: str):
        """Tells oscilloscope to enable a given measurement (eg. freq, Vpp_avg)"""
        pass

    def read_measurement(self, parameter: str, avg: str):
        """Reads measurement value from oscilloscope (if measurement first set
        by 'set_measurement()')"""
        pass

    #
    #
    # Returns (V, t) as float[]
    def read_waveform(self, channel: int):  # TODO
        """Reads a waveform from the oscilloscope."""

        if self.dummy or not self.online:
            t = np.linspace(0, 1e-3, 100, False)
            noise = 0.02 * np.random.rand(1, 100)

            # in the line below we have to take index 0 of 'noise' because noise
            # is 2D array w/ 1 row and we need a 1D array
            v = np.sin(t * 5e3 * float(channel)) + noise[0]

            return f"CH{channel}_WVFM", t.tolist(), v.tolist()

        try:

            self.write(f"WAV:SOUR CHAN{channel}")  # Specify channel to read
            self.write("WAV:MODE NORM")  # Specify to read data displayed on screen
            self.write("WAV:FORM ASCII")  # Specify data format to ASCII
            data = self.query("WAV:DATA?")  # Request data

            # Split string into ASCII voltage values
            volts = data[11:].split(",")

            # Convert strings to floats for every point
            for idx, v in enumerate(volts):
                volts[idx] = float(v)

            # #Pull header out of data, get number of point
            # TMC_data_desc_header = data[0:12].decode("utf-8")
            # npts = float(tmc[-4:])
            #
            # #Check that specified number of points matches number recieved
            # if npts != len(data)-12:
            #     return "", [], []

            # Get timing data
            xorigin = float(self.query("WAV:XOR?"))
            xincr = float(self.query("WAV:XINC?"))

            # Get time values
            t = list(
                np.linspace(xorigin, xorigin + xincr * (len(volts) - 1), len(volts))
            )

        except:
            logger.error(
                "ERROR: Failed to read waveform data from scope", exc_info=True
            )
            return "", [], []

        return f"CH{channel}_WVFM", t, volts
