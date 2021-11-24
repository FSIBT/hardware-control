"""
.. image:: /images/NI9000.jpeg
  :height: 200

"""

import logging
import time
import os

import warnings

with warnings.catch_warnings():
    # ignore
    warnings.simplefilter("ignore", DeprecationWarning)
    import nidaqmx
    from nidaqmx.constants import TerminalConfiguration

from typing import Optional, List, Dict

from ...base import Instrument

logger = logging.getLogger(__name__)


class Ni_9000(Instrument):
    """
        Native Instruments (NI) 9000 series DAQ Module instrument class.

        NI objects require a name for the instrument, a connection address for
        the physical instrument, and a list of modules in the instrument. Each
        module contains a given number of analog and/or digital channels. These
        channels can be specified in the analog_channels and digital_channels
        dictionaries, which have module numbers as keys and a list of channel
        numbers (either analog or digital) as values. As an example, one can
        initialize an NI_9000 object like so:

        Ni_9000("Power_Supplies", connection_addr = "cDAQ1", modules = [1, 6],
        analog_channels = {1: [0, 1]}, digital_channels = {6: [6, 7]})

        Channel names consist of a module number, a signal type ('a' for analog
        and 'd' for digital), and a channel number. For example, channel number 1 on
        module number 2 with an analog signal would be 'Mod2/a-1'.

    PARAMETERS
        * CH<X>_V_MAX (*float*)
            * Maximum analog voltage for channel 'X'.
        * CH<X>_V_MIN (*float*)
            * Minimum analog voltage for channel 'X'.
        * CH<X>_TERMINAL_CONFIG (*DIFF*, *NRSE*, *RSE*)
            * Method of determining electrical potential differences for channel 'X'.
        * CH<X>_ANALOG (*float*)
            * Analog input/output value for channel 'X'.
        * CH<X>_DIGITAL (*bool*)
            * Digital input/output value for channel 'X'

    COMMANDS
        * DISPLAY_CONFIGURATION
            * Log terminal configurations, voltage maxima, and voltage minima for each channel.
    """

    def __init__(
        self,
        instrument_name: str = "NI_9000",
        connection_addr: str = "",
        modules: Optional[List] = None,
        analog_channels: Optional[Dict] = None,
        digital_channels: Optional[Dict] = None,
    ):

        # A default port is required for this instrument
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=0,
        )

        # Numeric list of all modules
        self.modules = modules if modules is not None else [1]
        # Numeric lists of all analog and digital channels
        self.analog_channels = analog_channels if analog_channels is not None else {}
        self.digital_channels = digital_channels if digital_channels is not None else {}

        # Dictionaries for storing parameter values for each channel
        self.term_config_modes = {
            "DIFF": TerminalConfiguration.DIFFERENTIAL,
            "NRSE": TerminalConfiguration.NRSE,
            "RSE": TerminalConfiguration.RSE,
        }
        self.channel_term_configs = {}
        self.V_mins = {}
        self.V_maxes = {}

        # Initialize parameters on all requested channels
        for mod in self.modules:
            if self.analog_channels.get(mod) is not None:
                for chan in self.analog_channels[mod]:
                    self._initialize_params(mod, chan, "a")
            if self.digital_channels.get(mod) is not None:
                for chan in self.digital_channels[mod]:
                    self._initialize_params(mod, chan, "d")

        self.add_command("DISPLAY_CONFIGURATION", self._display_configuration)

    def _initialize_params(self, module_num, channel, signal_type):
        channel_string = f"Mod{module_num}/{signal_type}{channel}"
        self.add_parameter(
            f"CH{channel_string}_V_MAX",
            read_command=lambda: self._read_V_max(channel_string),
            set_command=lambda value: self._set_V_max(channel_string, value),
            dummy_return="20.",
        )

        self.add_parameter(
            f"CH{channel_string}_V_MIN",
            read_command=lambda: self._read_V_min(channel_string),
            set_command=lambda value: self._set_V_min(channel_string, value),
            dummy_return="0.",
        )

        self.add_parameter(
            f"CH{channel_string}_TERMINAL_CONFIG",
            read_command=self._read_term_config(channel_string),
            set_command=self._set_term_config(channel_string),
            dummy_return="DIFF",
        )

        self.channel_term_configs[channel_string] = "DIFF"

        if signal_type == "a":
            if channel[0] == "i":
                read_command = lambda: self._analog_read(channel_string)
                set_command = None
            elif channel[0] == "o":
                read_command = None
                set_command = lambda value: self._analog_write(channel_string, value)
            else:
                logger.error(
                    f"The channel '{channel}' of port '{channel_string}' must start with either an 'i' (input) or 'o' (output)."
                )
                return

            self.add_parameter(
                f"CH{channel_string}_ANALOG",
                read_command=read_command,
                set_command=set_command,
                dummy_return="10.",
            )

        elif signal_type == "d":
            logger.warning(
                "The NI_9000 driver's digital functionality remains untested. Proceed with caution."
            )
            if channel[0] == "i":
                read_command = lambda: self._digital_read(channel_string)
                set_command = None
            elif channel[0] == "o":
                read_command = None
                set_command = lambda value: self._digital_write(channel_string, value)
            else:
                logger.error(
                    f"The channel '{channel}' of port '{channel_string}' must start with either an 'i' (input) or 'o' (output)."
                )
                return

            self.add_parameter(
                f"CH{channel_string}_DIGITAL",
                read_command=read_command,
                set_command=set_command,
                dummy_return="True",
            )

        else:
            logger.error(
                f"The signal type '{signal_type}' of port '{channel_string}' must be either 'a' (analog) or 'd' (digital)."
            )

    def _set_V_max(self, channel_string, value):
        self.V_maxs[channel_string] = float(value)

    def _set_V_min(self, channel_string, value):
        self.V_mins[channel_string] = float(value)

    def _read_V_max(self, channel_string):
        return self.V_maxs[channel_string]

    def _read_V_min(self, channel_string):
        return self.V_mins[channel_string]

    def _read_term_config(self, channel_string):
        def _read_term_config_value():
            return self.channel_term_configs[channel_string]

        return _read_term_config_value

    def _set_term_config(self, channel_string):
        def _set_term_config_value(value):
            self.channel_term_configs[channel_string] = value

        return _set_term_config_value

    def try_connect(self):
        if not self._dummy and os.name == "nt":
            try:
                with nidaqmx.Task() as task:
                    if task.name:
                        self._online = True
            except nidaqmx.errors.DaqError:
                self._online = False
                logger.error(
                    "Connection failed due to DaqError."
                    " This could mean the NIDAQ must be reserved"
                    " in NI-Max Application."
                )
            except Exception:
                self._online = False
                logger.error("Connect failed.", exc_info=True)
        else:
            self._online = True
        return self._online

    def _analog_write(self, channel_string, value):
        with nidaqmx.Task() as task:
            channel_min = self.V_mins.get(channel_string, -10)
            channel_max = self.V_maxes.get(channel_string, 10)

            task.ao_channels.add_ao_voltage_chan(
                f"{self.connection_addr}{channel_string}",
                min_val=channel_min,
                max_val=channel_max,
            )

            task.write(value)
            time.sleep(0.010)
            task.is_task_done()

    def _analog_read(self, channel_string):
        with nidaqmx.Task() as task:
            if channel_string in self.term_config_modes:
                config_mode = self.term_config_modes[
                    self.channel_term_configs[channel_string]
                ]
                task.ai_channels.add_ai_voltage_chan(
                    physical_channel=f"{self.connection_addr}{channel_string}",
                    terminal_config=config_mode,
                )
            else:
                task.ai_channels.add_ai_voltage_chan(
                    f"{self.connection_addr}{channel_string}"
                )
            value = str(task.read())

        return value

    def _digital_write(self, channel_string, value):
        with nidaqmx.Task() as task:
            task.ao_channels.add_do_chan(f"{self.connection_addr}{channel_string}")
            task.write(value)
            time.sleep(0.010)
            task.is_task_done()

    def _digital_read(self, channel_string):
        with nidaqmx.Task() as task:
            task.ai_channels.add_di_chan(f"{self.connection_addr}{channel_string}")
            value = str(task.read())

        return value

    def _display_configuration(self):
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
