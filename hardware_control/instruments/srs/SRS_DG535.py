"""
.. image:: /images/DG535.jpg
  :height: 200

"""

import logging
from typing import Optional

from hardware_control.gui.controls.DelayGenerator import DelayChannelWidget

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
        * TRIGGER_IMPEDANCE (*50-OHMS*, *HI-Z*)
            * Trigger input impedance.
        * TRIGGER_LEVEL (*float*)
            * External trigger voltage.
        * TRIGGER_PERIOD (*int*)
            * Period (in milliseconds) of one trigger in a burst (between 2 and 37266).
        * PULSES_PER_BURST (*int*)
            * Number of pulses in a burst (between 2 and 32766).
        * CH<X>_OUTPUT_MODE (*TTL*, *NIM*, *ECL*, *VAR*)
            * Channel 'X' output mode (transistor-transistor logic, nuclear instrument modules, emitter-coupled logic, or variable)
        * CH<X>_OUTPUT_OFFSET (*float*)
            * Voltage output offset of channel 'X'. Only available in variable output mode.
        * CH<X>_OUTPUT_AMPLITUDE (*float*)
            * Voltage output amplitude of channel 'X'. Only available in variable output mode.
        * CH<X>_CH<Y>_DELAY
            * Delay time (in seconds) of channel 'X' relative to channel 'Y'.

    COMMANDS
        * SINGLE_TRIGGER
            * Set the instrument to trigger once.
    """

    _CHANNEL_NAMES = {
        "TRIG": 0,
        "T0": 1,
        "A": 2,
        "B": 3,
        "AB": 4,
        "C": 5,
        "D": 6,
        "CD": 7,
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
            dummy_return="SINGLE",
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
            "TRIGGER_IMPEDANCE",
            read_command=f"TZ 0",
            set_command="TZ 0,{}",
            dummy_return="50-OHMS",
        )
        self.add_lookup("TRIGGER_IMPEDANCE", {"50-OHMS": "0", "HI-Z": "1"})

        for channel, inst_ch_name in SRS_DG535._CHANNEL_NAMES.items():
            if channel in ["Trig0", "T0"]:
                continue
            self.add_parameter(
                f"CH{channel}_OUTPUT_MODE",
                read_command=f"OM {inst_ch_name}",
                set_command=f"OM {inst_ch_name},{{}}",
                dummy_return="TTL",
            )
            self.add_lookup(
                f"CH{channel}_OUTPUT_MODE",
                {
                    "TTL": "0",
                    "NIM": "1",
                    "ECL": "2",
                    "VAR": "3",
                },
            )

        for channel, inst_ch_name in SRS_DG535._CHANNEL_NAMES.items():
            if channel in ["Trig0", "T0"]:
                continue
            self.add_parameter(
                f"CH{channel}_OUTPUT_OFFSET",
                read_command=f"OO {inst_ch_name}",
                set_command=f"OO {inst_ch_name},{{}}",
                dummy_return="0.2",
            )
        for channel, inst_ch_name in SRS_DG535._CHANNEL_NAMES.items():
            if channel in ["Trig0", "T0"]:
                continue
            self.add_parameter(
                f"CH{channel}_OUTPUT_AMPLITUDE",
                read_command=f"OA {inst_ch_name}",
                set_command=f"OA {inst_ch_name},{{}}",
                pre_hooks=[range_validator(0.1, 4.0)],
                dummy_return="3.2",
            )

        """
                for ch in channels:
                    self.add_parameter(f"CH{ch}_relative_to", read_command="DT {ch}", set_command=lambda x: self.update_relative(ch, x))
                    self.add_parameter(f"CH{ch}_delay", read_command="DT {ch}",set_command=self.update_delay)

            def update_relative(self, channel, relative):
                self.rel[channel] = relative
                self.set_relative_delay()
            def update_delay
                self.delay[channel] = delay
                self.set_relative_delay()
            def set_relative_delay
                self.delay
                self.rel
                self.write(f"DT  ")
        """     


        for channel1, channel1_int in SRS_DG535._CHANNEL_NAMES.items():
            if channel1 in ["Trig0", "T0"]:
                continue
            for channel2, channel2_int in SRS_DG535._CHANNEL_NAMES.items():
                if channel1 in ["AB", "CD"]:
                    continue
                if channel2 in ["AB", "CD"]:
                    continue
                self.add_parameter(
                    f"CH{channel1}_CH{channel2}_DELAY",
                    read_command=f"DT {channel1_int}",
                    set_command=f"DT {channel1_int},{channel2_int},{{}}",
                    dummy_return="0.1",
                    post_hooks=[substring_hook(2,None)]
                )
        self.add_parameter(
            "PULSES_PER_BURST",
            read_command="BC",
            set_command="BC {}",
            dummy_return=500,
        )
        self.add_parameter(
            "TRIGGER_LEVEL", read_command="TL", set_command="TL{}", dummy_return="1"
        )
        self.add_parameter(
            "TRIGGER_PERIOD", read_command="BP", set_command="BP {}", dummy_return="1"
        )
        
        def try_connect(self):
            """Need to clear the buffer every time we start the instrument."""
            super().try_connect()
            self.device.write("CL")