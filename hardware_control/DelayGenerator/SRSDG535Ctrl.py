"""Stanford Research Systems DG535.

See class definition for details.

"""

import logging

from hardware_control.base.HC_Backend import HC_Backend
from hardware_control.utility import ensure_float, get_channel_from_command

logger = logging.getLogger(__name__)


class SRSDG535Ctrl(HC_Backend):
    """A driver for the Stanford Research Systems DG535.

    Instrument home page: https://www.thinksrs.com/products/DG535.htm
    Manual: https://www.thinksrs.com/downloads/pdfs/manuals/DG535m.pdf

    The instrument uses GPIB (tested with a NI-GPIB-usb adapter) and
    is controlled using the pyvisa library.

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

    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)
        channel = SRSDG535Ctrl.SRS_channel_number_scheme.get(channel, None)

        value_orig = value
        value = ensure_float(value)

        if self.dummy:
            return value_orig
        elif not self.online:
            return "offline"

        if setting == "trigger_mode":
            mode = 0
            if value_orig == "Internal":
                mode = 0
            elif value_orig == "External":
                mode = 1
            elif value_orig == "Single":
                mode = 2
            elif value_orig == "Burst":
                mode = 3
            w = f"TM{mode}"
        elif setting == "trigger_edge":
            mode = 0
            if value_orig == "Positive":
                mode = 1
            elif value_orig == "Negative":
                mode = 0
            w = f"TS{mode}"
        elif setting == "ext_trig_Zin":
            mode = 0
            if value_orig == "50 Ohms":
                mode = 0
            elif value_orig == "Hi-Z":
                mode = 1
            w = f"TZ{mode}"
        elif setting_X == "CHX_output_mode":
            mode = 0
            if value_orig == "TTL":
                mode = 0
            elif value_orig == "NIM":
                mode = 1
            elif value_orig == "ECL":
                mode = 2
            elif value_orig == "VAR":
                mode = 3
            w = f"OM {channel},{mode}"
        elif setting_X == "CHX_relative":
            self.channels_relative[channel] = value_orig
            if channel in self.channels_ampl:
                ampl_chan = self.channels_ampl[channel]
            else:
                ampl_chan = "1"
            channel_number = SRSDG535Ctrl.SRS_trigger_names.get(value_orig, None)
            w = f"DT {channel},{channel_number},{ampl_chan}"
        elif setting_X == "CHX_delay":
            self.channels_ampl[channel] = value_orig
            if channel in self.channels_relative:
                rel_chan = self.channels_relative[channel]
            else:
                rel_chan = "Trig"
            rel_chan = SRSDG535Ctrl.SRS_trigger_names.get(rel_chan, None)

            w = f"DT {channel},{rel_chan},{value}"
        elif setting_X == "CHX_output_offset":
            w = f"OO {channel},{value_orig}"
        elif setting_X == "CHX_output_amplitude":
            if value > 4:
                value = 4
            if value < 0.1:
                value = 0.1
            w = f"OA {channel},{value}"
        elif setting == "pulses_per_burst":
            w = f"BC{value}"
        elif setting == "trigger_period":
            w = f"BP{value}"
        elif setting == "trigger_level":
            w = f"TL{value}"
        else:
            logger.warning(f"{self.ID} - Unknown setting: {setting} | {value}")
            return "False"

        try:
            logger.debug(f"{self.ID} writes: {w}")
            self.write(w)
            return "True"
        except Exception:
            logging.error(
                f"{self.ID} - An exception occurred in update_setting()", exc_info=True,
            )
            return "False"

    def command(self, cmd: str):
        if self.online:
            try:
                if cmd == "single_trigger":
                    # Tells DG535 to do a single trigger
                    self.write("SS")
                else:
                    logger.warning(f"{self.ID} : unknown command")
            except Exception:
                logger.error(
                    f"{self.ID} - An exception occurred in command()", exc_info=True
                )
        return cmd

    def write(self, cmd: str):
        try:
            if self.online and not self.dummy:
                self.device.write(cmd)
                logger.debug(f'\tSRSDG535< "{cmd}"')
        except Exception:
            logger.error(f"{self.ID} - An exception occurred in write", exc_info=True)
