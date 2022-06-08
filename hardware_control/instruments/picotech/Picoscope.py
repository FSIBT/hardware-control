"""
.. image:: /images/Pico_6000.jpg
  :height: 200

"""

from functools import partial
import json
import logging
import numpy as np
from typing import List

from ...base import Instrument

logger = logging.getLogger(__name__)

from ...base.hooks import format_float

from picoscope.ps2000a import PS2000a
from picoscope.ps5000a import PS5000a
from picoscope.ps6000 import PS6000


def pico_error_check(func):
    """Decorator to log all errors thrown by Picoscope python package."""

    def inner(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Picoscope {e.__class__.__name__} while calling {func.__name__}: {e}"
            )

    return inner


class Picoscope(Instrument):
    """Picotech Picoscpe 2000a and 5000a series instrument class.

    Notes
    -----
    1. The picoscope.ps5000a python library is meant for both 5000a and 5000b
    series instruments.
    2. Picoscope channels are numbered such that the first channel is 0.

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
        * CH<X>_ACTIVE
            * On/off status of channel 'X'.
        * CH<X>_PROBE_ATTEN (*float*)
            * Probe attenuation for channel 'X'. For example, providing the value '10' would indicate a 10x or 10:1 probe.
        * CH<X>_COUPLING (*AC*, *DC*)
            * Coupling mode for channel 'X'.
        * CH<X>_WAVEFORM
            * Most recent waveform measurement from channel 'X'.

    COMMANDS
        * SINGLE_TRIGGER
            * Set the instrument to trigger once.
    """

    def __init__(
        self,
        instrument_name: str,
        pico_series: str,
        channels: List,
        timeout_ms: int = 20_000,
    ):
        super().__init__(instrument_name=instrument_name)
        self.pico_series = pico_series
        self.channels = channels
        self.timeout_ms = timeout_ms  # time (in ms) instrument waits for trigger before auto-triggering

        self.num_vert_divisions = 8
        self.record_length = 1e3  # Maximum 64 MS
        self.trigger_channel = 0
        self.offset_position = 0
        self.timebase = 10e-3  # time/div * number of divisions

        self.measurements = ["", "", "", "", ""]
        self.channel_params = {}
        self.trigger_params = {
            "trigger_level": 1.0,
            "channel": 0,
            "edge": "Rising",
        }

        self.add_parameter(
            "TIMEBASE",
            read_command=self._get_timebase,
            set_command=self._set_timebase,
            dummy_return="5e-3",
        )
        self.add_parameter(
            "TIME_OFFSET",
            read_command=self._get_timeoffset,
            set_command=self._set_timeoffset,
            dummy_return="6e-3",
        )

        self.add_parameter(
            "TRIGGER_LEVEL",
            read_command=None,
            set_command=self.create_set_trigger_func("trigger_level"),
        )
        self.add_parameter(
            "TRIGGER_CHANNEL",
            read_command=None,
            set_command=self.create_set_trigger_func("channel"),
        )
        self.add_parameter(
            "TRIGGER_EDGE",
            read_command=None,
            set_command=self.create_set_trigger_func("edge"),
        )

        for channel in self.channels:
            self.channel_params[channel] = {
                "volts_div": 2.0,
                "offset": 0.0,
                "coupling": "DC",
                "probe_atten": 1.0,
            }
            self.add_parameter(
                f"CH{channel}_VOLTS_DIV",
                read_command=None,
                set_command=self.create_set_channel_func(channel, "volts_div"),
            )
            self.add_parameter(
                f"CH{channel}_OFFSET",
                read_command=None,
                set_command=self.create_set_channel_func(channel, "offset"),
            )
            self.add_parameter(
                f"CH{channel}_COUPLING",
                read_command=None,
                set_command=self.create_set_channel_func(channel, "coupling"),
            )
            self.add_parameter(
                f"CH{channel}_PROBE_ATTEN",
                read_command=None,
                set_command=self.create_set_channel_func(channel, "probe_atten"),
            )
            self.add_parameter(
                f"CH{channel}_WAVEFORM",
                read_command=partial(self._read_waveform, channel),
                set_command=None,
                dummy_return=self._read_waveform_dummy,
            )

        self.add_command("SINGLE_TRIGGER", self._trigger)

    def create_set_trigger_func(self, param):
        """Create a function that sets all parameters relating to triggering."""

        @pico_error_check
        def func(value):
            self.trigger_params[param] = value
            channel = int(self.trigger_params["channel"])
            if float(self.trigger_params["trigger_level"]) >= float(
                self.channel_params[channel]["volts_div"]
            ):
                logger.error("Trigger Level must be smaller than Volts/Div.")
                return
            kwargs = {
                "threshold_V": float(self.trigger_params["trigger_level"]),
                "direction": self.trigger_params["edge"],
                "timeout_ms": self.timeout_ms,
            }

            self.ps.setSimpleTrigger(trigSrc=channel, **kwargs)

        return func

    def create_set_channel_func(self, channel, param):
        """Create a channel specific function to set a parameter."""

        @pico_error_check
        def func(value):
            self.channel_params[channel][param] = value
            kwargs = {
                "VRange": float(self.channel_params[channel]["volts_div"]),
                "VOffset": float(self.channel_params[channel]["offset"]),
                "coupling": self.channel_params[channel]["coupling"],
                "probeAttenuation": float(self.channel_params[channel]["probe_atten"]),
            }

            if 5 * kwargs["probeAttenuation"] < kwargs["VRange"]:
                logger.error(
                    "Volts/Div must be greater than 5 times the Probe Attenuation."
                )
                return

            self.ps.setChannel(channel=channel, **kwargs)

        return func

    @pico_error_check
    def _get_timebase(self):
        return str(self.ps.sampleInterval * self.ps.noSamples)

    @pico_error_check
    def _set_timebase(self, value):
        self.timebase = float(value)
        if self.timebase < 5e-6:
            self.timebase = 5e-6
        sampling_interval = self.timebase / self.record_length
        self.ps.setSamplingInterval(sampling_interval, self.timebase)
        # could not get normal readout mode to work, so using memory Segments and bulk readout
        self.ps.memorySegments(1)
        self.ps.setNoOfCaptures(1)

    def _get_timeoffset(self):
        return str(self.offset_position)

    def _set_timeoffset(self, value):
        self.offset_position = float(value)

    @pico_error_check
    def _trigger(self):
        self.ps.runBlock(pretrig=self.offset_position / self.timebase)
        self.ps.waitReady()

    def try_connect(self):
        """Unique picoscope ‘try_connect’ function."""

        if self._dummy:
            if self._online:
                return True

            logger.debug(
                f"{self.name}: creating dummy connection to {self.connection_addr}"
            )
            self._online = True
            return True

        if self._online:
            return True

        logger.debug(f"{self.name}: trying to connect")

        try:
            if self.pico_series == "2000a":
                self.ps = PS2000a()
            elif self.pico_series == "5000a":
                self.ps = PS5000a()
            elif self.pico_series == "6000":
                self.ps = PS6000()
            self._online = True
        except Exception as e:
            self._online = False
            logger.debug(
                f"\t({self.name}) ERROR connecting with picoscope: {e}.", exc_info=True
            )
            logger.debug(f"{self.name} is offline")
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
        t : list
            List of the time stamps
        volts : list
            List of the function values in Volts

        """

        try:
            data = self.ps.getDataV(channel)
            volts = list(data)

            # Get time values
            t = np.linspace(0, self.ps.sampleInterval * self.ps.noSamples, len(volts))
            t = t - t[-1] * self.offset_position / self.timebase
            t = list(t)
        except OSError as e:
            if "PICO_NO_SAMPLES_AVAILABLE" in e.args[0]:
                logger.error(
                    "Failed to read waveform data from scope: no data available"
                )
            else:
                logger.error("Failed to read waveform data from scope", exc_info=True)
            return
        except AttributeError as e:
            if "maxSamples" in e.args[0]:
                logger.error(
                    "Failed to read waveform data from scope: TIMEBASE not set"
                )
            elif "noSamples" in e.args[0]:
                logger.error(
                    "Failed to read waveform data from scope: TIMEBASE not set"
                )
            else:
                logger.error("Failed to read waveform data from scope", exc_info=True)
            return

        return json.dumps([t, volts], separators=(",", ":"))

    def _read_waveform_dummy(self):
        """Returns a dummy waveform.

        Returns
        -------
        waveform : str
            A string that contains a list of times and a list of random waveform values (between 0 and 10) embedded in another list.
        """

        dummy_return = str(np.random.uniform(0.0, 10.0, 10).tolist()).replace(" ", "")
        return f"[[1,2,3,4,5,6,7,8,9,10],{dummy_return}]"
