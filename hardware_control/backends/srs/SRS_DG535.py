"""Stanford Research Systems DG535.

.. image:: /images/DG535.jpg
  :height: 200

See class definition for details.

"""

import logging

from ..base import Backend, ensure_online
from ..utility import ensure_float, get_channel_from_command

logger = logging.getLogger(__name__)


class SRS_DG535(Backend):
    """A driver for the Stanford Research Systems DG535.

    Instrument home page: https://www.thinksrs.com/products/DG535.htm
    Manual: https://www.thinksrs.com/downloads/pdfs/manuals/DG535m.pdf

    The instrument uses GPIB (tested with a NI-GPIB-usb adapter) and
    is controlled using the pyvisa library.

    The `DelayGenerator` frontend implements most of the device's features.

    """

    # 12: combined output for ch1 and ch2
    # 34: combined output for ch3 and ch4
    SRS_channel_number_scheme = {1: 2, 2: 3, 3: 5, 4: 6, 12: 4, 34: 7}
    SRS_trigger_names = {"Trig": 0, "T0": 1, "A": 2, "B": 3, "C": 5, "D": 6}

    def __init__(self, connection_addr):

        super().__init__(instrument_name="SRS-DG535", connection_addr=connection_addr)

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

    @ensure_online
    def update_setting(self, setting: str, value):

        if self.dummy:
            return value

        channel, setting_X = get_channel_from_command(setting)
        channel = SRS_DG535.SRS_channel_number_scheme.get(channel, None)

        value_orig = value
        value = ensure_float(value)

        if setting == "TRIGGER_MODE":
            mode = 0
            if value_orig == "INTERNAL":
                mode = 0
            elif value_orig == "EXTERNAL":
                mode = 1
            elif value_orig == "SINGLE":
                mode = 2
            elif value_orig == "BURST":
                mode = 3
            command = f"TM{mode}"
        elif setting == "TRIGGER_EDGE":
            mode = 0
            if value_orig == "POSITIVE":
                mode = 1
            elif value_orig == "NEGATIVE":
                mode = 0
            command = f"TS{mode}"
        elif setting == "EXT_TRIG_ZIN":
            mode = 0
            if value_orig == "50 OHMS":
                mode = 0
            elif value_orig == "HI-Z":
                mode = 1
            command = f"TZ{mode}"
        elif setting_X == "CHX_OUTPUT_MODE":
            mode = 0
            if value_orig == "TTL":
                mode = 0
            elif value_orig == "NIM":
                mode = 1
            elif value_orig == "ECL":
                mode = 2
            elif value_orig == "VAR":
                mode = 3
            command = f"OM {channel},{mode}"
        elif setting_X == "CHX_RELATIVE":
            self.channels_relative[channel] = value_orig
            if channel in self.channels_ampl:
                ampl_chan = self.channels_ampl[channel]
            else:
                ampl_chan = "1"
            channel_number = SRS_DG535.SRS_trigger_names.get(value_orig, None)
            command = f"DT {channel},{channel_number},{ampl_chan}"
        elif setting_X == "CHX_DELAY":
            self.channels_ampl[channel] = value_orig
            if channel in self.channels_relative:
                rel_chan = self.channels_relative[channel]
            else:
                rel_chan = "TRIG"
            rel_chan = SRS_DG535.SRS_trigger_names.get(rel_chan, None)

            command = f"DT {channel},{rel_chan},{value}"
        elif setting_X == "CHX_OUTPUT_OFFSET":
            command = f"OO {channel},{value_orig}"
        elif setting_X == "CHX_OUTPUT_AMPLITUDE":
            if value > 4:
                value = 4
            if value < 0.1:
                value = 0.1
            command = f"OA {channel},{value}"
        elif setting == "PULSES_PER_BURST":
            command = f"BC{value}"
        elif setting == "TRIGGER_PERIOD":
            command = f"BP{value}"
        elif setting == "TRIGGER_LEVEL":
            command = f"TL{value}"
        else:
            logger.warning(f"{self.ID} - Unknown setting: {setting} | {value}")
            return "False"

        try:
            logger.debug(f"{self.ID} writes: {command}")
            self.write(command)
            error_byte = self.query("ES")
            if error_byte == 0:
                return f"{setting}={value_orig}"
            logging.error(
                f"{self.ID} - Got instrument error in update_setting: {setting} {value_orig} error: {error_byte}",
            )
            return "Error"

        except Exception:
            logging.error(
                f"{self.ID} - An exception occurred in update_setting()", exc_info=True,
            )
            return "Error"

    @ensure_online
    def command(self, cmd: str):
        if cmd == "SINGLE_TRIGGER":
            self.write("SS")
        else:
            logger.warning(f"{self.ID} : unknown command")
        return cmd
