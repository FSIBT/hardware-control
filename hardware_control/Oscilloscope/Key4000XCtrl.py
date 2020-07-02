import re
from hardware_control.HC_Backend import HC_Backend, VISA
from hardware_control.utility import (
    returnChannelNumber,
    regex_compare,
    to_NR3,
    str_NR3,
    str_NR1,
    boolstr_NR1,
)
import numpy as np
import logging

logger = logging.getLogger(__name__)


class Key4000XCtrl(HC_Backend):

    # sigReturnWaves = pyqtSignal(int, list, list)

    def __init__(
        self, connection_addr: str,
    ):
        super().__init__()
        self.ID = "KEYSIGHT-4000X"

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

        if not self.online:
            return "Offline"
        if self.dummy:
            return value
        try:
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
                return self.query(f"CHAN{chan}:PROB?")  # ie. 10 gives x10 or 10:1 probe

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
                "An error occured in Key4000XCtrl.py sending SCPI commands.",
                exc_info=True,
            )

    def command(self, cmd: str):
        if not self.online:
            return "Offline"

        if cmd == "SINGLE_TRIGGER":
            self.write(":SING")
        elif cmd == "RUN":
            self.write(":RUN")
        elif cmd == "CONFIG_READ_WAVE":
            self.configure_read_waveform()
        elif cmd == "STOP":
            self.write(":STOP")

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

    def digitize(self):
        """Similar to single trigger. Aquires waveform according to :ACQ command
        subsystem. Stops instrument when aquisition is complete. Acquires
        channels currently displayed (can change this with arguments to do more
        or less). """
        if not self.dummy:
            self.write(":DIG")

    # def read_all_waveforms(self, ch1, ch2, ch3, ch4):
    #
    #     wave = {}
    #
    #
    #     if not self.dummy:
    #         if ch1:
    #             wave["CH1"] = self.read_waveform(1)
    #         if ch2:
    #             wave["CH2"] = self.read_waveform(2)
    #         if ch3:
    #             wave["CH3"] = self.read_waveform(3)
    #         if ch4:
    #             wave["CH4"] = self.read_waveform(4)
    #
    #     return wave

    def single_trigger(self):
        """Tells oscilloscope to run with trigger mode set to single trigger"""
        if not self.dummy:
            self.write(":SING")

    def norm_trigger(self):
        """Tell oscilloscope to run with trigger mode set to normal"""
        if not self.dummy:
            self.write(":RUN")

    def auto_trigger(self):
        """Tells oscilloscope to run with trigger mode set to auto"""
        pass

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
    def read_waveform(self, channel: int):
        """Reads a waveform from the oscilloscope."""

        if self.dummy or not self.online:
            t = np.linspace(0, 1e-3, 100, False)
            noise = 0.02 * np.random.rand(1, 100)

            # in the line below we have to take index 0 of 'noise' because noise
            # is 2D array w/ 1 row and we need a 1D array
            v = np.sin(t * 5e3 * float(channel)) + noise[0]

            return f"CH{channel}_WVFM", t.tolist(), v.tolist()

        # Read data from oscilloscope
        try:
            self.write(f":WAV:SOUR CHAN{channel}")
            # Set the source channel
            raw_data = self.query(":WAV:DATA?")
            # Read waveform data
        except:
            self.digitize()
            self.configure_read_waveform()
            raw_data = self.query(":WAV:DATA?")
            # Read waveform data

        x_orig = self.query(":WAV:XOR?")
        # Read X Origin
        x_ref = self.query(":WAV:XREF?")
        # Read X Reference
        x_incr = self.query(":WAV:XINC?")
        # Read X Increment

        try:
            # x_orig = float(x_orig[0:len(x_orig)-1]); #Convert X Origin
            x_orig = float(x_orig[0 : len(x_orig)])
            # Convert X Origin
        except Exception as e:
            logger.error("Received bad origin from scope.", exc_info=True)
            return "", [], []
        try:
            # x_ref = float(x_ref[0:len(x_ref)-1]); #Convert X Reference
            x_ref = float(x_ref[0 : len(x_ref)])
            # Convert X Reference
        except Exception as e:
            logger.error("Received bad reference from scope.", exc_info=True)
            return "", [], []
        try:
            # x_incr = float(x_incr[0:len(x_incr)-1]); #Convert X Increment
            x_incr = float(x_incr[0 : len(x_incr)])
            # Convert X Increment
        except Exception as e:
            logger.error("Received bad increment from scope.", exc_info=True)
            return "", [], []

        try:
            # Format and convert data into float[]
            block_header = raw_data[0:10]
            raw_data = raw_data[
                11 : len(raw_data) - 1
            ]  # Trim block header from packet & remove newline character from end
            fmt = [float(x.strip()) for x in raw_data.split(",")]
            # Break at commas, strip whitespace, convert to float, add to array

            t = (
                (np.linspace(0, len(fmt), len(fmt), False) - x_ref) * x_incr + x_orig
            ).tolist()
            # Calculate time values
        except Exception as e:
            logger.error("Failed to calculate V & t.", exc_info=True)
            return "", [], []

        return f"CH{channel}_WVFM", t, fmt

    def configure_read_waveform(self):
        """Sets the data transfer mode of the oscilloscope. Call this function
        once before reading waveform data with 'read_waveform()'. """

        self.write(":WAV:FORM ASC")
        # Sets data format to ASCII text
        self.write(":WAV:POIN 1000")
        # Set the number of points to read to 1000 (OPtions: 1000, 500, 250, 100, MAX (~4M))
        self.write(":WAV:POIN:MODE NORM")
        # Set data record to transfer to 'measurement record'
        self.write(":ACQ:TYPE NORM")
        # Set aquisition mode to normal
