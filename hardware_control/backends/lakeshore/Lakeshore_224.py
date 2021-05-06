"""
Control class to handle Lake shore 224 Temperature Monitor for Temp readouts.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with Lakeshore models 224
connection works over proprietary driver, with "tasks"
https://www.lakeshore.com/docs/default-source/product-downloads/224_manual.pdf for the manual


"""

import logging
import random

from ..base import Backend, ensure_online
from ..utility import ensure_float, get_channel_from_command

logger = logging.getLogger(__name__)


class Lakeshore_224(Backend):
    """
    A driver for the Lakeshore 224 Temp Monitor
    Instrument home page:
    https://www.lakeshore.com/products/categories/overview/temperature-products/cryogenic-temperature-monitors/model-224-temperature-monitor
    """

    def __init__(
        self,
        connection_addr: str,
    ):
        super().__init__(
            instrument_name="Lakeshore_224",
            connection_addr=connection_addr,
            default_port=7777,
        )
        self.num_channels = 12
        self.check_connection_commands = "*IDN?"
        self.active_channels = [
            "A",
            "B",
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",
        ]
        self.termination = "\r\n"
        # self.read_termination = '\r\n'
        # self.write_termination ='\n'

    def update_setting(self, setting: str, value):
        """
        Changes a specified setting to the specied value

        Parameters
        ----------
        setting : str
            Setting to change

        Notes
        --------
        Available settings (<X> indicates a number, values in parethesis show acceptable values):

        * CH<X>_CHANGE_CURVE: select calibration curve for channel X
        """

        channel, setting_X = get_channel_from_command(setting)
        value_original = value
        value = ensure_float(value)

        logger.info(
            f"Lakeshore u_s received {setting}, {value} and interpreted chan={channel}, setting_X={setting_X}, value={value}"
        )

        # These settings return valid values even in dummy mode or while offline.
        # That's why we check for self.online after these if-statements

        if not self.online:
            logger.info("Lakeshore")
            return f"{self.ID}-Offline"

        if self.dummy:
            return f"{setting}={value}"

        if setting_X == "CHX_CHANGE_CURVE":
            if value_original == 0:
                self.query(f"INCRV {channel} 0")
                self.active_channels.remove(channel)
                return f"{channel} is OFF"
            else:
                self.query(f"INCRV {channel} {value}")
                self.active_channels.append(channel)

                if self.read_status()["CURVE"] == value:
                    # remove dupilicate item in channal list
                    self.active_channels = list(set(self.active_channels))
                    return f"{channel} is using curve {value}"

                elif self.read_status()["CURVE"] == "00":
                    # remove this channel from active channel list
                    self.active_channels.remove(channel)
                    raise Exception(f"{channel} is not using any curve")

                else:
                    raise Exception(f"setting curve {value} to {channel} is failure")

        if setting_X == "CHX_CHANGE_NAME":
            if value_original == 0:
                self.query(f"INNAME {channel} {channel}")
                return f"{channel} is named as default"
            else:
                self.query(f"INCRV {channel} {value}")
                return f"{channel} is named {value}"

    def command(self, cmd: str):
        """
        Executes an action specified by 'cmd'.

        Parameters
        ----------
        cmd
            Name of command to execute

        Notes
        -----
        CHX_READ_TEMP:  Read the temperature for channel [A, B, C1-C5, D1-D5], 0 is all online channels
        """
        channel, cmd_X = get_channel_from_command(cmd)

        if cmd_X == "CHX_READ_TEMP":
            temps = {}
            if channel == 0:
                for chan in self.active_channels:
                    temp = self.query(f"KRDG? {chan}")
                    temps[f"{chan}"] = f"{temp}"

            elif channel in self.active_channels:
                temp = self.query(f"KRDG? {channel}")
                temps[f"{channel}"] = f"{temp}"

            else:
                raise Exception(f"Sorry, channel {channel} is Offline")

            return temps

    def read_status(self, channel):
        """
        Read all settings of the instrument

        Parameters
        ----------
        setting : str
            Setting to change
        """
        if self.dummy:
            outputs = [1 + 128 + 1024, 128, 1, 1024]
            value = random.choice(outputs)
        else:
            status = {}
            status["CURVE"] = self.query(f"INCRV? {channel}")
            status["NAME"] = self.query(f"INNAME? {channel}")

        return status
