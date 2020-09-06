"""Picoscpe 6000 series.

.. image:: /images/Pico_6000.jpg
  :height: 200

See class definition for details.

"""

import logging
import numpy as np

from picoscope.ps6000 import PS6000

from ..base import Backend, ensure_online
from ..utility import (
    regex_compare,
    ensure_float,
    get_channel_from_command,
)

logger = logging.getLogger(__name__)


class Picotech_6000(Backend):
    """A driver for the Picotech Picoscpe 6000 series

    Instrument home page: https://www.picotech.com/oscilloscope/picoscope-6000-series
    """

    def __init__(
        self, connection_addr,
    ):
        super().__init__(instrument_name="Pico-6000", connection_addr=connection_addr)

        self.num_vert_divisions = 8
        self.record_length = 1e6  # Maximum 64 MS
        self.trigger_channel = 0
        self.offset_position = 0
        self.timebase = 10e-3  # time/div * number of divisions

        self.measurements = ["", "", "", "", ""]

    def try_connect(self):
        """Checks if the backend is in communication with the object, if it is
        not, it tries to re-establish communication."""

        if self.dummy:
            if self.online:
                return True

            logger.debug(
                f"{self.ID}: creating dummy connection to {self.connection_addr}"
            )
            self.online = True
            return True

        if self.online:
            return True

        logger.debug(f"{self.ID}: trying to connect")

        try:
            self.ps = PS6000()
            self.online = True
        except Exception:
            self.online = False
            logger.debug(
                f"\t({self.ID}) ERROR connecting with picoscope.", exc_info=True
            )
            logger.debug(f"{self.ID} is offline")
        else:
            self.online = True

        # If connection purportedly successful, verify connection
        if self.online:
            if not self.check_connection():
                self.online = False

        return self.online

    def check_connection(self):
        """TODO: could use ps.ping() to test"""
        if not self.online:
            return False

        return True

    @ensure_online
    def update_setting(self, setting: str, value):
        value_orig = value
        value = ensure_float(value)

        if self.dummy:
            return value

        try:
            # first check for commands that are not channel specific
            if setting == "LABELS_ENABLED":
                return "Not available"

            if setting == "TIMEBASE":
                self.timebase = value * 10  # Time/div * #div

                obs_duration = value
                sampling_interval = obs_duration / self.record_length

                if sampling_interval < 1e-9:
                    sampling_interval = 1e-9
                    obs_duration = sampling_interval * int(
                        obs_duration / sampling_interval
                    )

                rval, _, _ = self.ps.setSamplingInterval(
                    sampling_interval, obs_duration
                )
                # could not get normal readout mode to work, so using memory Segments and bulk readout
                self.ps.memorySegments(1)
                self.ps.setNoOfCaptures(1)
                return f"{setting}={rval}"
            if setting == "TIME_OFFSET":
                self.offset_position = value
                return f"{setting}={value}"
            if setting == "TRIGGER_LEVEL":
                if self.trigger_channel != "None":
                    self.ps.setSimpleTrigger(
                        self.trigger_channel, threshold_V=value, enabled=True
                    )
                return f"{setting}={value}"
            if setting == "TRIGGER_COUPLING":
                return "Not available"
            if setting == "TRIGGER_EDGE":
                # Make sure valid option given
                if value not in ["BOTH", "NEG", "POS", "ALT"]:
                    value = "Rising"
                elif value == "POS":
                    value = "Rising"
                elif value == "NEG":
                    value = "Falling"
                elif value == "BOTH":
                    # This model does not support BOTH mode
                    value = "Rising"
                elif value == "ALT":
                    # This model does not support alternating trigger
                    value = "Rising"
                if self.trigger_channel != "None":
                    self.ps.setSimpleTrigger(
                        self.trigger_channel, direction=value, enabled=True
                    )
                return f"{setting}={value}"
            if setting == "TRIGGER_CHANNEL":
                if value_orig == "None":
                    self.trigger_channel = value_orig
                else:
                    self.trigger_channel = int(value_orig) - 1
                if self.trigger_channel == "None":
                    self.ps.setSimpleTrigger(0, enabled=False)
                else:
                    self.ps.setSimpleTrigger(self.trigger_channel, enabled=True)
                return f"{setting}={value}"
            if regex_compare("meas_slot.", setting):
                return "Not available"
            if setting == "use_meas_avg":
                return "Not available"
            if setting == "meas_stat_enabled":
                return "Not available"

            # verify channel and check for all channel related commands
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

            if setting_X == "CHX_VOLTS_DIV":
                self.ps.setChannel(channel=chan, VRange=value)
                return f"{setting}={value}"
            if setting_X == "CHX_OFFSET":
                self.ps.setChannel(channel=chan, VOffset=value)
                return f"{setting}={value}"
            if setting_X == "CHX_BW_LIM":
                self.ps.setChannel(channel=chan, BWLimited=value)
                return f"{setting}={value}"
            if setting_X == "CHX_ACTIVE":
                self.ps.setChannel(channel=chan, enabled=value)
                return f"CH{channel}={value}"
            if setting_X == "CHX_IMPEDANCE":
                return "Not available"
            if setting_X == "CHX_LABEL":
                return "Not available"
            if setting_X == "CHX_INVERT":
                return "Not availanle"
            if setting_X == "CHX_PROBE_ATTEN":
                self.ps.setChannel(channel=chan, probeAttenuation=value)
                return f"{setting}={value}"
            if setting_X == "CHX_COUPLING":
                # Make sure valid value provided
                if value not in ["AC", "DC"]:
                    value = "DC"
                self.ps.setChannel(channel=chan, coupling=value)
                return f"{setting}={value}"

        except Exception:
            logger.error(
                "An error occured in Picoscope6000.", exc_info=True,
            )

    @ensure_online
    def command(self, cmd: str):

        ret_str = ""

        add_asterisk = False
        if cmd[-1] == "*":
            add_asterisk = True
            cmd = cmd[0:-1]

        if cmd == "SINGLE_TRIGGER":
            self.ps.runBlock(pretrig=self.offset_position / self.timebase)
            self.ps.waitReady()
        elif cmd == "RUN":
            self.ps.runBlock(pretrig=self.offset_position / self.timebase)
            self.ps.waitReady()
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

        channel, cmd_X = get_channel_from_command(cmd)

        if not self.online:
            return "", [], []

        if cmd_X == "CHX_WVFM?":
            return self.read_waveform(channel)

        if cmd_X == "CHX_CLEAR":
            return f"CH{channel}_WVFM", [], []

        return "", [], []

    def read_waveform(self, channel: str):
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

        channel_orig = channel
        channel = int(channel) - 1

        if self.dummy or not self.online:
            t = np.linspace(0, 1e-3, 100, False)
            noise = 0.02 * np.random.rand(1, 100)

            # in the line below we have to take index 0 of 'noise' because noise
            # is 2D array w/ 1 row and we need a 1D array
            v = np.sin(t * 5e3 * float(channel)) + noise[0]

            return f"CH{channel_orig}_WVFM", t.tolist(), v.tolist()

        try:
            number_samples = min(self.ps.noSamples, self.ps.maxSamples)

            # seems data and dataR are needed
            data = np.zeros(number_samples, dtype=np.float64)
            dataR = np.zeros(number_samples, dtype=np.int16)
            data = self.ps.getDataV(channel, dataV=data, dataRaw=dataR)
            volts = list(data)

            # Get time values
            t = np.linspace(0, self.ps.sampleInterval * self.noSamples, len(volts))
            t = t - t[-1] * self.offset_position / self.timebase
            t = list(t)
        except OSError as e:
            if "PICO_NO_SAMPLES_AVAILABLE" in e.args[0]:
                logger.error(
                    "ERROR: Failed to read waveform data from scope: no data available"
                )
            else:
                logger.error(
                    "ERROR: Failed to read waveform data from scope", exc_info=True
                )
            return "", [], []
        except AttributeError as e:
            if "maxSamples" in e.args[0]:
                logger.error(
                    "ERROR: Failed to read waveform data from scope: time base not set"
                )
            elif "noSamples" in e.args[0]:
                logger.error(
                    "ERROR: Failed to read waveform data from scope: time base not set"
                )
            else:
                logger.error(
                    "ERROR: Failed to read waveform data from scope", exc_info=True
                )
            return "", [], []

        return f"CH{channel_orig}_WVFM", t, volts
