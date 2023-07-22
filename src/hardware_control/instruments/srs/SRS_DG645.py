"""
.. image:: /images/DG535.jpg
  :height: 200

"""

import logging

from ...base import Instrument
from ...base.hooks import range_validator, substring_hook

logger = logging.getLogger(__name__)


class SRS_DG645(Instrument):
    """Stanford Research Systems DG645 instrument class.

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

    _CHANNEL_NAMES_B = {
        "T0": "0",
        "AB": "2",
        "CD": "2",
        "EF": "3",
        "GH": "4",
    }

    _CHANNEL_NAMES_C = {
        "T0": "0",
        "T1": "1",
        "A": "2",
        "B": "3",
        "C": "4",
        "D": "5",
        "E": "6",
        "F": "7",
        "G": "8",
        "H": "9",
    }

    def __init__(
        self,
        instrument_name: str = "SRS_DG645",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        self.manufacturer = "SRS"
        self.model = "DG645"

        #   Device Specific Values
        self.delay = 0.25
        self.startup_delay = 3.0
        self._termination = "\r\n"

        self.check_connection_commands = ["*IDN?", "TSRC 5"]

        self.add_command("SINGLE_TRIGGER", "TSRC 5")
        self.add_parameter(
            "TRIGGER_SOURCE",
            read_command="TSRC?",
            set_command="TSRC {}",
            dummy_return="BURST",
        )
        trigger_source = {
            "INTERNAL": "0",
            "EXTERNAL_RISING": "1",
            "EXTERNAL_FALLING": "2",
            "SINGLE": "5",
            "LINE": "6",
        }

        self.add_lookup("TRIGGER_SOUCE", {**trigger_source})

        self.add_parameter(
            "TRIGGER_LEVEL",
            read_command="TLVL?",
            set_command="TLVL {}",
            dummy_return="1.0",
        )

        self.add_parameter(
            "INTERNAL_TRIGGER_RATE",
            read_command="TRAT? 0",
            set_command="TRAT {}",
            dummy_return="3.0",
        )

        self.add_parameter(
            "BURST_COUNT",
            read_command="BURC?",
            set_command="BURC {}",
            dummy_return="500.0",
        )

        self.add_parameter(
            "BURST_DELAY",
            read_command="BURD?",
            set_command="BURD {}",
            dummy_return="500.0",
        )

        self.add_parameter(
            "BURST_PERIOD",
            read_command="BURP?",
            set_command="BURP {}",
            dummy_return="500.0",
        )

        for inst_ch_name, channel in self._CHANNEL_NAMES_B.items():
            if inst_ch_name in ["T0", "T1"]:
                continue
            self.add_parameter(
                f"CH{inst_ch_name}_OUTPUT_MODE",
                read_command=f"OM {channel}",
                set_command=f"OM {channel},{{}}",
                dummy_return="VAR",
            )

            self.add_parameter(
                f"CH{inst_ch_name}_OUTPUT_OFFSET",
                read_command=f"LOFF? {channel}",
                set_command=f"LOFF {channel},{{}}",
                dummy_return="0.2",
            )
            self.add_parameter(
                f"CH{inst_ch_name}_OUTPUT_AMPLITUDE",
                read_command=f"LAMP? {channel}",
                set_command=f"LAMP {channel},{{}}",
                pre_hooks=[range_validator(0.1, 4.0)],
                dummy_return="3.2",
            )
            self.add_parameter(
                f"CH{inst_ch_name}_OUTPUT_POLARITY",
                read_command=f"LPOL? {channel}",
                set_command=f"LPOL {channel},{{}}",
                dummy_return="0.2",
            )

        for inst_ch_name, channel in self._CHANNEL_NAMES_C.items():
            # DELAY and RELATIVE_TO parameters both return values of the format
            # {'relative channel'},{'delay time'}. A post-hook is added to both
            # parameters in order to only read out the delay time for the DELAY
            # parameter and the relative channel for the RELATIVE_TO parameter

            self.add_parameter(
                f"CH{inst_ch_name}_RELATIVE",
                read_command=f"DLAY? {channel}",
                set_command=f"DLAY {channel},{{}}",
                post_hooks=[
                    substring_hook(None, 1),
                    self.numeric_to_alpha,
                ],
                dummy_return="T0",
            )

    def try_connect(self):
        """Need to clear the buffer every time we start the instrument."""
        super().try_connect()
        self.device.write("*CLS")

    def numeric_to_alpha(self, value):
        inverse_CHANNEL_NAMES = {b: a for a, b in self._CHANNEL_NAMES_C.items()}
        value = inverse_CHANNEL_NAMES[value]

        return value
