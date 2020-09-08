"""InfiniiVision 4000 X-Series Oscilloscope.

.. image:: /images/Keysight4000X.jpeg
  :height: 200

See class definition for details.

"""

import logging

import numpy as np

from ..base import Backend
from ..utility import get_channel_from_command


logger = logging.getLogger(__name__)


class Keysight_4000X(Backend):
    """ A backend to control the Keysight 4000X Series oscilloscopes
    """

    # sigReturnWaves = pyqtSignal(int, list, list)

    def __init__(
        self, connection_addr: str,
    ):
        super().__init__(
            instrument_name="KEYSIGHT-4000X",
            connection_addr=connection_addr,
            default_port=5025,
        )
        self.num_vert_divisions = 8
        self.check_connection_commands = "*IDN?"

    def update_setting(self, setting: str, value):
        """ Changes a specified setting to the specied value

        Parameters
        ----------
        setting : str
            Setting to change

        Notes
        --------
        Available settings (<X> indicates a number, values in parethesis show acceptable values):

        * timebase: horizontal resolution in time per division (float)
        * time_offset: time offset from trigger (float)
        * NUM_POINTS: number of points on the time axis
        * labels_enabled: enables or disables channel labels on the instrument (bool)
        * trigger_level: Set trigger level (float)
        * trigger_coupling: Set the trigger coupling (AC, DC, LFReject)
        * trigger_edge: Set which edge of waveform oscilloscope triggers on (BOTH, NEG, POS, ALT)
        * trigger_channel: Which channel to trigger on (1,2,3,4)
        * CH<X>_volts_div: Sets the voltage per division for channel 'X' (float)
        * CH<X>_offset: Sets the voltage offset for channel 'X' (float)
        * CH<X>_BW_lim: Enables or disables the 20MHz bandwidth limit for channel 'X' (bool)
        * CH<X>_active: Enables or disables channel 'X' (bool)
        * CH<X>_impedance: Sets the imedance for the channnel (50, 1e6)
        * CH<X>_label: Label for the channel (str)
        * CH<X>_invert: Enables or disables inverting for channel 'X' (bool)
        * CH<X>_probe_atten: Sets the probe attenuation for channel 'X'. For example, providing the value '10' would indicate a 10x or 10:1 probe. (float)
        * CH<X>_coupling: Sets the coupling mode for the speicied channel (AC, DC)
        """

        if self.dummy:
            return value

        if setting == "TIMEBASE":
            self.write(f":TIM:SCAL {float(value):.6E}")
            rval = self.query(":TIM:SCAL?")
            return f"{setting}={rval}"
        if setting == "TIME_OFFSET":
            self.write(f":TIM:POS {float(value):.6E}")
            rval = self.query(":TIM:POS?")
            return f"{setting}={rval}"
        if setting == "NUM_POINTS":
            self.write(f":WAV:POIN {int(float(value)):}")
            rval = self.query(":WAV:POIN?")
            return f"{setting}={rval}"
        if setting == "LABELS_ENABLED":
            self.write(f"DISP:LAB {int(value=='True')}")
            rval = self.query("DISP:LAB?")
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

        channel, setting_X = get_channel_from_command(setting)

        if setting_X == "CHX_VOLTS_DIV":
            self.write(f":CHAN{channel}:SCAL {float(value):.6E}")
            rval = self.query(f":CHAN{channel}:SCAL?")
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
            ret = self.query(f"CHAN{channel}:DISP?")
            if ret in ["0", "1"]:
                rval = str(bool(int(ret)))
                return f"{setting}={rval}"
            else:
                return ret
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

    def command(self, cmd: str):
        """ Executes an action specified by 'cmd'.

        Parameters
        ----------
        cmd
            Name of command to execute

        Notes
        -----
        Available commands:

        * SINGLE_TRIGGER: Set the instrument to trigger once and retain the data
        * RUN: Set the instrument to continuously trigger
        * CONFIG_READ_WAVE: Configure oscilloscope settings to prepare for reading waveforms
        * STOP: Prevent the instrument from triggering
        """

        if cmd == "SINGLE_TRIGGER":
            self.write(":SING")
        elif cmd == "RUN":
            self.write(":RUN")
        elif cmd == "CONFIG_READ_WAVE":
            self.configure_read_waveform()
        elif cmd == "STOP":
            self.write(":STOP")

    def command_listdata(self, cmd: str):
        """ Executes an action specified by 'cmd', returns a tuple with a string and two lists

        Parameters
        ----------
        cmd
            Name of command to execute

        Notes
        -----
        Available commands (<X> indicates a number):

        * CH<X>_WVFM?: Reads the waveform for channel 'X'
        * CH<X>_CLEAR: Clears the waveform for channel 'X' and returns two empty lists
        * RUN: Set the instrument to continuously trigger
        * CONFIG_READ_WAVE: Configure oscilloscope settings to prepare for reading waveforms
        * STOP: Prevent the instrument from triggering
        """

        if not self.online:
            return "", [], []

        channel, cmd_X = get_channel_from_command(cmd)

        if cmd_X == "CHX_WVFM?":
            # Returns a tuple (str, list, list)
            return self.read_waveform(channel)
        if cmd_X == "CHX_CLEAR":
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

    def read_waveform(self, channel: int):
        """Reads a waveform from the oscilloscope.

        Parameters
        ----------
        channel : int
            Channel number to read

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
            fmt = [float(x.strip()) for x in raw_data.split(",")][:-1]

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
        # Set data record to transfer to 'measurement record'
        self.write(":WAV:POIN:MODE NORM")
        # Set aquisition mode to normal
        self.write(":ACQ:TYPE NORM")
