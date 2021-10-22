"""RIGOL’s 1000Z Series Digital Oscilloscope

.. image:: /images/RigolDS100Z.png
  :height: 200

See class definition for details.

"""

import json
import logging

import numpy as np

from ...base.hooks import format_float, format_bool, min_len_converter
from ...base import Instrument

logger = logging.getLogger(__name__)


class Rigol_DS1000Z1(Instrument):
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
            write_command=":TIM:MAIN:SCAL {}",
            dummy_return="1e-6",
            pre_hooks=[format_float(".6E")],
        )

        self.add_parameter(
            "TIME_OFFSET",
            read_command=":TIM:MAIN:OFFS?",
            write_command=":TIM:MAIN:OFFS {}",
            dummy_return="2e-6",
            pre_hooks=[format_float(".6E")],
        )
        self.add_parameter(
            "LABELS_ENABLED",
            read_command="DISP:LAB?",
            write_command="DISP:LAB {}",
            dummy_return="1",
            pre_hooks=[format_bool],
        )
        self.add_parameter(
            "TRIGGER_LEVEL",
            read_command="TRIG:EDGE:LEV?",
            write_command="TRIG:EDGE:LEV {}",
            dummy_return="1e-6",
            pre_hooks=[format_float(".6E")],
        )

        # possible values: "AC", "DC", "LFReject", "HFReject"
        self.add_parameter(
            "TRIGGER_COUPLING",
            read_command="TRIG:COUP?",
            write_command="TRIG:COUP {}",
            dummy_return="DC",
        )

        # possible values: "NEG", "POS", "RFALI"
        self.add_parameter(
            "TRIGGER_EDGE",
            read_command="TRIG:EDGE:SLOP?",
            write_command="TRIG:EDGE:SLOP {}",
            dummy_return="NEG",
        )
        self.add_parameter(
            "TRIGGER_CHANNEL",
            read_command="TRIG:EDG:SOUR?",
            write_command="TRIG:EDG:SOUR CHAN{}",
            dummy_return="1",
        )

        self.add_parameter(
            "MEAS_STAT_ENABLED",
            read_command=":MEAS:STAT:DISP?",
            write_command=":MEAS:STAT:DISP {}",
            dummy_return="1",
            pre_hooks=[format_bool],
        )

        for ch in range(self.number_channels):

            self.add_parameter(
                f"CH{ch}_VOLTS_DIV",
                read_command=f":CHAN{ch}:SCAL?",
                write_command=f":CHAN{ch}:SCAL {{}}",
                dummy_return="2",
                pre_hooks=[format_float(".6E")],
            )
            self.add_parameter(
                f"CH{ch}_OFFSET",
                read_command=f"CHAN{ch}:OFFS?",
                write_command=f"CHAN{ch}:OFFS {{}}",
                dummy_return="1e-6",
                pre_hooks=[format_float(".6E")],
            )
            self.add_parameter(
                f"CH{ch}_BW_LIM",
                read_command=f"CHAN{ch}:BWL?",
                write_command=f"CHAN{ch}:BWL {{}}",
                dummy_return="True",
            )
            self.add_lookup(f"CH{ch}_BW_LIM", {"True": "20M", "False": "OFF"})

            self.add_parameter(
                f"CH{ch}_ACTIVE",
                read_command=f"CHAN{ch}:DISP?",
                write_command=f"CHAN{ch}:DISP {{}}",
                dummy_return="1",
                pre_hooks=[format_bool],
            )

            self.add_parameter(
                f"CH{ch}_LABEL",
                read_command=f"CHAN{ch}:LAB?",
                write_command=f"CHAN{ch}:LAB {{}}",
                dummy_return="label unkown",
                pre_hooks=[min_len_converter(32)],
            )

            self.add_parameter(
                f"CH{ch}_INVERT",
                read_command=f"CHAN{ch}:INV?",
                write_command=f"CHAN{ch}:INV {{}}",
                dummy_return="1",
                pre_hooks=[format_bool],
            )

            self.add_parameter(
                f"CH{ch}_PROBE_ATTEN",
                read_command=f"CHAN{ch}:PROB?",
                write_command=f"CHAN{ch}:PROB {{}}",
                dummy_return="1",
                pre_hooks=[format_float(".6E")],
            )

            # possible values: "AC, "DC"
            self.add_parameter(
                f"CH{ch}_COUPLING",
                read_command=f"CHAN{ch}:COUP?",
                write_command=f"CHAN{ch}:COUP {{}}",
                dummy_return="DC",
            )

            sefl.add_parameter(
                f"CH{ch}_WVFM",
                read_command=lambda: self.read_waveform(ch),
            )

        self.add_command("SINGLE_TRIGGER", ":SING")
        self.add_command("RUN", ":RUN")
        self.add_command("STOP", ":STOP")

    def read_waveform(self, channel: int):

        self.write(f"WAV:SOUR CHAN{channel}")  # Specify channel to read
        self.write("WAV:MODE NORM")  # Specify to read data displayed on screen
        self.write("WAV:FORM ASCII")  # Specify data format to ASCII
        data = self.query("WAV:DATA?")  # Request data

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
