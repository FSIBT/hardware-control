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
from PyQt5.QtCore import QTimer

from ..widgets import load_icon, HCLineEdit, HCLabel

logger = logging.getLogger(__name__)


class TempMonitor(QGroupBox):
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

        self.TempA = HCLabel(
            self,
            "A_TEMP",
            unit="K",
            use_prefix=False,
            label_align="right",
        )
        self.Acurve = HCLineEdit(
            self,
            "CHA_CHANGE_CURVE",
            label="A_CURVE",
            label_align="right",
        )
        self.TempB = HCLabel(
            self,
            "B_TEMP",
            unit="K",
            use_prefix=False,
            label_align="right",
        )
        self.Bcurve = HCLineEdit(
            self,
            "CHB_CHANGE_CURVE",
            label="B_CURVE:",
            label_align="right",
        )
        self.TempC1 = HCLabel(
            self,
            "C1_TEMP",
            unit="K",
            use_prefix=False,
            label_align="right",
        )
        self.C1curve = HCLineEdit(
            self,
            "CHC1_CHANGE_CURVE",
            label="C1_CURVE",
            label_align="right",
        )
        self.TempD1 = HCLabel(
            self,
            "D1_TEMP",
            unit="K",
            use_prefix=False,
            label_align="right",
        )
        self.D1curve = HCLineEdit(
            self,
            "CHD1_CHANGE_CURVE",
            label="D1_CURVE",
            label_align="right",
        )
        self.autolayout_grid()

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

        logger.debug("Initalized")

        self.values["CHA_READ_TEMP"] = "-"
        self.values["CHB_READ_TEMP"] = "-"

    def close(self):
        self.readout_timer.stop()
        super().close()

    def update_readout(self):
        """Queries the instrument for current readout data, then reads the most
        recent readout data from the inbox and pushes it to the GUI"""

        # Request updated readout data
        self.command("CHA_READ_TEMP?")
        self.command("CHB_READ_TEMP?")
        self.command("CHC1_READ_TEMP?")
        self.command("CHD1_READ_TEMP?")

        print("debug", self.values, flush=True)

        # Update labels
        self.TempA.setText(self.values.get("CHA_READ_TEMP"))
        self.TempB.setText(self.values.get("CHB_READ_TEMP"))
        self.TempC1.setText(self.values.get("CHC1_READ_TEMP"))
        self.TempD1.setText(self.values.get("CHD1_READ_TEMP"))

    def settings_to_UI(self):
        print("Need to Add?")

    def default_state(self):
        """Create the defualt state variable"""

        return {
            "CHA_CHANGE_CURVE": "06",
            "CHB_CHANGE_CURVE": "21",
            "CHC1_CHANGE_CURVE": "32",
            "CHD1_CHANGE_CURVE": "20",
        }
