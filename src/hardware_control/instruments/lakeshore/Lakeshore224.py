"""
Control class to handle Lake shore 224 Temperature Monitor for Temp readouts.

.. image:: /images/Lake_Shore_224.png
  :height: 200

Has been tested with Lakeshore models 224
connection works over proprietary driver, with "tasks"
https://www.lakeshore.com/docs/default-source/product-downloads/224_manual.pdf for the manual


"""

import logging

from .LakeshoreBase import LakeshoreBase

logger = logging.getLogger(__name__)


class Lakeshore_224(LakeshoreBase):
    """
    A driver for the Lakeshore 224 Temp Monitor
    Instrument home page:
    https://www.lakeshore.com/products/categories/overview/temperature-products/cryogenic-temperature-monitors/model-224-temperature-monitor
    """

    def __init__(
        self,
        instrument_name: str = "LAKESHORE_224",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=7777,
            num_channels=12,
            active_channels=[
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
            ],
        )

        self.model = "224"
