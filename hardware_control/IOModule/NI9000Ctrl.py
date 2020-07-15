"""
This is a special device regarding how it handels the communication
therefore additional commentary is written.
Of this kind multiple Backends can be spawned for the same module

This specific device is an analog input module with 32 channels

There were some problems with the import of nidaqmx an try_connect,
therefore it is written with reliability in mind. But it is only
partially tested. Some statements might be unnecessary.
NI-DaQ's will not work on Unix based OS.
"""

import random
import time
from colorama import Fore, Style
import os

# import nidaqmx happens in a method below, which reports the status

from colorama import Fore, Style

if os.name == "nt":
    import nidaqmx
    from nidaqmx.constants import TerminalConfiguration

from hardware_control.HC_Backend import HC_Backend
from hardware_control.utility import get_channel_from_command
import logging
from hardware_control.utility import ensure_float

logger = logging.getLogger(__name__)

"""This class behaves like it would read from a Powersupply"""


class NI9000Ctrl(HC_Backend):
    def __init__(self, connection_addr: str):

        super().__init__()
        self.num_channels = 1

        self.ID = "NI-9000"
        self.max_V = [5] * 22

        self.connection_addr = connection_addr
        self.parse_connection_addr()

        self.online = False
        self.dummy = False

        self.num_channels = 22

        self.term_config_modes = {}

        self.channel_data = None

        # # Check if channels are in expected format
        # if not (
        #     regex_compare(".+/ao.+", self.setVoltageChannel)
        #     and regex_compare(".+/ai.+", self.readCurrentChannel)
        #     and regex_compare(".+/ai.+", self.readVoltageChannel)
        # ):
        #     raise Exception(self.ID + " : Unexpected Channel name")

        # these are the conversion Factors for the Voltage settings / readouts
        # self.convSetVoltage = 1
        # self.convReadVoltage = 1
        # self.convReadCurrent = 1
        #
        # self.lastVset = 0

        # Check import
        if not nidaxmxTest():
            self.dummy = True
            logger.error(f"{self.ID}: import of nidaqmx failed, changing to dummy mode")

    ###About this device:
    # Has been tested with models NI 9264 and NI 9205
    # connection works over proprietary driver, with "tasks"
    # https://nidaqmx-python.readthedocs.io/en/latest/index.html for further info
    # and check the Gdocs manual!

    # TODO: Rework this
    def try_connect(self):
        if not self.dummy and os.name == "nt":
            try:
                with nidaqmx.Task() as task:
                    if task.name:
                        self.online = True
            except Exception as e:
                self.online = False
                logger.error("Connect failed.", exc_info=True)
        else:
            self.online = True
        return self.online

    def init_channels(self):

        print(f"IC: {self.online}\t\t{str(self)}")

        if self.channel_data == None:
            print("RETURRNING NONE")
            return

        for c in self.channel_data:

            chan = self.channel_data[c]

            if "OPTIONS" in chan and chan["OPTIONS"] is not None:
                if "DIFF" in chan["OPTIONS"]:
                    print("\tDIFF")
                    name = chan["ID_STR"]
                    self.update_setting(f"CH{name}_terminal_config", "DIFF")
                elif "NRSE" in chan["OPTIONS"]:
                    print("\tNRSE")
                    name = chan["ID_STR"]
                    self.update_setting(f"CH{name}_terminal_config", "DIFF")
                elif "RSE" in chan["OPTIONS"]:
                    print("\tRSE")
                    name = chan["ID_STR"]
                    self.update_setting(f"CH{name}_terminal_config", "DIFF")

    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)

        value_orig = value
        value = ensure_float(value)

        if setting_X == "CHX_V_max":
            self.max_V[channel - 1] = value
            return str(value)

        if not self.online:
            return "Offline"

        if self.dummy:
            return str(value)

        try:
            if setting_X == "CHX_analog_write":

                with nidaqmx.Task() as task:
                    task.ao_channels.add_ao_voltage_chan(channel)
                    task.write(value)
                    time.sleep(0.010)
                    done = task.is_task_done()

            if setting_X == "CHX_digital_write":

                with nidaqmx.Task() as task:
                    task.ao_channels.add_do_chan(channel)
                    task.write(value >= 1)
                    time.sleep(0.010)
                    done = task.is_task_done()
                return str(done)

            if setting_X == "CHX_terminal_config":

                if value == "DIFF":
                    config_mode = TerminalConfiguration.DIFFERENTIAL
                elif value == "NRSE":
                    config_mode = TerminalConfiguration.NRSE
                else:
                    config_mode = TerminalConfiguration.RSE

                self.term_config_modes[channel] = config_mode

                print(f"\tSet TC for {channel} to {value}")

                return str(value)

            print(f"Unrecognized command {setting_X}, {channel}, {value}")

        except:
            logger.error("Error occured in NI9000 command.", exc_info=True)

    def command(self, cmd: str):

        channel, setting_X = get_channel_from_command(cmd)

        if not self.online:
            return "Offline"

        if self.dummy:
            num = random.random() * 10
            return f"{cmd.strip('?')}={num}"

        try:
            if "CHX_analog_read?" == setting_X:

                with nidaqmx.Task() as task:
                    # if channel in self.term_config_modes:
                    # config_mode = self.term_config_modes[channel]
                    config_mode = TerminalConfiguration.DIFFERENTIAL
                    task.ai_channels.add_ai_voltage_chan(
                        channel, terminal_config=config_mode
                    )
                    # print("USING MODE")
                    # else:
                    #     task.ai_channels.add_ai_voltage_chan(channel)
                    #     print("Not using mode")
                    val = str(task.read())
                return cmd[:-1] + "=" + str(val)
            if "CHX_digital_read?" == setting_X:

                with nidaqmx.Task() as task:
                    task.ai_channels.add_di_chan(channel)
                    val = str(task.read())
                return cmd[:-1] + "=" + str(val)

            if "INIT_CHANNELS" == cmd:

                print("IC From COmmand")

                self.init_channels()

        except:
            logger.error("Error occured in NI9000 command.", exc_info=True)

    def close(self):
        if self.online and not self.dummy:
            try:  # make sure tasks are done (tasks have an internal timeout)
                with nidaqmx.Task() as task:
                    if not task.is_task_done():
                        time.sleep(0.500)
                        if not ask.is_task_done():
                            return True
            except Exception as e:
                logger.error(f"An error occured while trying to close.", exc_info=True)
        return False


"""
This method checks that the import goes smooth and
reports that so that all functionality can ether be disabled or
further checks can happen.
"""


def nidaxmxTest():
    if os.name == "nt":
        try:
            with nidaqmx.Task() as task:
                if task.name:
                    return True
            return True
        except Exception:
            print(
                Fore.RED
                + "WARNING: Can not acsess NIDAQMX on this system. NIDAQ will not function"
                + Style.RESET_ALL
            )
            return False
        # We check which OS is calling because nidaqmx only works on Windows. Importing
        # nidaqmx on macOS or linux will cause pyvisa and sockets to break.
    else:
        print(
            Fore.RED
            + "WARNING: Can not acsess NIDAQMX on this system. NIDAQ will not function"
            + Style.RESET_ALL
        )
    return False
