"""
The manual for this instrument can be found at

 https://www.thinksrs.com/downloads/pdfs/manuals/DG535m.pdf page 9ff

"""
import socket
import os
import pyvisa

from hardware_control.HC_Backend import HC_Backend, get_channel_from_command
from hardware_control.utility import ensure_float
import logging

logger = logging.getLogger(__name__)


class SRSDG535Ctrl(HC_Backend):
    def __init__(self, connection_addr):

        super().__init__()

        self.ID = "SRS-DG535"

        self.connection_addr = connection_addr
        self.online = False
        self.num_vert_divisions = 8

        self.command_str = ""  # string used to trigger
        #   Device Specific Values
        self.delayRange = 999.999999999995
        self.ExternalTriggerThreshold = 2.56
        self.PulsesPerBurst = 32766

        self.channels_relative = {}
        self.channels_ampl = {}

    def convert_to_SRS_number_scheme(self, x: int):

        if x == 1:
            return 2
        if x == 2:
            return 3
        if x == 3:
            return 5
        if x == 4:
            return 6
        if x == 12:  # Combined 1&2
            return 4
        if x == 34:  # Combined 3&4
            return 7

    def convert_relative_to_SRS_number_scheme(self, x: str):

        if x == "A":
            return 2
        if x == "B":
            return 3
        if x == "C":
            return 5
        if x == "D":
            return 6
        if x == "Trig":  # Combined 1&2
            return 0
        if x == "T0":  # Combined 3&4
            return 1

    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)

        channel = self.convert_to_SRS_number_scheme(channel)

        value_orig = value
        value = ensure_float(value)

        if self.dummy:
            return value_orig
        elif not self.online:
            return "offline"

        elif self.online:
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
                channel_number = self.convert_relative_to_SRS_number_scheme(value_orig)
                w = f"DT {channel},{channel_number},{ampl_chan}"
            elif setting_X == "CHX_delay":

                self.channels_ampl[channel] = value_orig

                if channel in self.channels_relative:
                    rel_chan = self.channels_relative[channel]
                else:
                    rel_chan = "Trig"
                rel_chan = self.convert_relative_to_SRS_number_scheme(rel_chan)

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
            #
            try:
                logger.debug(f"{self.ID} writes: {w}")
                self.write(w)
                return "True"
            except Exception as e:
                self.error(
                    f"{self.ID} - An exception occurred in update_setting()",
                    exc_info=True,
                )
                return "False"

    def command(self, cmd: str):
        if self.online:
            try:
                if cmd == "single_trigger":
                    """Tells DG535 to trigger"""
                    self.write("SS")
                else:
                    logger.warning(f"{self.ID} : unknown command")
            except Exception as e:
                logger.error(
                    f"{self.ID} - An exception occurred in command()", exc_info=True
                )
        return cmd

    def write(self, cmd: str):
        try:
            if self.online and not self.dummy:
                self.device.write(cmd)
                logger.debug(f'\tSRSDG535< "{cmd}"')
        except Exception as e:
            logger.error(f"{self.ID} - An exception occurred in write", exc_info=True)

    def try_connect(self):
        if self.dummy:
            self.online = True
            return self.online

        if not self.online:
            try:
                rm = pyvisa.ResourceManager()
                self.device = rm.open_resource(self.connection_addr)  # Open connection
                logger.debug(f"Recource list pyvisa: {rm.list_resources()}")
                self.online = True
            except ValueError:
                logger.warning("Can not open this resource type.", exc_info=True)
            except Exception as e:
                # logger.error("An error occured while connecting with Pyvisa", exc_info=True)
                self.online = False

        if self.online:
            try:
                instrstat = self.device.query("IS")
                es = self.device.query("ES")
                logger.debug(
                    f"{self.ID}: Instrument status: {instrstat} \tError status: {es}"
                )
            except Exception as e:
                # logger.error("An error occured while checking online status", exc_info=True)
                self.online = False

        return self.online


#
# >>> import pyvisa
# >>> rm = pyvisa.ResourceManager()
# >>> rm.list_resources()
# ('GPIB0::10::INSTR', 'GPIB0::1::INSTR', 'TCPIP0::a-dx4054a-00879.local::hislip0::INSTR', 'TCPIP0::a-dx4054a-00879.local::inst0::INSTR', 'ASRL1::INSTR')
# >>> inst = rm.open_resource('GPIB0::10::INSTR')
# >>> inst.query("ES")
# '0\r\n'
