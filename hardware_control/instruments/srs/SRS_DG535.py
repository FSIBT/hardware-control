"""Stanford Research Systems DG535.

.. image:: /images/DG535.jpg
  :height: 200

See class definition for details.

"""

import logging
from typing import Optional

from ...base import Instrument, hooks

logger = logging.getLogger(__name__)


class SRS_DG535(Instrument):
    """Stanford Research Systems DG535 instrument class.

    Instrument home page: https://www.thinksrs.com/products/DG535.htm
    Manual: https://www.thinksrs.com/downloads/pdfs/manuals/DG535m.pdf

    The instrument uses GPIB (tested with a NI-GPIB-usb adapter) and
    is controlled using the pyvisa library.

    The `DelayGenerator` frontend implements most of the device's features.

    """

    CHANNEL_NAMES = {
        "Trig": 0,
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
        settings_file: Optional[str] = None,
    ):

        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
        )

        self.manufacturer = "SRS"
        self.model = "DG535"

        self.num_vert_divisions = 8
        self.termination = "\r\n"

        self.command_str = ""  # string used to trigger
        #   Device Specific Values
        self.delayRange = 999.999999999995
        self.ExternalTriggerThreshold = 2.56
        self.PulsesPerBurst = 32766

        self.channels_relative = {}
        self.channels_ampl = {}

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
            dummy_return="POSITIVE",
        )
        self.add_lookup("TRIGGER_EDGE", {"POSITIVE": "1", "NEGATIVE": "0"})

        self.add_parameter(
            "EXT_TRIG_ZIN",
            read_command=f"TZ0",
            set_command="TZ0,{}",
            dummy_return="50-OHMS",
        )
        self.add_lookup("EXT_TRIG_ZIN", {"50-OHMS": "0", "HI-Z": "1"})

        for channel, inst_ch_name in SRS_DG535.CHANNEL_NAMES.items():
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

        for channel, inst_ch_name in SRS_DG535.CHANNEL_NAMES.items():
            if channel in ["Trig0", "T0"]:
                continue
            self.add_parameter(
                f"CH{channel}_OUTPUT_OFFSET",
                read_command=f"OO {inst_ch_name}",
                set_command=f"OO {inst_ch_name},{{}}",
                dummy_return="0.2",
            )
        for channel, inst_ch_name in SRS_DG535.CHANNEL_NAMES.items():
            if channel in ["Trig0", "T0"]:
                continue
            self.add_parameter(
                f"CH{channel}_OUTPUT_AMPLITUDE",
                read_command=f"OA {inst_ch_name}",
                set_command=f"OA {inst_ch_name},{{}}",
                pre_hooks=[hooks.range_validator(0.1, 4.0)],
                dummy_return="3.2",
            )

        for channel1, channel1_int in SRS_DG535.CHANNEL_NAMES.items():
            if channel1 in ["Trig0", "T0"]:
                continue
            for channel2, channel2_int in SRS_DG535.CHANNEL_NAMES.items():
                if channel1_int <= channel2_int:
                    continue
                if channel1 in ["AB", "CD"]:
                    continue
                if channel2 in ["AB", "CD"]:
                    continue
                self.add_parameter(
                    f"CH{channel1}_{channel2}_DELAY",
                    read_command=f"DT {channel1_int}",
                    set_command=f"DT {channel1_int},{channel2_int},{{}}",
                    dummy_return="0.1",
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

        if settings_file != None:
            self.load_state(settings_file)
