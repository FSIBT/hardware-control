"""
Control class to handle Granville Phillips 356 Series Ion gauge for preesure readout.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with GP356 Ion gauge
connection works over proprietary driver, with "tasks"
"""

import logging
import random

import numpy as np

from ..base import Backend, ensure_online
from ..utility import ensure_float, get_channel_from_command

logger = logging.getLogger(__name__)


class GP_356(Backend):
    """
    A driver for the Grandville Phillips Ion Gauge
    """

    def __init__(
        self,
        connection_addr: str,
    ):
        super().__init__(
            instrument_name="GrandvillePhillips_356",
            connection_addr=connection_addr,
            default_port=7777,
        )
        self.ins_add = "#02"  # The address setting on the instrument
        self.check_connection_commands = (
            self.ins_add + "IGS"
        )  # different command for connection checking

        # self.termination = "\r"
        self.read_termination = "\r"
        self.write_termination = "\r"

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
            logger.info("GrandvillePhillips")
            return f"{self.ID}-Offline"

        if self.dummy:
            return f"{setting}={value}"

        if setting_X == "RD":
            self.query(f"{self.ins_add}RD")

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
        CHX_READ_PRS:  Read the temperature for channel [A, B, C1-C5, D1-D5], 0 is all online channels
        """

        if self.dummy:
            return f"{cmd[:-1]}={np.random.uniform()*100}"

        channel, cmd_X = get_channel_from_command(cmd)
        print("debug", cmd, cmd_X, channel)

        if cmd_X == "CHX_READ_PRS?":

            prs = self.query(f"{self.ins_add}RD")
            self.write(f"Pressure: {prs}")

            return prs

        if cmd_X == "CHX_READ_REC?":

            REC = self.query(f"{self.ins_add}RE")
            self.write(f"Pressure: {REC}")

            return REC

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
            status["PRS"] = self.query(f"{self.ins_add}RD")
            status["STS"] = self.query(f"{self.ins_add}IGS")
            status["Fliment"] = self.query(f"{self.ins_add}RF")

        return status
