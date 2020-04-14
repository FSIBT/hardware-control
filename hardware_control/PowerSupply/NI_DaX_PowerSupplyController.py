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

from hardware_control.HC_Backend import HC_Backend
from hardware_control.utility import regex_compare
import logging

logger = logging.getLogger(__name__)

"""This class behaves like it would read from a Powersupply"""


class NI_DaX_PowerSupplyController(HC_Backend):
    def __init__(
        self,
        setVoltageChannel: str = "cDaQ1Mod1/ao10",
        readVoltageChannel: str = "cDaQ1Mod2/ai20",
        readCurrentChannel: str = "cDaQ1Mod2/ai20",
    ):

        super().__init__()
        self.num_channels = 1

        self.ID = "NI_DaX_PowerSupplyController"

        self.connection_addr = None
        self.online = False
        self.dummy = False
        #
        self.setVoltageChannel = setVoltageChannel
        self.readVoltageChannel = readVoltageChannel
        self.readCurrentChannel = readCurrentChannel
        # Check if channels are in expected format
        if not (
            regex_compare(".+/ao.+", self.setVoltageChannel)
            and regex_compare(".+/ai.+", self.readCurrentChannel)
            and regex_compare(".+/ai.+", self.readVoltageChannel)
        ):
            raise Exception(self.ID + " : Unexpected Channel name")

        # these are the conversion Factors for the Voltage settings / readouts
        self.convSetVoltage = 1
        self.convReadVoltage = 1
        self.convReadCurrent = 1

        self.lastVset = 0

        # Check import
        if not nidaxmxTest():
            self.dummy = True
            logger.error(f"{self.ID}: import of nidaqmx failed, changing to dummy mode")

    ###About this device:
    # there are two modules currently in use, NI 9264 and NI 9205
    # connection works over proprietary driver, with "tasks"
    # https://nidaqmx-python.readthedocs.io/en/latest/index.html for further info
    # and check the Gdocs manual!

    # ToDo Rework this
    def try_connect(self):
        if not self.dummy and os.name == "nt":
            try:
                with nidaqmx.Task() as task:
                    if task.name:
                        self.online = True
            except Exception as e:
                logger.error("Connect failed.", exc_info=True)
                return False
        else:
            self.online = True
        return self.online

    def update_setting(self, setting: str, value):
        if self.dummy:
            return value
        elif self.online:
            try:
                if "CH1_V_set" == setting:
                    with nidaqmx.Task() as task:
                        task.ao_channels.add_ao_voltage_chan(self.setVoltageChannel)
                        task.write(float(value))
                        self.lastVset = value
                        time.sleep(0.200)
                        done = task.is_task_done()
                    return str(done)
                elif "CH1_I_set" == setting:
                    return "False"
                else:
                    raise Exception(self.ID + "updateSetting - Setting not found")
            except Exception as e:
                logger.error("Failed to update setting.", exc_info=True)
        else:
            return "False"

    def command(self, cmd: str):

        if not self.online:
            return "Offline"

        try:

            if self.dummy:
                num = random.random() * 10
                return f"{cmd.strip('?')}={num}"

            if "CH1_V_out?" == cmd:
                with nidaqmx.Task() as task:
                    task.ai_channels.add_ai_voltage_chan(self.readVoltageChannel)
                    val = str(task.read())
                return cmd[:-1] + "=" + str(val[0])
            elif "CH1_I_out?" == cmd:
                with nidaqmx.Task() as task:
                    task.ai_channels.add_ai_voltage_chan(self.readCurrentChannel)
                    val = str(task.read())
                return cmd[:-1] + "=" + str(val[0])
            elif "CH1_V_set?" == cmd:
                return cmd[:-1] + "=" + str(self.lastVset)
            elif "CH1_I_set?" == cmd:
                return cmd[:-1] + "=" + "0"
            else:
                raise Exception(self.ID + "unknown Command : ", cmd)
        except Exception as e:
            logger.error("Failed to execute command. ", exc_info=True)

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
        except Exception as e:
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
