import logging

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QGroupBox, QLabel, QGridLayout

from .utility import load_icon

logger = logging.getLogger(__name__)


class StatusTool(QGroupBox):
    """A widget to display if instruments are online or offline.

    It gets the list of instruments from the app class, so it should
    be created after all instrumensts are defined already.

    """

    def __init__(self, app, name: str = "Connection Status", short_indicators=False):

        super().__init__(name)

        self.settings = self.default_state()
        self.name = name
        self.app = app
        self.ignore = True
        self.ignore_control = True
        self.instrument_names = {}

        if short_indicators:
            self.green_indicator = load_icon("green_ind.svg")
            self.grey_indicator = load_icon("grey_ind.svg")
            self.darkgrey_indicator = load_icon("ind_darkgrey.png")
            self.red_indicator = load_icon("red_ind.svg")
            self.blue_indicator = load_icon("blue_ind.svg")
        else:
            self.green_indicator = load_icon("online_label.svg")
            self.grey_indicator = load_icon("na_label.svg")
            self.darkgrey_indicator = load_icon("disabled_label.svg")
            self.red_indicator = load_icon("offline_label.svg")
            self.blue_indicator = load_icon("enabled_label.svg")

        self.instruments_label = QLabel()
        self.instruments_label.setPixmap(load_icon("status_label.png"))
        self.instruments_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.instrument_grid = QGridLayout()

        # Add a grid layout that will hold all the connection status information
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.instruments_label, 0, 0, 1, 1)
        self.master_layout.addLayout(self.instrument_grid, 1, 0, 1, 1)
        self.setLayout(self.master_layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)

        self.update_instruments()

    def update_instruments(self):
        """Adds all currently known instruments."""

        # Clear layout
        for i in reversed(range(self.instrument_grid.count())):
            self.instrument_grid.itemAt(i).widget().setParent(None)
        self.instrument_names = {}

        for row, inst in enumerate(self.app.instruments):
            if inst.ignore:
                continue

            # save the row to make updating the instrument later easier
            self.instrument_names[inst.name] = row

            label = QLabel(inst.name)
            indicator = QLabel()
            indicator.setPixmap(self.grey_indicator)
            indicator.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            self.instrument_grid.addWidget(label, row, 0)
            self.instrument_grid.addWidget(indicator, row, 1)

    def update_status(self):
        """Check if instrument is online/offline.

        This updates the icons to represent the online/offline
        state. The function is normally called every second by a
        QtTimer.

        """
        for instrument in self.app.instruments:

            row = self.instrument_names.get(instrument.name, None)
            if row is None:
                continue

            if self.instrument_grid.itemAtPosition(row, 1) is None:
                continue

            if instrument.online:
                self.instrument_grid.itemAtPosition(row, 1).widget().setPixmap(
                    self.blue_indicator
                    if instrument.online_color == "Blue"
                    else self.green_indicator
                )
            else:
                self.instrument_grid.itemAtPosition(row, 1).widget().setPixmap(
                    self.darkgrey_indicator
                    if instrument.online_color == "Blue"
                    else self.red_indicator
                )

    def default_state(self):
        return {
            "values": "",
            "instrument": "----------",
            "parameter": "----------",
            "action_instrument": "----------",
            "action_parameter": "----------",
            "progress": 0,
        }
