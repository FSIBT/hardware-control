import logging

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator
from PyQt5.QtWidgets import (
    QGroupBox,
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QWidget,
    QLineEdit,
    QLabel,
)

from ..base import Instrument
from ..widgets import load_icon, QControl, QControlCombo

logger = logging.getLogger(__name__)


class TempMonitor(Instrument):
    """
    A GUI for Lakeshore Temperature Monitor
    """

    def __init__(
        self,
        app,
        backend,
        name: str = "Lakeshore 224 Temperature Monitor",
        lock_until_sync=False,
        channels: int = 4,
    ):

        super().__init__(app, name, backend, lock_until_sync)

        self.channels = channels
        self.channel_list = [
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
        self.settings = self.default_state()
        # Create GUI

        self.channel_layout = QGridLayout()
        for i in range(self.channels):
            self.setChannelWidgets(i)

        self.setLayout(self.channel_layout)

    def setChannelWidgets(self, ch_num):
        ch_label = QLabel(f"CH{ch_num+1}:")
        curve_label = QLabel(f"Curve:")

        # Pick up one channel to read
        self.channel_drop = QComboBox()
        self.channel_drop.addItems(self.channel_list)
        self.channel_drop.setCurrentText(self.channel_list[ch_num])

        self.file_name = QLineEdit()

        self.channel_layout.addWidget(ch_label, 0, ch_num * 2)
        self.channel_layout.addWidget(curve_label, 1, ch_num * 2)
        self.channel_layout.addWidget(self.channel_drop, 0, ch_num * 2 + 1)
        self.channel_layout.addWidget(self.file_name, 1, ch_num * 2 + 1)

    def settings_to_UI(self):
        print("Need to Add?")

    def default_state(self):
        """Create the defualt state variable"""

        default = {}