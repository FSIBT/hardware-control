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

import numpy as np

from ...base import Instrument
from ..utility import ensure_float, get_channel_from_command

logger = logging.getLogger(__name__)


class Lakeshore_224(Instrument):
    """
    A driver for the Lakeshore 224 Temp Monitor
    Instrument home page:
    https://www.lakeshore.com/products/categories/overview/temperature-products/cryogenic-temperature-monitors/model-224-temperature-monitor
    """

    def __init__(
        self,
        name,
        connection_addr: str,
    ):
        super().__init__(
            instrument_name=name,
            connection_addr=connection_addr,
            default_port=7777,
        )

        self.manufacturer = "Lakeshore"
        self.model = "224"

        self.num_channels = 12
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

        self.check_connection_commands = ["*IDN?"]

        for channel in self.active_channels:
            self.add_command("SET_CH{channel}_OFF", f"INCRV {channel} 0")
            self.add_command(f"READ_CH{channel}_STATUS", self.read_status(channel))

            self.add_parameter(
                f"CH{channel}_CURVE",
                read_command=f"INCRV? {channel}",
                set_command=f"INCRV {channel} {{}}",
                post_hooks=[lambda value: value if value != "00" else None],
                dummy_return="",
            )

            self.add_parameter(
                f"CH{channel}_READ_TEMP",
                read_command=f"KRDG? {channel}",
                set_command="",
                post_hooks=[lambda value: value if value != "00" else None],
                dummy_return="",
            )

            # self.add_parameter(
            #     f"CH{channel}_NAME",
            #     read_command=f"INNAME? {channel}",
            #     set_command=f"INCRV {channel} {{}}",
            #     post_hooks=[lambda value: channel if value == 0 else value],
            #     dummy_return="",
            # )

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
