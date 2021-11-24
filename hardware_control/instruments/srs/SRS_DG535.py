"""
.. image:: /images/DG535.jpg
  :height: 200

"""

import logging

from ...base import Instrument
from ...base.hooks import range_validator, substring_hook

logger = logging.getLogger(__name__)


class SRS_DG535(Instrument):
    """Stanford Research Systems DG535 instrument class.

    The instrument uses GPIB (tested with a NI-GPIB-usb adapter) and
    is controlled using the pyvisa library. The `DelayGenerator` control
    implements most of the device's features.

    PARAMETERS
        * TRIGGER_MODE (*INTERNAL*, *EXTERNAL*, *SINGLE*, *BURST*)
            * Trigger mode.
        * TRIGGER_EDGE (*POS*, *NEG*)
            * Trigger edge – either falling (POS) or rising (NEG).
        * TRIGGER_LEVEL (*float*)
            * External trigger voltage.
        * TRIGGER_PERIOD (*int*)
            * Period (in milliseconds) of one trigger in a burst (between 2 and 37266).
        * INTERNAL_TRIGGER_RATE (*int*)
            * Trigger frequency (in Hz) while in internal trigger mode. Only available in Internal mode.
        * BURST_TRIGGER_RATE (*int*)
            * Trigger frequency (in Hz) while in burst trigger mode. Only available in Burst mode.
        * PULSES_PER_BURST (*int*)
            * Number of pulses in a burst (between 2 and 32766).
        * CH<X>_OUTPUT_MODE (*TTL*, *NIM*, *ECL*, *VAR*)
            * Channel 'X' output mode (transistor-transistor logic, nuclear instrument modules, emitter-coupled logic, or variable)
        * CH<X>_OUTPUT_OFFSET (*float*)
            * Voltage output offset of channel 'X'. Only available in variable output mode.
        * CH<X>_OUTPUT_AMPLITUDE (*float*)
            * Voltage output amplitude of channel 'X'. Only available in variable output mode.
        * CH<X>_DELAY (*float*)
            * Delay time (in seconds) of channel 'X' with respect to another channel (see 'CH<X>_RELATIVE_TO').
        * CH<X>_RELATIVE_TO (*'T0'*, *'A'*, *'B'*, *'C'*, *'D'*)
            * Channel with respect to which the delay on channel 'X' is applied (see 'CH<X>_DELAY').
        * CH<X>_TRIGGER_IMPEDANCE (*50-OHMS*, *HI-Z*)
            * Trigger input impedance of channel 'X'.

    COMMANDS
        * SINGLE_TRIGGER
            * Set the instrument to trigger once.
    """

    _CHANNEL_NAMES = {
        "TRIG": "0",
        "T0": "1",
        "A": "2",
        "B": "3",
        "AB": "4",
        "C": "5",
        "D": "6",
        "CD": "7",
    }

    def __init__(
        self,
        instrument_name: str = "SRS_DG535",
        connection_addr: str = "",
    ):

        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        self.manufacturer = "SRS"
        self.model = "DG535"

        #   Device Specific Values
        self.delay = 0.25
        self.startup_delay = 3.0
        self._termination = "\r\n"

        self.check_connection_commands = ["IS", "ES"]

        self.add_command("SINGLE_TRIGGER", "SS")
        self.add_parameter(
            "TRIGGER_MODE",
            read_command="TM",
            set_command="TM {}",
            dummy_return="BURST",
        )
        self.add_lookup(
            "TRIGGER_MODE",
            {
                "INTERNAL": "0",
                "EXTERNAL": "1",
                "SINGLE": "2",
                "BURST": "3",
            },
        )

        self.add_parameter(
            "TRIGGER_EDGE",
            read_command="TS",
            set_command="TS {}",
            dummy_return="POS",
        )
        self.add_lookup("TRIGGER_EDGE", {"POS": "1", "NEG": "0"})

        self.add_parameter(
            "TRIGGER_LEVEL", read_command="TL", set_command="TL {}", dummy_return="1.0"
        )

        self.add_parameter(
            "TRIGGER_PERIOD", read_command="BP", set_command="BP {}", dummy_return="2.0"
        )

        self.add_parameter(
            "INTERNAL_TRIGGER_RATE",
            read_command="TR 0",
            set_command="TR 0,{}",
            dummy_return="3.0",
        )

        self.add_parameter(
            "BURST_TRIGGER_RATE",
            read_command="TR 1",
            set_command="TR 1,{}",
            dummy_return="4.0",
        )

        self.add_parameter(
            "PULSES_PER_BURST",
            read_command="BC",
            set_command="BC {}",
            dummy_return="500.0",
        )

        for inst_ch_name, channel in SRS_DG535._CHANNEL_NAMES.items():
            if inst_ch_name in ["Trig0", "T0"]:
                continue
            self.add_parameter(
                f"CH{inst_ch_name}_OUTPUT_MODE",
                read_command=f"OM {channel}",
                set_command=f"OM {channel},{{}}",
                dummy_return="VAR",
            )
            self.add_lookup(
                f"CH{inst_ch_name}_OUTPUT_MODE",
                {
                    "TTL": "0",
                    "NIM": "1",
                    "ECL": "2",
                    "VAR": "3",
                },
            )
            self.add_parameter(
                f"CH{inst_ch_name}_OUTPUT_OFFSET",
                read_command=f"OO {channel}",
                set_command=f"OO {channel},{{}}",
                dummy_return="0.2",
            )
            self.add_parameter(
                f"CH{inst_ch_name}_OUTPUT_AMPLITUDE",
                read_command=f"OA {channel}",
                set_command=f"OA {channel},{{}}",
                pre_hooks=[range_validator(0.1, 4.0)],
                dummy_return="3.2",
            )
            self.add_parameter(
                f"CH{inst_ch_name}_TRIGGER_IMPEDANCE",
                read_command=f"TZ {channel}",
                set_command=f"TZ {channel},{{}}",
                dummy_return="50-OHMS",
            )
            self.add_lookup(
                f"CH{inst_ch_name}_TRIGGER_IMPEDANCE", {"50-OHMS": "0", "HI-Z": "1"}
            )

            if inst_ch_name in ["AB", "CD"]:
                continue
            # DELAY and RELATIVE_TO parameters both return values of the format
            # {'relative channel'},{'delay time'}. A post-hook is added to both
            # parameters in order to only read out the delay time for the DELAY
            # parameter and the relative channel for the RELATIVE_TO parameter
            self.add_parameter(
                f"CH{inst_ch_name}_DELAY",
                read_command=f"DT {channel}",
                set_command=f"DT {channel},{{}}",
                post_hooks=[substring_hook(2, None)],
                dummy_return="0.5",
            )

            self.add_parameter(
                f"CH{inst_ch_name}_RELATIVE_TO",
                read_command=f"DT {channel}",
                set_command=f"DT {channel},{{}}",
                post_hooks=[
                    substring_hook(None, 1),
                    self.numeric_to_alpha,
                ],
                dummy_return="T0",
            )

        def try_connect(self):
            """Need to clear the buffer every time we start the instrument."""
            super().try_connect()
            self.device.write("CL")

    def numeric_to_alpha(self, value):
        inverse_CHANNEL_NAMES = {b: a for a, b in self._CHANNEL_NAMES.items()}
        value = inverse_CHANNEL_NAMES[value]

        return value
