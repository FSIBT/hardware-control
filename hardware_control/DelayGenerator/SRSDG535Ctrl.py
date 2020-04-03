"""
The manual for this instrument can be found at

 https://www.thinksrs.com/downloads/pdfs/manuals/DG535m.pdf page 9ff

"""
import socket
import os
import pyvisa

from hardware_control.HC_Backend import HC_Backend
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

    def update_setting(self, setting: str, value):
        if self.dummy:
            return value
        elif not self.online:
            return "offline"
        elif self.online:
            if setting == "trigger_mode":
                mode = 0
                if value == "Internal":
                    mode = 0
                elif value == "External":
                    mode = 1
                elif value == "Single":
                    mode = 2
                elif value == "Burst":
                    mode = 3
                w = f"TM{mode}"
            elif setting == "trigger_edge":
                mode = 0
                if value == "Positive":
                    mode = 1
                elif value == "Negative":
                    mode = 0
                w = f"TS{mode}"
            elif setting == "ext_trig_Zin":
                mode = 0
                if value == "50 Ohms":
                    mode = 0
                elif value == "Hi-Z":
                    mode = 1
                w = f"TZ{mode}"
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
                    self.write(self.command_str)
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
