"""
    .. image:: /images/widgets/connection_status.png
      :height: 400
"""
import logging

from PyQt5 import QtCore
from PyQt5.QtWidgets import QGroupBox, QLabel, QGridLayout

from .hc_widgets import load_pixmap, HCOnOffIndicator

logger = logging.getLogger(__name__)


class StatusTool(QGroupBox):
    """A widget to display if instruments are online or offline.

    The widget gets the list of instruments from the app class, so it should
    be created after all instrumensts are defined already.
    """

    def __init__(self, app, name: str = "Connection Status", short_indicators=False):

        super().__init__(name)

        self.app = app
        self.name = name
        self.instrument_rows = {}

        if short_indicators:
            self.green_indicator = "green_ind.svg"
            self.grey_indicator = "grey_ind.svg"
            self.red_indicator = "red_ind.svg"
        else:
            self.green_indicator = "online_label.svg"
            self.grey_indicator = "na_label.svg"
            self.red_indicator = "offline_label.svg"

        self.instruments_label = QLabel()
        self.instruments_label.setPixmap(load_pixmap("status_label.png"))
        self.instruments_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.instrument_grid = QGridLayout()

        # Add a grid layout that will hold all the connection status information
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.instruments_label, 0, 0, 1, 1)
        self.master_layout.addLayout(self.instrument_grid, 1, 0, 1, 1)
        self.setLayout(self.master_layout)

        self.update_instruments()

    def update_instruments(self):
        """Add all currently known instruments to the connection status widget."""
        for row, instrument in enumerate(self.app.list_instruments()):
            # If ignore parameter is True, do not add instrument to connection status widget
            if self.app.get_instrument_parameter(instrument, "IGNORE"):
                continue

            connection_ind = HCOnOffIndicator(
                self.app,
                instrument,
                "ONLINE",
                label=instrument,
                label_align="right",
                show_icon=True,
                icon_checked=self.green_indicator,
                icon_unchecked=self.red_indicator,
            )
            self.instrument_grid.addWidget(connection_ind.label, row, 0)
            self.instrument_grid.addWidget(connection_ind, row, 1)
