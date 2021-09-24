"""
Control class to handle NI Daq modules for analog voltage input and outputs.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with models NI 9264 and NI 9205
connection works over proprietary driver, with "tasks"
https://nidaqmx-python.readthedocs.io/en/latest/index.html for further info
and check the Gdocs manual!

"""

import logging
import os
import random
import time
from nidaqmx.constants import TerminalConfiguration

from ...base import Instrument
from ..utility import ensure_float

logger = logging.getLogger(__name__)


class Ni_9000(Instrument):
    def __init__(self, instrument_name: str = "NI-9000", connection_addr: str = ""):

        # need to set a default port for this instrument
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=0,
        )

        # NEED TO FIGURE OUT HOW MANY MODs AND AIs ARE PRESENT IN Instrument
        # THIS SCRIPT IS CURRENTLY BROKEN
        # Numeric list of all modules
        self.n_mods = list(range(1, 3))
        # Numeric list of all channels (analog input, analog output, digital input, digital output)
        self.n_analogs = list(range(0, 6))
        self.n_digitals = list(range(0, 6))

        self.term_config_modes = {}
        self.V_mins = {}
        self.V_maxes = {}

        for mod in self.n_mods:
            for chan in self.n_analogs:
                self.initialize_params(mod, chan, "a")
            for chan in self.n_digitals:
                self.initialize_params(mod, chan, "d")

        self.add_command("DISPLAY_CONFIGURATION", lambda: self.display_configuration())

    def initialize_params(self, module_num, chan_num, signal_type):
        channel = f"Mod{module_num}/{signal_type}-{chan_num}"
        self.add_parameter(
            f"CH{channel}_V_MAX",
            read_command=None,
            set_command=lambda x: self.set_V_max(channel, x),
            dummy_return="20",
        )

        self.add_parameter(
            f"CH{channel}_V_MIN",
            read_command=None,
            set_command=lambda x: self.set_V_min(channel, x),
            dummy_return="0",
        )

        self.add_parameter(
            f"CH{channel}_TERMINAL_CONFIG",
            read_command=None,
            set_command=lambda x: self.set_term_config(channel, x),
            dummy_return="DIFF",
        )
        self.add_lookup(
            f"CH{channel}_TERMINAL_CONFIG",
            {
                "DIFF": TerminalConfiguration.DIFFERENTIAL,
                "NRSE": TerminalConfiguration.NRSE,
                "RSE": TerminalConfiguration.RSE,
            },
        )

        if signal_type == "a":
            self.add_parameter(
                f"CH{channel}_ANALOG",
                read_command=lambda value: self.analog_read(channel),
                set_command=lambda value: self.analog_write(channel, value),
                dummy_return="10",
            )

        elif signal_type == "d":
            self.add_parameter(
                f"CH{channel}_DIGITAL",
                read_command=lambda value: self.digital_read(channel),
                set_command=lambda value: self.digital_write(channel, value),
                dummy_return="True",
            )

    def set_V_max(self, channel, value):
        self.V_maxs[channel] = float(value)

    def set_V_min(self, channel, value):
        self.V_mins[channel] = float(value)

    def set_term_config(self, channel, value):
        self.term_config_modes[channel] = value

    def analog_write(self, channel, value):
        with nidaqmx.Task() as task:
            channel_min = self.V_mins.get(channel, -10)
            channel_max = self.V_maxes.get(channel, 10)

            task.ao_channels.add_ao_voltage_chan(
                f"{self.connection_addr}{channel.replace('-', 'o')}",
                min_val=channel_min,
                max_val=channel_max,
            )
            task.write(value)
            time.sleep(0.010)
            task.is_task_done()

    def analog_read(self, channel):
        with nidaqmx.Task() as task:
            if channel in self.term_config_modes:
                config_mode = self.term_config_modes[channel]
                task.ai_channels.add_ai_voltage_chan(
                    f"{self.connection_addr}{channel.replace('-', 'i')}",
                    terminal_config=config_mode,
                )
            else:
                task.ai_channels.add_ai_voltage_chan(f"{self.connection_addr}{channel}")
            value = str(task.read())

        return value

    def digital_write(self, channel, value):
        with nidaqmx.Task() as task:
            task.ao_channels.add_do_chan(
                f"{self.connection_addr}{channel.replace('-', 'o')}"
            )
            task.write(value)
            time.sleep(0.010)
            task.is_task_done()

    def digital_read(self, channel):
        with nidaqmx.Task() as task:
            task.ai_channels.add_di_chan(
                f"{self.connection_addr}{channel.replace('-', 'i')}"
            )
            value = str(task.read())

        return value

    def display_configuration():
        logger.info(f"--------- Configuration for {self.ID} ---------")
        logger.info("Terminal Configurations:")
        for key in self.term_config_modes:
            val = self.term_config_modes[key]
            logger.info(f"\t{key}:{val}")
        logger.info("Minima:")
        for key in self.term_mins:
            val = self.term_mins[key]
            logger.info(f"\t{key}:{val}")
        logger.info("Maxima:")
        for key in self.term_maxes:
            val = self.term_maxes[key]
            logger.info(f"\t{key}:{val}")
        return
