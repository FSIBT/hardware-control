"""
Control class to handle NI Daq modules for analog voltage input and outputs.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with models NI 9264 and NI 9205
connection works over proprietary driver, with "tasks"
https://nidaqmx-python.readthedocs.io/en/latest/index.html for further info
and check the Gdocs manual!

NI-DaQ's will curently not work on Unix based OS.

"""

import logging
import os
import random
import time

# import nidaqmx happens in a method below, which reports the status

if os.name == "nt":
    import nidaqmx
from nidaqmx.constants import TerminalConfiguration

from ..base import Backend
from ..utility import get_channel_from_command, ensure_float

logger = logging.getLogger(__name__)


class Ni_9000(Backend):
    def __init__(self, connection_addr: str = ""):

        # need to set a default port for this instrument
        super().__init__(
            instrument_name="NI-9000", connection_addr=connection_addr, default_port=0
        )

        self.num_channels = 1
        self.num_channels = 22

        self.term_config_modes = {}
        self.term_mins = {}
        self.term_maxes = {}

        self.channel_data = None

        # Check import
        if not nidaxmxTest():
            self.dummy = True
            logger.error(f"{self.ID}: import of nidaqmx failed, changing to dummy mode")

    def try_connect(self):
        if not self.dummy and os.name == "nt":
            try:
                with nidaqmx.Task() as task:
                    if task.name:
                        self.online = True
            except nidaqmx.errors.DaqError:
                self.online = False
                logger.error(
                    "Connection failed due to DaqError."
                    " This could mean the NIDAQ must be reserved"
                    " in NI-Max Application."
                )
            except Exception:
                self.online = False
                logger.error("Connect failed.", exc_info=True)
        else:
            self.online = True
        return self.online

    def update_setting(self, setting: str, value):

        channel, setting_X = get_channel_from_command(setting)

        value_orig = value
        value = ensure_float(value)

        if setting_X == "CHX_V_MAX":

            if not isinstance(value, float):
                logger.warning(
                    f"Failed to set CH{channel} V Max to '{value_orig}'."
                    f" Failed to convert to float"
                )

            self.term_maxes[channel] = value
            return f"{setting}={value_orig}"
        if setting_X == "CHX_V_MIN":

            if not isinstance(value, float):
                logger.warning(
                    f"Failed to set CH{channel} V Min to '{value_orig}'."
                    f" Failed to convert to float"
                )

            self.term_mins[channel] = value
            return f"{setting}={value_orig}"
        if setting_X == "CHX_TERMINAL_CONFIG":

            if value_orig == "DIFF":
                config_mode = TerminalConfiguration.DIFFERENTIAL
            elif value_orig == "NRSE":
                config_mode = TerminalConfiguration.NRSE
            else:
                config_mode = TerminalConfiguration.RSE

            self.term_config_modes[channel] = config_mode

            return f"{setting}={value_orig}"

        if not self.online:
            return f"{self.ID}-Offline"

        if self.dummy:
            return f"{setting}={value_orig}"

        try:
            if setting_X == "CHX_ANALOG_WRITE":

                with nidaqmx.Task() as task:
                    if channel in self.term_mins and isinstance(
                        self.term_mins[channel], float
                    ):
                        channel_min = self.term_mins[channel]
                    else:
                        channel_min = -10.0
                    if channel in self.term_maxes and isinstance(
                        self.term_maxes[channel], float
                    ):
                        channel_max = self.term_maxes[channel]
                    else:
                        channel_max = 10.0
                    task.ao_channels.add_ao_voltage_chan(
                        channel, min_val=channel_min, max_val=channel_max
                    )
                    task.write(value)
                    time.sleep(0.010)
                    task.is_task_done()
                    return

            if setting_X == "CHX_DIGITAL_WRITE":

                with nidaqmx.Task() as task:
                    task.ao_channels.add_do_chan(channel)
                    task.write(value >= 1)
                    time.sleep(0.010)
                    task.is_task_done()
                    return
        except:
            logger.error("Error occured in NI9000 command.", exc_info=True)

    def command(self, cmd: str):

        channel, setting_X = get_channel_from_command(cmd)

        if setting_X == "DISPLAY_CONFIGURATION":
            print(f"--------- Configuration for {self.ID} ---------")
            print("Terminal Configurations:")
            for key in self.term_config_modes:
                val = self.term_config_modes[key]
                print(f"\t{key}:{val}")
            print("Minima:")
            for key in self.term_mins:
                val = self.term_mins[key]
                print(f"\t{key}:{val}")
            print("Maxima:")
            for key in self.term_maxes:
                val = self.term_maxes[key]
                print(f"\t{key}:{val}")
            return
        if self.dummy:
            num = random.random() * 10
            return f"{cmd.strip('?')}={num}"

        try:
            if setting_X == "CHX_ANALOG_READ?":
                with nidaqmx.Task() as task:
                    if channel in self.term_config_modes:
                        config_mode = self.term_config_modes[channel]
                        task.ai_channels.add_ai_voltage_chan(
                            channel, terminal_config=config_mode
                        )
                    else:
                        task.ai_channels.add_ai_voltage_chan(channel)
                    val = str(task.read())
                return f"{cmd[:-1]}={val}"
            if setting_X == "CHX_DIGITAL_READ?":
                with nidaqmx.Task() as task:
                    task.ai_channels.add_di_chan(channel)
                    val = str(task.read())
                return f"{cmd[:-1]}={val}"
        except:
            logger.error("Error occured in NI9000 command.", exc_info=True)

    def close(self):
        if self.online and not self.dummy:
            try:  # make sure tasks are done (tasks have an internal timeout)
                with nidaqmx.Task() as task:
                    if not task.is_task_done():
                        time.sleep(0.500)
                        if not task.is_task_done():
                            return True
            except Exception:
                logger.error("An error occured while trying to close.", exc_info=True)
        return False


def nidaxmxTest():
    """This method checks that the import goes smooth and reports that so
    that all functionality can ether be disabled or further checks can
    happen.

    """

    # We check which OS is calling because nidaqmx only works on
    # Windows. Importing nidaqmx on macOS or linux will cause pyvisa
    # and sockets to break.

    if os.name == "nt":
        try:
            with nidaqmx.Task() as task:
                if task.name:
                    return True
            return True
        except Exception:
            logger.error(
                "WARNING: Can not acsess NIDAQMX on this system. NIDAQ will not function"
            )
            return False
    else:
        logger.error(
            "WARNING: Can not acsess NIDAQMX on this system. NIDAQ will not function"
        )

    return False
