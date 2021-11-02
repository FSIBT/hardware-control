import logging

from PyQt5.QtWidgets import QGroupBox

from ..widgets import HCLineEdit, HCLabel, HCGridLayout

logger = logging.getLogger(__name__)


class TempMonitor(QGroupBox):
    """
    A GUI for Lakeshore Temperature Monitor.

    It only includes channels listed in `channel_list`.
    """

    def __init__(
        self,
        app,
        instrument: str,
        channel_list,
    ):

        super().__init__(instrument)
        self.app = app
        self.instrument = instrument

        self.channel_list = channel_list

        self.widgets = []
        for channel in self.channel_list:
            temperature = HCLabel(
                self.app,
                self.instrument,
                parameter=f"CH{channel}_READ_TEMP",
                label=f"{channel} temperature",
                unit="K",
                use_prefix=False,
                label_align="right",
            )
            curve = HCLineEdit(
                self.app,
                self.instrument,
                parameter=f"CH{channel}_CURVE",
                label=f"{channel}_CURVE",
                label_align="right",
            )
            self.widgets.append(temperature)
            self.widgets.append(curve)

        self.grid = HCGridLayout(self.widgets)
        self.setLayout(self.grid)

        self.default_update_readout()
        logger.debug("Initalized")

    def default_update_readout(self):
        """Register parameters for automatic updates."""

        for channel in self.channel_list:
            self.app.add_auto_update_instrument_parameter(
                self.instrument, f"CH{channel}_READ_TEMP"
            )
