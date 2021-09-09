from hardware_control import instruments
import logging

from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
)
from PyQt5.QtCore import QTimer

from ..widgets import load_icon, HCLineEdit, HCLabel

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

        self.vbox = QVBoxLayout()
        for widget in self.widgets:
            tmp = QHBoxLayout()
            tmp.addWidget(widget.label)
            tmp.addWidget(widget)
            self.vbox.addLayout(tmp)

        self.setLayout(self.vbox)

        # Create timer to query temperatures
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.app.globalRefreshRate)

        logger.debug("Initalized")

    def close(self):
        self.readout_timer.stop()
        super().close()

    def update_readout(self):
        """Queries the instrument for current readout data, then reads the most
        recent readout data from the inbox and pushes it to the GUI"""

        for channel in self.channel_list:
            self.app.update_instrument_parameter(
                self.instrument, f"CH{channel}_READ_TEMP"
            )
