"""
This is a special device regarding how it handels the communication
therefore additional commentary is written.
Of this kind multiple Backends can be spawned for the same module

This specific device is an analog input module with 32 channels


"""

import time

import nidaqmx  # python wrapper for the driver

from hardware_control.HC_Backend import HC_Backend, regex_compare

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

        self.ID = "NI_DaX_PowerSupplyController"

        self.connection_addr = None
        self.online = False
        self.dummy = dummy
        self.debug = debug
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

    ###About this device:
    # there are two modules currently in use, NI 9264 and NI 9205
    # connection works over proprietary driver, with "tasks"
    # https://nidaqmx-python.readthedocs.io/en/latest/index.html for further info
    # and check the Gdocs manual!

    # ToDo
    def try_connect(self):
        if not dummy:
            self.online = True
        else:
            self.online = True
        return self.online

    def update_setting(self, setting: str, value):
        if self.dummy:
            return value
        else:
            try:

                if "CH1_V_set" == setting:
                    with nidaqmx.Task() as task:
                        task.ao_channels.add_ao_voltage_chan(self.setVoltageChannel)
                        task.write(float(value))
                        self.lastVset = value
                        time.sleep(0.200)
                        done = task.is_task_done()
                    return str(done)
                else:
                    raise Exception(self.ID + "updateSetting - Setting not found")
            except Exception as e:
                print(e)

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
        try:  # make sure tasks are done (tasks have an internal timeout)
            with nidaqmx.Task() as task:
                while not task.is_task_done():
                    print(self.ID + " : Not all Tasks are done!")
                    time.sleep(0.500)
        except Exception as e:
            raise e
