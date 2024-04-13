"""
    .. image:: /images/controls/MicrowaveController.png
      :height: 150
"""

import logging
from typing import Optional

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

    One can customize the power levels that are available. This can be useful,
    if the TPI is used together with an amplifier to generate higher output
    power and one wants these to be shown.

    See Also
    --------
    hardware_control.instruments.trinity_power.TDI.TDI
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        name: str = "Microwave Controller",
        power_levels: Optional[dict] = None,
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

        if power_levels is None:
            power_levels = {
                "9 dBm": "9",
                "8 dBm": "8",
                "7 dBm": "7",
                "6 dBm": "6",
                "5 dBm": "5",
                "4 dBm": "4",
                "3 dBm": "3",
                "2 dBm": "2",
                "1 dBm": "1",
                "0 dBm": "0",
                "-1 dBm": "-1",
                "-2 dBm": "-2",
                "-3 dBm": "-3",
                "-4 dBm": "-4",
                "-5 dBm": "-5",
                "-6 dBm": "-6",
                "-7 dBm": "-7",
                "-8 dBm": "-8",
                "-9 dBm": "-9",
            }
        self.power = HCComboBox(
            self.app,
            self.instrument,
            parameter="OUTPUT_LEVEL",
            label="Power",
            items=list(power_levels.keys()),
            lookuptable=power_levels,
            label_align="right",
        )
        self.power_read = HCLabel(
            self.app,
            self.instrument,
            parameter="OUTPUT_LEVEL",
            label="Power",
            label_align="right",
        )

        self.on_off = HCOnOffButton(
            self.app,
            self.instrument,
            parameter="OUTPUT_ON_OFF",
            label="MW",
            show_icon=True,
            text_pretext="MW",
        )

        self.layout = HCGridLayout(
            [self.on_off, self.power, self.power_read, self.frequency, self.online_ind]
        )
        self.setLayout(self.layout)
