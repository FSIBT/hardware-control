"""
.. image:: /images/Keysight4000X.jpeg
  :height: 200

"""

from functools import partial
import json
import logging
import numpy as np

from ...base import Instrument
from ...base.hooks import (
    format_float,
    format_int,
    expected_input_validator,
    max_len_converter,
    substring_hook,
    range_validator,
)

logger = logging.getLogger(__name__)


class Keysight_4000X(Instrument):
    """Keysight InfiniiVision 4000 X-Series Oscilloscope instrument class.

    PARAMETERS
        * TIMEBASE (*float*)
            * Horizontal resolution in time per division.
        * TIME_OFFSET (*float*)
            * Time offset from trigger.
        * NUM_POINTS (*int*)
            * Number of points on the time axis.
        * LABELS_ENABLED (*bool*)
            * On/Off status of channel labels on the instrument.
        * TRIGGER_LEVEL (*float*)
            * Trigger level.
        * TRIGGER_COUPLING (*AC*, *DC*, *LFReject*)
            * Trigger coupling type.
        * TRIGGER_EDGE (*BOTH*, *NEG*, *POS*, *ALT*)
            * Edge of waveform that the oscilloscope triggers on.
        * TRIGGER_CHANNEL (*int*)
            * The channel (1,2,3, or 4) to trigger on.
        * CH<X>_VOLTS_DIV (*float*)
            * The voltage per division for channel 'X'.
        * CH<X>_OFFSET (*float*)
            * The voltage offset for channel 'X'.
        * CH<X>_IMPEDANCE (*50*, *1e6*)
            * The imedance for channnel 'X'.
        * CH<X>_LABEL (*str*)
            * Label for channel 'X'.
        * CH<X>_PROBE_ATTEN (*float*)
            * Probe attenuation for channel 'X'. For example, providing the value '10' would indicate a 10x or 10:1 probe.
        * CH<X>_COUPLING (*AC*, *DC*)
            * Coupling mode for channel 'X'.
        * CH<X>_WAVEFORM
            * Most recent waveform measurement from channel 'X'.
        * CH<X>_ON-OFF
            * Enables or disables channel 'X'.
        * CH<X>_BW_LIM
            * Enables or disables the 20MHz bandwidth limit for channel 'X'.
        * CH<X>_INVERT
            * Enables or disables inversion of the channel 'X' waveform.

    COMMANDS
        * SINGLE_TRIGGER
            * Set the instrument to trigger once and save the data.
        * RUN
            * Set the instrument to continuously trigger.
        * STOP
            * Prevent the instrument from triggering.
        * DIGITIZE
            * Start digitize process for waveform

    """

    def __init__(
        self,
        instrument_name: str = "KEYSIGHT-4000X",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=5025,
        )

        self.chan_nums = [1, 2, 3, 4]

        self.num_vert_divisions = 8
        self.check_connection_commands = "*IDN?"

        self.add_parameter(
            "TIMEBASE",
            read_command=":TIM:SCAL?",
            set_command=":TIM:SCAL {}",
            pre_hooks=[range_validator(1e-9, 50), format_float(".6E")],
            dummy_return="5e-3",
        )

        self.add_parameter(
            "TIME_OFFSET",
            read_command=":TIM:POS?",
            set_command=":TIM:POS {}",
            pre_hooks=[format_float(".6E")],
            dummy_return="6e-3",
        )

        self.add_parameter(
            "NUM_POINTS",
            read_command=":WAV:POIN?",
            set_command=":WAV:POIN {}",
            pre_hooks=[format_int],
            dummy_return="2",
        )

        self.add_parameter(
            "LABELS_ENABLED",
            read_command="DISP:LAB?",
            set_command="DISP:LAB {}",
            dummy_return="False",
        )
        self.add_lookup("LABELS_ENABLED", {"True": "1", "False": "0"})

        self.add_parameter(
            "TRIGGER_LEVEL",
            read_command="TRIG:EDGE:LEV?",
            set_command="TRIG:EDGE:LEV {}",
            pre_hooks=[format_float(".6E")],
            dummy_return="8.",
        )

        self.add_parameter(
            "TRIGGER_COUPLING",
            read_command="TRIG:COUP?",
            set_command="TRIG:COUP {}",
            pre_hooks=[expected_input_validator(["AC", "DC", "LFReject"], "DC")],
            dummy_return="DC",
        )

        self.add_parameter(
            "TRIGGER_EDGE",
            read_command="TRIG:EDGE:SLOP?",
            set_command="TRIG:EDGE:SLOP {}",
            pre_hooks=[expected_input_validator(["BOTH", "NEG", "POS", "ALT"], "POS")],
            dummy_return="POS",
        )

        self.add_parameter(
            "TRIGGER_CHANNEL",
            read_command="TRIG:SOUR?",
            set_command="TRIG:SOUR CHAN{}",
            pre_hooks=[format_int],
            post_hooks=[substring_hook(4, None)],
            dummy_return="1",
        )

        for channel in self.chan_nums:
            self.add_parameter(
                f"CH{channel}_VOLTS_DIV",
                read_command=f":CHAN{channel}:SCAL?",
                set_command=f":CHAN{channel}:SCAL {{}}",
                pre_hooks=[format_float(".6E")],
                dummy_return="0.05",
            )

            self.add_parameter(
                f"CH{channel}_OFFSET",
                read_command=f"CHAN{channel}:OFFS?",
                set_command=f"CHAN{channel}:OFFS {{}}",
                pre_hooks=[format_float(".6E")],
                dummy_return="1.",
            )

            self.add_parameter(
                f"CH{channel}_LABEL",
                read_command=f"CHAN{channel}:LAB?",
                set_command=f"CHAN{channel}:LAB {{}}",
                pre_hooks=[max_len_converter(32)],
                dummy_return="2.",
            )

            self.add_parameter(
                f"CH{channel}_COUPLING",
                read_command=f"CHAN{channel}:COUP?",
                set_command=f"CHAN{channel}:COUP {{}}",
                pre_hooks=[expected_input_validator(["AC", "DC"], "DC")],
                dummy_return="DC",
            )

            self.add_parameter(
                f"CH{channel}_IMPEDANCE",
                read_command=f"CHAN{channel}:IMP?",
                set_command=f"CHAN{channel}:IMP {{}}",
                dummy_return="1e6",
            )
            self.add_lookup(f"CH{channel}_IMPEDANCE", {"50": "FIFT", "1E6": "ONEM"})

            self.add_parameter(
                f"CH{channel}_PROBE_ATTEN",
                read_command=f"CHAN{channel}:PROB?",
                set_command=f"CHAN{channel}:PROB {{}}",
                pre_hooks=[format_float(".6E")],
                dummy_return="1",
            )

            self.add_parameter(
                f"CH{channel}_WAVEFORM",
                read_command=partial(self._read_waveform, channel),
                dummy_return=self._read_waveform_dummy,
            )

            self.add_parameter(
                f"CH{channel}_ON-OFF",
                read_command=f"CHAN{channel}:DISP?",
                set_command=f"CHAN{channel}:DISP {{}}",
                dummy_return="True",
            )
            self.add_lookup(f"CH{channel}_ON-OFF", {"True": "1", "False": "0"})

            self.add_parameter(
                f"CH{channel}_BW_LIM",
                read_command=f"CHAN{channel}:BWL?",
                set_command=f"CHAN{channel}:BWL {{}}",
                dummy_return="True",
            )
            self.add_lookup(f"CH{channel}_BW_LIM", {"True": "1", "False": "0"})

            self.add_parameter(
                f"CH{channel}_INVERT",
                read_command=f"CHAN{channel}:INV?",
                set_command=f"CHAN{channel}:INV {{}}",
                dummy_return="True",
            )
            self.add_lookup(f"CH{channel}_INVERT", {"True": "1", "False": "0"})

        self.add_command("SINGLE_TRIGGER", ":SING")
        self.add_command("RUN", ":RUN")
        self.add_command("STOP", ":STOP")
        self.add_command("DIGITIZE", ":DIG")

        # Initial configure call
        self.write("\n*CLS")

    def _read_waveform(self, channel: int):
        """Reads a waveform from the oscilloscope.

        Parameters
        ----------
        channel : int
            Channel number to read

        Returns
        -------
        waveform : str
            A string that contains a list of times and a list of waveform values embedded in another list.
        """

        channel_active = self.query(f"CHAN{channel}:DISP?")
        if not channel_active:
            return "[[],[]]"

        # switch to correct channel and request ASCII output
        self.write(f":WAV:SOUR CHAN{channel}")
        self.write(":WAV:FORM ASCII")
        self.write(":WAV:POIN:MODE NORM")

        # Read waveform data
        raw_data = self.query(":WAV:DATA?")

        # Read X Origin
        x_orig = self.query(":WAV:XOR?")
        # Read X Reference
        x_ref = self.query(":WAV:XREF?")
        # Read X Increment
        x_incr = self.query(":WAV:XINC?")

        try:
            # Convert X Origin
            x_orig = float(x_orig)
            x_ref = float(x_ref)
            x_incr = float(x_incr)
        except (ValueError, TypeError):
            logger.error("Received bad origin from scope.", exc_info=True)
            return "[[],[]]"

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
            return "[[],[]]"

        out = json.dumps([t, fmt])
        return out

    def _read_waveform_dummy(self):
        """Returns a dummy waveform.

        Returns
        -------
        waveform : str
            A string that contains a list of times and a list of random waveform values (between 0 and 10) embedded in another list.
        """

        dummy_return = str(np.random.uniform(0.0, 10.0, 10).tolist()).replace(" ", "")
        return f"[[1,2,3,4,5,6,7,8,9,10],{dummy_return}]"
