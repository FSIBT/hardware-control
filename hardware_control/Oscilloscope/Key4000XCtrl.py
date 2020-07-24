import logging

import numpy as np

from hardware_control.base.HC_Backend import HC_Backend, VISA, SOCKET
from hardware_control.utility import (
    get_channel_from_command,
    str_NR3,
    str_NR1,
    boolstr_NR1,
)


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

        self.check()

    def update_setting(self, setting: str, value):

        if not self.online:
            return "Offline"
        if self.dummy:
            return value

        if setting == "timebase":
            self.write(f":TIM:SCAL {str_NR3(value)}")
            return self.query(":TIM:SCAL?")
        if setting == "time_offset":
            self.write(f":TIM:POS {str_NR3(value)}")
            return self.query(":TIM:POS?")
        if setting == "labels_enabled":
            self.write(f"DISP:LAB {boolstr_NR1(value)}")
            return self.query("DISP:LAB?")
        if setting == "trigger_level":
            self.write(f"TRIG:EDGE:LEV {str_NR3(value)}")
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
            self.write(f"TRIG:SOUR CHAN{str_NR1(value)}")
            return self.query("TRIG:SOUR?")

        channel, setting_X = get_channel_from_command(setting)

        if setting_X == "CHX_volts_div":
            self.write(f":CHAN{channel}:SCAL {str_NR3(value)}")
            return self.query(f":CHAN{channel}:SCAL?")
        if setting_X == "CHX_offset":
            self.write(f"CHAN{channel}:OFFS {-float(value):.6E}")
            return self.query(f"CHAN{channel}:OFFS?")
        if setting_X == "CHX_BW_lim":
            self.write(f"CHAN{channel}:BWL {boolstr_NR1(value)}")
            return self.query(f"CHAN{channel}:BWL?")
        if setting_X == "CHX_active":
            self.write(f"CHAN{channel}:DISP {boolstr_NR1(value)}")
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
        if setting_X == "CHX_invert":
            self.write(f"CHAN{channel}:INV {boolstr_NR1(value)}")
            return self.query(f"CHAN{channel}:INV?")
        if setting_X == "CHX_probe_atten":
            self.write(f"CHAN{channel}:PROB {str_NR3(value)}")
            return self.query(f"CHAN{channel}:PROB?")  # ie. 10 gives x10 or 10:1 probe
        if setting_X == "CHX_coupling":
            # Make sure valid value provided
            if value not in ["AC", "DC"]:
                value = "DC"
            self.write(f"CHAN{channel}:COUP {value}")
            return self.query(f"CHAN{channel}:COUP?")

    def check_connection(self):
        """
        Verifies that the backend is able to communicate with the instrument by
        querying the instruments name and checking for a valid return value.

        Returns true if online, false if offline, and None if unknown connection
        type.
        """

        if not self.online:
            return False

        if self.connection_type in [SOCKET, VISA]:

            try:
                self.device.query("*IDN?")
                self.online = True
            except Exception:  # Not connected - reconnect
                logger.warning(
                    "Device connection check failed. Setting online to false.",
                    exc_info=True,
                )
                self.online = False
            return self.online
        else:

            return None

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

        channel, cmd_X = get_channel_from_command(cmd)

        if cmd_X == "CHX+_WVFM?":
            # Returns a tuple (str, list, list)
            return self.read_waveform(channel)
        if cmd_X == "CHX+_CLEAR":
            return f"CH{channel}_WVFM", [], []
        else:
            return "", [], []

    def digitize(self):
        """Similar to single trigger.

        Aquires waveform according to :ACQ command subsystem. Stops
        instrument when aquisition is complete. Acquires channels
        currently displayed (can change this with arguments to do more
        or less).

        """
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

    def read_waveform(self, channel: int):
        """Reads a waveform from the oscilloscope.

        Returns
        -------
        CHX_WVFM : str
            Information about the channel number
        t : list
            List of the time stamps
        values : list
            List of the function values in Volts

        """

        if self.dummy or not self.online:
            t = np.linspace(0, 1e-3, 100, False)
            noise = 0.02 * np.random.rand(1, 100)

            # in the line below we have to take index 0 of 'noise' because noise
            # is 2D array w/ 1 row and we need a 1D array
            v = np.sin(t * 5e3 * float(channel)) + noise[0]

            return f"CH{channel}_WVFM", t.tolist(), v.tolist()

        # Check if we have data and read it from oscilloscope
        try:
            data_length = int(self.query(":WAV:POINTS?"))
            if data_length == 0:
                return "", [], []
        except ValueError:
            return "", [], []

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

        # Read X Origin
        x_orig = self.query(":WAV:XOR?")
        # Read X Reference
        x_ref = self.query(":WAV:XREF?")
        # Read X Increment
        x_incr = self.query(":WAV:XINC?")

        try:
            # Convert X Origin
            x_orig = float(x_orig)
        except ValueError:
            logger.error("Received bad origin from scope.", exc_info=True)
            return "", [], []
        try:
            # Convert X Reference
            x_ref = float(x_ref)
        except ValueError:
            logger.error("Received bad reference from scope.", exc_info=True)
            return "", [], []
        try:
            # Convert X Increment
            x_incr = float(x_incr)
        except ValueError:
            logger.error("Received bad increment from scope.", exc_info=True)
            return "", [], []

        try:
            # Trim block header from packet & remove newline character from end
            raw_data = raw_data[11:-1]
            # Break at commas, strip whitespace, convert to float, add to array
            fmt = [float(x.strip()) for x in raw_data.split(",")]

            # Calculate time values
            t = np.linspace(start=0, stop=len(fmt), num=len(fmt), endpoint=False)
            t = (t - x_ref) * x_incr + x_orig
            t = t.tolist()
        except Exception:
            logger.error("Failed to calculate V & t.", exc_info=True)
            return "", [], []

        return f"CH{channel}_WVFM", t, fmt

    def configure_read_waveform(self):
        """Sets the data transfer mode of the oscilloscope.

        Call this function once before reading waveform data with
        'read_waveform()'.

        """

        # Sets data format to ASCII text
        self.write(":WAV:FORM ASC")
        # Set the number of points to read to 1000 (OPtions: 1000,
        # 500, 250, 100, MAX (~4M))
        self.write(":WAV:POIN 1000")
        # Set data record to transfer to 'measurement record'
        self.write(":WAV:POIN:MODE NORM")
        # Set aquisition mode to normal
        self.write(":ACQ:TYPE NORM")
