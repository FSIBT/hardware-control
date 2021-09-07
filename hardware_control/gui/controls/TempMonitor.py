from hardware_control import instruments
import logging

from PyQt5 import QtCore
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
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
                parameter=f"{channel}_TEMP",
                label=f"{channel} temperature",
                unit="K",
                use_prefix=False,
                label_align="right",
            )
            curve = HCLineEdit(
                self.app,
                self.instrument, 
                parameter=f"CH{channel}_CHANGE_CURVE",
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

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(1000)

        logger.debug("Initalized")

    def close(self):
        self.readout_timer.stop()
        super().close()

    def update_readout(self):
        """Queries the instrument for current readout data, then reads the most
        recent readout data from the inbox and pushes it to the GUI"""

        # Request updated readout data
        for parameter in ["CHA_READ_TEMP", "CHB_READ_TEMP","CHC1_READ_TEMP", "CHD1_READ_TEMP"]:
            self.app.update_instrument_parameter(self.instrument, parameter)
