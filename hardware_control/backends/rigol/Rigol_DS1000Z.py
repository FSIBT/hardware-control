"""RIGOL’s 1000Z Series Digital Oscilloscope

.. image:: /images/RigolDS100Z.png
  :height: 200

See class definition for details.

"""

import logging

import numpy as np

from ..base import Backend, ensure_online
from ..utility import get_channel_from_command, returnChannelNumber, regex_compare

logger = logging.getLogger(__name__)


class Rigol_DS1000Z(Backend):
    def __init__(
        self, connection_addr,
    ):
        super().__init__(
            instrument_name="RIGOL-DS1000Z", connection_addr=connection_addr
        )

        self.num_vert_divisions = 8
        self.use_avg = False
        self.measurements = ["", "", "", "", ""]

    @ensure_online
    def update_setting(self, setting: str, value):

        if self.dummy:
            return value

        if setting == "TIMEBASE":
            self.write(f":TIM:MAIN:SCAL {float(value):.6E}")
            rval = self.query(":TIM:MAIN:SCAL?")
            return f"{setting}={rval}"

        if setting == "TIME_OFFSET":
            self.write(f":TIM:MAIN:OFFS {float(value):.6E}")
            rval = self.query(":TIM:MAIN:OFFS?")
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
            if value not in ["AC", "DC", "LFReject", "HFReject"]:
                value = "DC"

            self.write(f"TRIG:COUP {value}")
            rval = self.query("TRIG:COUP?")
            return f"{setting}={rval}"

        if setting == "TRIGGER_EDGE":
            # Make sure valid option given
            if value not in ["BOTH", "NEG", "POS", "ALT"]:
                value = "POS"

            # This model does not support BOTH mode
            if value == "BOTH":
                value = "POS"

            # This model calls altermating mode 'RFALI'
            if value == "ALT":
                value = "RFALI"

            self.write(f"TRIG:EDGE:SLOP {value}")
            rval = self.query("TRIG:EDGE:SLOP?")
            return f"{setting}={rval}"

        if setting == "TRIGGER_CHANNEL":
            self.write(f"TRIG:EDG:SOUR CHAN{int(value)}")
            rval = self.query("TRIG:EDG:SOUR?")
            return f"{setting}={rval}"

        if setting == "USE_MEAS_AVG":
            self.use_avg = value == "True"
            return f"{setting}={value}"

        if setting == "MEAS_STAT_ENABLED":
            self.write(f":MEAS:STAT:DISP {int(value=='True')}")
            rval = self.query(":MEAS:STAT:DISP?")
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
            if value == "True":
                self.write(f"CHAN{channel}:BWL 20M")
            else:
                self.write(f"CHAN{channel}:BWL OFF")
            rval = self.query(f"CHAN{channel}:BWL?")
            return f"{setting}={rval}"

        if setting_X == "CHX_ACTIVE":
            self.write(f"CHAN{channel}:DISP {int(value=='True')}")
            rval = self.query(f"CHAN{channel}:DISP?")
            return f"{setting}={rval}"

        if setting_X == "CHX_IMPEDANCE":
            # This feature is not available on this model
            pass

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

        # Value must follow pattern 'meas_parameter','source_channel'
        if regex_compare("MEAS_SLOT.", setting):

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

    @ensure_online
    def command(self, cmd: str):

        add_asterisk = False
        if cmd[-1] == "*":
            add_asterisk = True
            cmd = cmd[0:-1]

        if cmd == "SINGLE_TRIGGER":
            self.write(":SING")
            return "SINGLE_TRIGGER"
        elif cmd == "RUN":
            self.write(":RUN")
            return "RUN"
        elif cmd == "STOP":
            self.write(":STOP")
            return "STOP"
        elif cmd == "CLEAR_MEAS":
            self.write("MEAS:CLEAR ALL")
            return "CLEAR_MEAS"
        elif regex_compare("MEAS_SLOT.", cmd):
            logger.debug(f"Reading slot w/ '{cmd}'")

            # Get slot number
            slot = int(cmd[9])
            ret_str = ""
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
            return ret_str
        elif cmd == "RESET_MEAS_STAT":
            self.write(":MEAS:STAT:DISP OFF")
            self.write(":MEAS:STAT:DISP ON")
            return cmd

    def command_listdata(self, cmd: str):
        if not self.online:
            return "", [], []

        channel, cmd_X = get_channel_from_command(cmd)

        if cmd_X == "CHX_WVFM?":
            return self.read_waveform(channel)
        if cmd_X == "CHX_CLEAR":
            return f"CH{channel}_WVFM", [], []
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

    def read_waveform(self, channel: int):  # TODO
        """Reads a waveform from the oscilloscope.

        Returns
        -------
           (V, t) as float[]
        """

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
            t = list(xorigin + np.linspace(0, xincr * (len(volts) - 1), len(volts)))

        except:
            logger.error(
                "ERROR: Failed to read waveform data from scope", exc_info=True
            )
            return "", [], []

        return f"CH{channel}_WVFM", t, volts
