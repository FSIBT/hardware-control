"""
    .. image:: /images/controls/TempMonitor.png
"""
import logging
from typing import Optional

from PyQt6.QtWidgets import QGroupBox

from ..widgets import HCLineEdit, HCLabel, HCGridLayout, HCOnOffButton

logger = logging.getLogger(__name__)


class TempMonitor_Adam(QGroupBox):
    """
    A control program for temperature monitors.

    Parameters
    ----------
    app : hardware_control.App
        The main app instance
    instrument_name: str
        The name of the temperature monitor instrument
    channels : list
        A list of channels to be shown in the control program

    See Also
    --------
    hardware_control.instruments.advantech.Adam_6015
    """

    def __init__(
        self,
        app,
        instrument: str,
        channel_list: list[int],
        label_list: Optional[list[str]] = None,
    ):
        super().__init__(instrument)
        self.app = app
        self.instrument = instrument

        self.channel_list = channel_list
        if label_list is None:
            self.label_list = [f"{channel} temperature" for channel in channel_list]
        else:
            self.label_list = label_list

        self.widgets = []
        for channel, label in zip(self.channel_list, self.label_list):
            temperature = HCLabel(
                self.app,
                self.instrument,
                parameter=f"CH{channel}_READ_TEMPERATURE",
                label=label,
                unit="C",
                use_prefix=False,
                label_align="right",
            )
            self.widgets.append(temperature)

        self.grid = HCGridLayout(self.widgets, columns=2)
        self.setLayout(self.grid)

        logger.debug("Initalized TempMonitor_Adam")
