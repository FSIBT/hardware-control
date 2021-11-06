"""
.. image:: /images/Pico_6000.jpg
  :height: 200

"""

import json
import logging
import numpy as np

from picoscope.ps6000 import PS6000

from ...base import Instrument

logger = logging.getLogger(__name__)


class Picotech_6000(Instrument):
    """Picotech Picoscpe 6000 series instrument class.

    PARAMETERS
        * TIMEBASE (*float*)
            * Horizontal resolution in time per division.
        * TIME_OFFSET (*float*)
            * Time offset from trigger.
        * TRIGGER_LEVEL (*float*)
            * Trigger level.
        * TRIGGER_EDGE (*BOTH*, *NEG*, *POS*, *ALT*)
            * Edge of waveform that the picoscope triggers on.
        * TRIGGER_CHANNEL (*int*)
            * The channel (1,2,3, or 4) to trigger on.
        * CH<X>_VOLTS_DIV (*float*)
            * The voltage per division for channel 'X'.
        * CH<X>_OFFSET (*float*)
            * The voltage offset for channel 'X'.
        * CH<X>_BW_LIM
            * Status of the bandwidth limit for channel 'X'.
        * CH<X>_ACTIVE
            * On/off status of channel 'X'.
        * CH<X>_PROBE_ATTEN (*float*)
            * Probe attenuation for channel 'X'. For example, providing the value '10' would indicate a 10x or 10:1 probe.
        * CH<X>_COUPLING (*AC*, *DC*)
            * Coupling mode for channel 'X'.
        * CH<X>_WVFM
            * Most recent waveform measurement from channel 'X'.

    COMMANDS
        * SINGLE_TRIGGER
            * Set the instrument to trigger once.
        * RUN
            * Set the instrument to continuously trigger.
        * STOP
            * Prevent the instrument from triggering.

    """

    def __init__(
        self,
        instrument_name: str = "PICOTECH_6000",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        self.number_of_channels = 4
        self.num_vert_divisions = 8
        self.record_length = 1e6  # Maximum 64 MS
        self.trigger_channel = 0
        self.offset_position = 0
        self.timebase = 10e-3  # time/div * number of divisions

        self.measurements = ["", "", "", "", ""]

        self.add_parameter(
            "TIMEBASE",
            read_command=self._get_timebase,
            set_command=self._set_timebase,
        )
        self.add_parameter(
            "TIME_OFFSET",
            read_command=self._get_timeoffset,
            set_command=self._set_timeoffset,
        )
        self.add_parameter(
            "TRIGGER_LEVEL",
            read_command=None,
            set_command=self._set_triggerlevel,
        )
        self.add_parameter(
            "TRIGGER_EDGE",
            read_command=None,
            set_command=self._set_triggeredge,
        )
        self.add_lookup(
            "TRIGGER_EDGE",
            {"BOTH": "Rising", "NEG": "Falling", "POS": "Rising", "ALT": "Rising"},
        )
        self.add_parameter(
            "TRIGGER_CHANNEL", read_command=None, set_command=self._set_triggerchannel
        )

        channels = {0: "A", 1: "B", 2: "C", 3: "D"}
        for i in range(self.number_of_channels):
            ch = channels[i]
            self.add_parameter(
                f"CH{ch}_VOLTS_DIV",
                read_command=None,
                set_commmand=lambda x: self.ps.setChannel(channel=ch, VRange=x),
            )
            self.add_parameter(
                f"CH{ch}_OFFSET",
                read_command=None,
                set_commmand=lambda x: self.ps.setChannel(channel=ch, VOffset=x),
            )
            self.add_parameter(
                f"CH{ch}_BW_LIM",
                read_command=None,
                set_commmand=lambda x: self.ps.setChannel(channel=ch, BWLimited=x),
            )
            self.add_parameter(
                f"CH{ch}_ACTIVE",
                read_command=None,
                set_commmand=lambda x: self.ps.setChannel(channel=ch, enabled=x),
            )
            self.add_parameter(
                f"CH{ch}_PROBE_ATTEN",
                read_command=None,
                set_commmand=lambda x: self.ps.setChannel(
                    channel=ch, probeAttenuation=x
                ),
            )
            self.add_parameter(
                f"CH{ch}_COUPLING",
                read_command=None,
                set_commmand=lambda x: self.ps.setChannel(channel=ch, coupling=x),
            )

            self.add_parameter(
                f"CH{ch}_WVFM",
                read_command=lambda: self._read_waveform(i),
                set_command=None,
            )

        self.add_command("SINGLE_TRIGGER", self._trigger)
        self.add_command("RUN", self._run)
        self.add_command("STOP", self.ps.stop)

    def _get_timebase(self):
        return str(self.timebase)

    def _set_timebase(self, value):
        self.timebase = value * 10
        obs_duration = self.timebase
        sampling_interval = obs_duration / self.record_length

        if sampling_interval < 1e-9:
            sampling_interval = 1e-9
            obs_duration = sampling_interval * int(obs_duration / sampling_interval)

        # could not get normal readout mode to work, so using memory Segments and bulk readout
        self.ps.memorySegments(1)
        self.ps.setNoOfCaptures(1)

    def _get_timeoffset(self):
        return str(self.offset_position)

    def _set_timeoffset(self, value):
        self.offset_position = value

    def _set_triggerlevel(self, value):
        if self.trigger_channel != "None":
            self.ps.setSimpleTrigger(
                self.trigger_channel, threshold_V=value, enabled=True
            )

    def _set_triggeredge(self, value):
        if self.trigger_channel != "None":
            self.ps.setSimpleTrigger(
                self.trigger_channel, direction=value, enabled=True
            )

    def _set_triggerchannel(self, value):
        if value == "None":
            self.trigger_channel = 0
        else:
            self.trigger_channel = int(value) - 1
        self.ps.setSimpleTrigger(self.trigger_channel, enabled=True)

    def _trigger(self):
        self.ps.runBlock(pretrig=self.offset_position / self.timebase)
        self.ps.waitReady()

    def _run(self):
        self.ps.runBlock(pretrig=self.offset_position / self.timebase)
        self.ps.waitReady()

    def try_connect(self):
        """Unique picoscope ‘try_connect’ function."""

        if self._dummy:
            if self._online:
                return True

            logger.debug(
                f"{self.ID}: creating dummy connection to {self.connection_addr}"
            )
            self._online = True
            return True

        if self._online:
            return True

        logger.debug(f"{self.ID}: trying to connect")

        try:
            self.ps = PS6000()
            self._online = True
        except Exception:
            self._online = False
            logger.debug(
                f"\t({self.ID}) ERROR connecting with picoscope.", exc_info=True
            )
            logger.debug(f"{self.ID} is offline")
        else:
            self._online = True

        # If connection purportedly successful, verify connection
        if self._online:
            if not self._check_connection():
                self._online = False

        return self._online

    def _check_connection(self):
        """TODO: could use ps.ping() to test"""
        if not self._online:
            return False

        return True

    def _read_waveform(self, channel: str):
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
            return "[[],[]]"
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
            return "[[],[]]"

        return json.dumps([t, volts])
