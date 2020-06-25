from hardware_control.HC_Backend import HC_Backend, VISA, get_channel_from_command
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
import picoscope
from picoscope.ps6000 import PS6000
from hardware_control.utility import regex_compare, ensure_float

logger = logging.getLogger(__name__)


class Pico5000ACtrl(HC_Backend):
    def __init__(
        self, connection_addr,
    ):
        super().__init__()
        self.ID = "Pico-5000A"

        self.connection_addr = connection_addr

        self.online = False
        self.dummy = False
        self.num_vert_divisions = 8

        self.record_length = 1e6  # Maximum 64 MS
        self.trigger_channel = "A"
        self.offset_position = 0
        self.timebase = 10e-3  # time/div * number of divisions

        self.measurements = ["", "", "", "", ""]
        self.check()

    def try_connect(self):
        """Checks if the backend is in communication with the object, if it is
        not, it tries to re-establish communication."""

        if self.dummy:
            if self.online:
                return True
            else:
                logger.debug(
                    f"{self.ID}: creating dummy connection"
                    + f" to {self.connection_addr}"
                )
                self.online = True
                return True

        if self.online:
            return True  # Todo: Add check_connection() here?

        logger.debug(f"{self.ID}: trying to connect")

        try:
            self.ps = PS6000()
            self.online=True
        except Exception as e:
            self.online = False
            logger.debug(f"\t({self.ID}) ERROR connecting with visa.", exc_info=True)
            logger.debug(f"{self.ID} is offline")
        else:
            self.online = True

        # If connection purportedly successful, verify connection
        if self.online == True:
            if self.check_connection() == False:
                self.online = False

        return self.online

    def check_connection(self):
        return True
        try:
            self.ps.ping()
        except:
            return False

        return True

    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)
        if channel == 1:
            chan = "A"
        elif channel == 2:
            chan = "B"
        elif channel == 3:
            chan = "C"
        elif channel == 4:
            chan = "D"
        else:
            return "Bad channel number"

        value = ensure_float(value)

        if not self.online:
            return "Offline"

        try:
            if self.dummy:
                return value
            else:
                if setting_X == "CHX_volts_div":

                    self.ps.setChannel(channel=chan, VRange=value)

                    return "Success"

                elif setting == "timebase":

                    self.timebase = value * 10  # Time/div * #div

                    obs_duration = value
                    sampling_interval = obs_duration / self.record_length

                    if sampling_interval < 1e-9:
                        sampling_interval = 1e-9
                        obs_duration = sampling_interval * int(
                            obs_duration / sampling_interval
                        )

                    rval = self.ps.setSamplingInterval(sampling_interval, obs_duration)

                    return rval

                elif setting == "time_offset":

                    self.offset_position = value

                elif setting_X == "CHX_offset":

                    self.ps.setChannel(channel=chan, VOffset=value)

                    return "Success"

                elif setting_X == "CHX_BW_lim":

                    self.ps.setChannel(channel=chan, BWLimited=value)

                    return "Success"

                elif setting_X == "CHX_active":

                    self.ps.setChannel(channel=chan, enabled=value)

                    return "Success"

                elif setting_X == "CHX_impedance":

                    return "Not available"

                elif setting_X == "CHX_label":  # TODO

                    # Length is capped at 32 characters
                    return "Not available"

                elif setting == "labels_enabled":  # TODO

                    return "Not available"

                elif setting_X == "CHX_invert":

                    return "Not availanle"

                elif setting_X == "CHX_probe_atten":

                    self.ps.setChannel(channel=chan, probeAttenuation=value)

                    return "Success"

                elif setting_X == "CHX_coupling":

                    # Make sure valid value provided
                    if value != "AC" and value != "DC":
                        value = "DC"

                    self.ps.setChannel(channel=chan, coupling=value)

                    return "Success"

                elif setting == "trigger_level":

                    self.ps.setSimpleTrigger(self.trigger_channel, threshold_V=value)

                    return "Success"

                elif setting == "trigger_coupling":

                    return "Not available"

                elif setting == "trigger_edge":

                    # Make sure valid option given
                    if (
                        value != "BOTH"
                        and value != "NEG"
                        and value != "POS"
                        and value != "ALT"
                    ):
                        value = "Rising"

                    if value == "POS":
                        value = "Rising"
                    else:
                        value = "Falling"

                    # This model does not support BOTH mode
                    if value == "BOTH":
                        value = "Rising"

                    # This model does not support alternating trigger
                    if value == "ALT":
                        value = "Rising"

                    self.ps.setSimpleTrigger(self.trigger_channel, direction=value)

                    return "Success"

                elif setting == "trigger_channel":

                    self.trigger_channel = value

                    self.ps.setSimpleTrigger(value)

                    return "Success"

                elif regex_compare("meas_slot.", setting):

                    return "Not available"

                elif setting == "use_meas_avg":

                    return "Not available"

                elif setting == "meas_stat_enabled":

                    return "Not available"

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
            self.ps.runBlock(pretrig=self.offset_position / self.timebase)
        elif cmd == "RUN":
            self.ps.runBlock(pretrig=self.offset_position / self.timebase)
        elif cmd == "STOP":
            self.ps.stop()
        elif cmd == "CLEAR_MEAS":
            return "Not available"
        elif regex_compare("meas_slot.", cmd):

            return "Not available"

        elif cmd == "RESET_MEAS_STAT":

            return "Not available"

        return ret_str

    def command_listdata(self, cmd: str):

        channel, setting_X = get_channel_from_command(cmd)

        if channel == 1:
            chan = "A"
        elif channel == 2:
            chan = "B"
        elif channel == 3:
            chan = "C"
        elif channel == 4:
            chan = "D"

        if not self.online:
            return "", [], []

        if regex_compare("CH.+_WVFM?", cmd):

            return self.read_waveform(channel)  # Returns a tuple (str, list, list)

        if regex_compare("CH.+_CLEAR", cmd):
            return f"CH{chan}_WVFM", [], []
        else:
            return "", [], []

    #
    #
    # Returns (V, t) as float[]
    def read_waveform(self, channel: str):
        """Reads a waveform from the oscilloscope."""

        if channel == "A":
            chan = 1
        elif channel == "B":
            chan = 2
        elif channel == "C":
            chan = 3
        elif channel == "D":
            chan = 4
        else:
            chan = 1

        if self.dummy or not self.online:
            t = np.linspace(0, 1e-3, 100, False)
            noise = 0.02 * np.random.rand(1, 100)

            # in the line below we have to take index 0 of 'noise' because noise
            # is 2D array w/ 1 row and we need a 1D array
            v = np.sin(t * 5e3 * float(channel)) + noise[0]

            return f"CH{chan}_WVFM", t.tolist(), v.tolist()

        try:

            volts = list(self.ps.getDataV(channel))

            # Get time values
            t = list(
                np.linspace(0, self.ps.noSamples / self.ps.sampleInterval, len(volts))
            )

        except:
            logger.error(
                "ERROR: Failed to read waveform data from scope", exc_info=True
            )
            return "", [], []

        return f"CH{chan}_WVFM", t, volts
