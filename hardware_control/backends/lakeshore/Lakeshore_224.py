"""
Control class to handle Lake shore 224 Temperature Monitor for Temp readouts.

.. image:: /images/NI9000.jpeg
  :height: 200

Has been tested with Lakeshore models 224
connection works over proprietary driver, with "tasks"
https://www.lakeshore.com/docs/default-source/product-downloads/224_manual.pdf for the manual


"""

import logging

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

        * CH<X>_CURVE: select calibration curve for channel X
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

        if setting_X == "CHX_CURVE":
            if value_original == "None":
                self.query(f"INCRV {channel} 0")
                self.active_channels.remove(channel)
                return f"{channel} is OFF"
            else:
                self.query(f"INCRV {channel} {value}")
                self.active_channels.append(channel)

                # remove dupilicate item in channal list
                self.active_channels = list(set(self.active_channels))

                return f"{channel} is using curve {value}"

    def command(self, cmd: str):
        """
        Executes an action specified by 'cmd'.

        Parameters
        ----------
        cmd
            Name of command to execute

        Notes
        -----
        !!!Just copy for future use!!!
        """

        if cmd == "SINGLE_TRIGGER":
            self.write(":SING")
        elif cmd == "RUN":
            self.write(":RUN")
        elif cmd == "CONFIG_READ_WAVE":
            self.configure_read_waveform()
        elif cmd == "STOP":
            self.write(":STOP")

    def read_temps(self, channel):
        """
        Read the temperature for channel online channel from [A, B, C1-C5, D1-D5]
        """

        # if self.dummy:
        #     outputs = [1 + 128 + 1024, 128, 1, 1024]
        #     value = random.choice(outputs)
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
