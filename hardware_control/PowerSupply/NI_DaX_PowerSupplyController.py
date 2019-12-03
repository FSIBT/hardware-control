"""
This is a special device regarding how it handels the communication
therefore additional commentary is written.
Of this kind multiple Backends can be spawned for the same module

This specific device is an analog input module with 32 channels


"""

import pyvisa
from typing import List
import numpy as np
import socket
from hardware_control.HC_Backend import HC_Backend, returnChannelNumber, regex_compare
import re
import random
import nidaqmx  #python wrapper for the driver
import time



"""This class behaves like it would read from a Powersupply"""
class NI_DaX_PowerSupplyController(HC_Backend):
    def __init__(
        self,
        setVoltageChannel: str,
        readVoltageChannel: str,
        readCurrentChannel: str,
        dummy: bool = False,
        debug: bool = False,
    ):

        super().__init__()

        self.ID = "NI_DaX_PowerSupp"

        self.visa_addr = visa_addr
        self.online = False
        self.dummy = dummy
        self.debug = debug

        self.setVoltageChannel = setVoltageChannel
        self.readVoltageChannel =readVoltageChannel
        self.readCurrentChannel= readCurrentChannel
        #TODO make shure channels are in the right format

        #ToDo add conversion factors

        self.lastVset = 0

###About this device:
    # there are two modules currently in use, NI 9264 and NI 9205
    # connection works over proprietary driver, with "tasks"
    # https://nidaqmx-python.readthedocs.io/en/latest/index.html for further info
    # and check the Gdocs manual

    #ToDo test if this works as it should - done by guessing
    def try_connect(self):
         if not dummy:

         else:
             self.online=True
         return self.online

    

    #needs to be implemented!
    def update_setting(self, setting: str, value):
        if self.dummy:
            return value
        else:
            try:

                if "CH1_V_set"==setting or:
                    with nidaqmx.Task() as task:
                        task.ao_channels.add_ao_voltage_chan(self.setVoltageChannel)
                        task.write(float(value))
                        self.lastVset= value
                        time.sleep(.200)
                        done = task.is_task_done()
                    return str(done)
                else:
                    raise Exception(self.ID + "updateSetting - Setting not found")
            except Exception as e:
                print(e)

    # needs to be implemented
    def command(self, cmd: str):
        if self.dummy:
            return cmd
        else:
            try:
                if "CH1_V_out?" == cmd:
                    with nidaqmx.Task() as task:
                        task.ai_channels.add_ai_voltage_chan(self.readVoltageChannel)
                        val = task.read()
                    return val[0]
                if "CH1_I_out?" == cmd:
                    with nidaqmx.Task() as task:
                        task.ai_channels.add_ai_voltage_chan(self.readCurrentChannel)
                        val = task.read()
                    return val[0]
                elif "CH1_V_set?" == cmd:
                    return self.lastVset
                else:
                    raise Exception(self.ID + "unknown Command")
            except Exception as e:
                print(e)

    def close(self):
        try:  # make sure connection is closed
            self.task.close()
        except:
            pass