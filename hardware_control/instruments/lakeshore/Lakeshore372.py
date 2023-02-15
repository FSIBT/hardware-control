"""
Control class to handle Lake shore 372 Temperature Monitor for Temp readouts.

.. image:: /images/Lake_Shore_372.png
  :height: 200

Has been tested with Lakeshore models 372
connection works over proprietary driver, with "tasks"
https://www.lakeshore.com/docs/default-source/product-downloads/manuals/372_manual.pdf for the manual

"""

import logging

from ...base import Instrument

logger = logging.getLogger(__name__)


class Lakeshore_372(Instrument):
    """
    A driver for the Lakeshore 372 Temp Monitor
    Instrument home page:
    https://www.lakeshore.com/products/categories/overview/temperature-products/ac-resistance-bridges/model-372-ac-resistance-bridge-temperature-controller
    """

    def __init__(
        self,
        instrument_name: str = "LAKESHORE_372",
        connection_addr: str = "",
    ):
        super().__init__(
            instrument_name=instrument_name,
            connection_addr=connection_addr,
            default_port=7777,
            num_channels=16,
            active_channels=[f"{i+1}" for i in range(16)],
        )

        self.model = "372"
