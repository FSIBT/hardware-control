"""RIGOL’s 1000Z Series Digital Oscilloscope

.. image:: /images/RigolDS100Z.png
  :height: 200

See class definition for details.

"""

from functools import partial
import json
import logging

import numpy as np

from ...base.hooks import format_float, format_bool, max_len_converter
from ...base import Instrument

logger = logging.getLogger(__name__)


class Rigol_DS1000Z(Instrument):
    """
    PARAMETERS
        * TIMEBASE (*float*)
            * Horizontal resolution in time per division.
        * TIME_OFFSET (*float*)
            * Time offset from trigger.
        * LABELS_ENABLED (*bool*)
            * On/Off status of channel labels on the instrument.
        * TRIGGER_LEVEL (*float*)
            * Trigger level.
        * TRIGGER_COUPLING (*AC*, *DC*, *LFReject*, *HFReject*)
            * Trigger coupling type.
        * TRIGGER_EDGE (*NEG*, *POS*, *RFALI*)
            * Edge of waveform that the oscilloscope triggers on.
        * TRIGGER_CHANNEL (*int*)
            * The channel (1,2,3, or 4) to trigger on.
        * MEAS_STAT_ENABLED (*bool*)
            * Show measurement stats
        * CH<X>_VOLTS_DIV (*float*)
            * The voltage per division for channel 'X'.
        * CH<X>_OFFSET (*float*)
            * The voltage offset for channel 'X'.
        * CH<X>_LABEL (*str*)
            * Label for channel 'X'.
        * CH<X>_PROBE_ATTEN (*float*)
            * Probe attenuation for channel 'X'. For example, providing the value '10' would indicate a 10x or 10:1 probe.
        * CH<X>_COUPLING (*AC*, *DC*)
            * Coupling mode for channel 'X'.
        * CH<X>_WAVEFORM
            * Most recent waveform measurement from channel 'X'.

    COMMANDS
        * SINGLE_TRIGGER
            * Set the instrument to trigger once and save the data.
        * RUN
            * Set the instrument to continuously trigger.
        * STOP
            * Prevent the instrument from triggering.

    """

    def __init__(
        self,
        instrument_name: str = "RIGOL_DS1000Z",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        self.number_channels = 4

        self.add_parameter(
            "TIMEBASE",
            read_command=":TIM:MAIN:SCAL?",
            set_command=":TIM:MAIN:SCAL {}",
            dummy_return="1e-6",
            pre_hooks=[format_float(".6E")],
        )

        self.add_parameter(
            "TIME_OFFSET",
            read_command=":TIM:MAIN:OFFS?",
            set_command=":TIM:MAIN:OFFS {}",
            dummy_return="2e-6",
            pre_hooks=[format_float(".6E")],
        )
        self.add_parameter(
            "LABELS_ENABLED",
            read_command="DISP:LAB?",
            set_command="DISP:LAB {}",
            dummy_return="1",
            pre_hooks=[format_bool],
        )
        self.add_parameter(
            "TRIGGER_LEVEL",
            read_command="TRIG:EDGE:LEV?",
            set_command="TRIG:EDGE:LEV {}",
            dummy_return="1e-6",
            pre_hooks=[format_float(".6E")],
        )

        self.add_parameter(
            "TRIGGER_COUPLING",
            read_command="TRIG:COUP?",
            set_command="TRIG:COUP {}",
            dummy_return="DC",
        )

        self.add_parameter(
            "TRIGGER_EDGE",
            read_command="TRIG:EDGE:SLOP?",
            set_command="TRIG:EDGE:SLOP {}",
            dummy_return="NEG",
        )
        self.add_parameter(
            "TRIGGER_CHANNEL",
            read_command="TRIG:EDG:SOUR?",
            set_command="TRIG:EDG:SOUR CHAN{}",
            dummy_return="1",
        )

        self.add_parameter(
            "MEAS_STAT_ENABLED",
            read_command=":MEAS:STAT:DISP?",
            set_command=":MEAS:STAT:DISP {}",
            dummy_return="1",
            pre_hooks=[format_bool],
        )

        for channel in range(self.number_channels):
            # channels are starting at 1 for Rigol scopes
            ch = channel + 1
            self.add_parameter(
                f"CH{ch}_VOLTS_DIV",
                read_command=f":CHAN{ch}:SCAL?",
                set_command=f":CHAN{ch}:SCAL {{}}",
                dummy_return="2",
                pre_hooks=[format_float(".6E")],
            )
            self.add_parameter(
                f"CH{ch}_ON-OFF",
                read_command=f"CHAN{ch}:DISP?",
                set_command=f"CHAN{ch}:DISP {{}}",
                dummy_return="True",
            )
            self.add_lookup(f"CH{ch}_ON-OFF", {"True": "1", "False": "0"})
            self.add_parameter(
                f"CH{ch}_OFFSET",
                read_command=f"CHAN{ch}:OFFS?",
                set_command=f"CHAN{ch}:OFFS {{}}",
                dummy_return="1e-6",
                pre_hooks=[format_float(".6E")],
            )
            self.add_parameter(
                f"CH{ch}_BW_LIM",
                read_command=f"CHAN{ch}:BWL?",
                set_command=f"CHAN{ch}:BWL {{}}",
                dummy_return="True",
            )
            self.add_lookup(f"CH{ch}_BW_LIM", {"True": "20M", "False": "OFF"})

            self.add_parameter(
                f"CH{ch}_ACTIVE",
                read_command=f"CHAN{ch}:DISP?",
                set_command=f"CHAN{ch}:DISP {{}}",
                dummy_return="1",
                pre_hooks=[format_bool],
            )

            self.add_parameter(
                f"CH{ch}_LABEL",
                read_command=f"CHAN{ch}:LAB?",
                set_command=f"CHAN{ch}:LAB {{}}",
                dummy_return=f"Channel_{ch}",
                pre_hooks=[max_len_converter(32)],
            )

            self.add_parameter(
                f"CH{ch}_INVERT",
                read_command=f"CHAN{ch}:INV?",
                set_command=f"CHAN{ch}:INV {{}}",
                dummy_return="True",
                pre_hooks=[format_bool],
            )

            self.add_parameter(
                f"CH{ch}_PROBE_ATTEN",
                read_command=f"CHAN{ch}:PROB?",
                set_command=f"CHAN{ch}:PROB {{}}",
                dummy_return="1",
                pre_hooks=[format_float(".6E")],
            )

            self.add_parameter(
                f"CH{ch}_COUPLING",
                read_command=f"CHAN{ch}:COUP?",
                set_command=f"CHAN{ch}:COUP {{}}",
                dummy_return="DC",
            )

            self.add_parameter(
                f"CH{ch}_WAVEFORM",
                read_command=partial(self._read_waveform, ch),
                dummy_return=self._read_waveform_dummy,
            )

        self.add_command("SINGLE_TRIGGER", ":SING")
        self.add_command("RUN", ":RUN")
        self.add_command("STOP", ":STOP")

    def _read_waveform(self, channel: int):
        """Read the waveform from the scope"""

        self.write(f"WAV:SOUR CHAN{channel}")  # Specify channel to read
        self.write("WAV:MODE NORM")  # Specify to read data displayed on screen
        self.write("WAV:FORM ASCII")  # Specify data format to ASCII
        data = self.query("WAV:DATA?")  # Request data

        if data is None:
            return "[[],[]]"

        # Split string into ASCII voltage values
        volts = data[11:].split(",")

        volts = [float(v) for v in volts]

        # Get timing data
        xorigin = float(self.query("WAV:XOR?"))
        xincr = float(self.query("WAV:XINC?"))

        # Get time values
        t = list(xorigin + np.linspace(0, xincr * (len(volts) - 1), len(volts)))

        out = [t, volts]
        return json.dumps(out)

    def _read_waveform_dummy(self):
        """Returns a dummy waveform.

        Returns
        -------
        waveform : str
            A string that contains a list of times and a list of random waveform values (between 0 and 10) embedded in another list.
        """

        dummy_return = str(np.random.uniform(0.0, 10.0, 10).tolist()).replace(" ", "")
        return f"[[1,2,3,4,5,6,7,8,9,10],{dummy_return}]"
