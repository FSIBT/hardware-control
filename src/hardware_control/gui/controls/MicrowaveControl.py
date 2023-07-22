"""
    .. image:: /images/controls/MicrowaveController.png
      :height: 150
"""
import logging

from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtGui import QIntValidator

from ..widgets import (
    HCLabel,
    HCLineEdit,
    HCGridLayout,
    HCOnOffButton,
    HCComboBox,
    HCOnOffIndicator,
)

logger = logging.getLogger(__name__)


class MicrowaveController(QGroupBox):
    """A GUI for microwave controllers.

    Implements setting the frequency, the power level and on/off.

    See Also
    --------
    hardware_control.instruments.trinity_power.TDI.TDI
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        name: str = "Microwave Controller",
    ):
        super().__init__(name)
        self.app = app
        self.instrument = instrument_name
        self.name = name

        self.online_ind = HCOnOffIndicator(
            self.app,
            self.instrument,
            "ONLINE",
            label="online status",
            show_icon=True,
        )

        freq_val = QIntValidator(35_000, 4_400_000)
        self.frequency = HCLineEdit(
            self.app,
            self.instrument,
            "FREQUENCY",
            label="Frequency (kHz)",
            validator=freq_val,
        )

        self.power = HCComboBox(
            self.app,
            self.instrument,
            parameter="OUTPUT_LEVEL",
            label="Power",
            items=[
                "210 W (8 dBm)",
                "205 W (7 dBm)",
                "200 W (6 dBm)",
                "160 W (5 dBm)",
                "130 W (4 dBm)",
                "100 W (3 dBm)",
                "80 W (2 dBm)",
                "60 W (1 dBm)",
                "35 W (0 dBm)",
                "20 W (-1 dBm)",
                "8 W (-2 dBm)",
            ],
            lookuptable={
                "210 W (8 dBm)": "8",
                "205 W (7 dBm)": "7",
                "200 W (6 dBm)": "6",
                "160 W (5 dBm)": "5",
                "130 W (4 dBm)": "4",
                "100 W (3 dBm)": "3",
                "80 W (2 dBm)": "2",
                "60 W (1 dBm)": "1",
                "35 W (0 dBm)": "0",
                "20 W (-1 dBm)": "-1",
                "8 W (-2 dBm)": "-2",
            },
            label_align="right",
        )

        self.on_off = HCOnOffButton(
            self.app,
            self.instrument,
            parameter="OUTPUT_ON_OFF",
            label="MW on/off",
            label_align="right",
            show_icon=True,
        )

        self.layout = HCGridLayout(
            [self.online_ind, self.frequency, self.power, self.on_off]
        )
        self.setLayout(self.layout)
