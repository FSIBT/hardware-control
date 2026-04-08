"""
.. image:: /images/controls/TempMonitor.png
"""

import logging

from PyQt6.QtWidgets import QGroupBox

from ...base.gui_control import ValidatedControl
from ..widgets import HCLineEdit, HCLabel, HCGridLayout, HCOnOffButton

logger = logging.getLogger(__name__)


class TempMonitor(ValidatedControl, QGroupBox):
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
    hardware_control.instruments.lakeshore.Lakeshore224
    """

    # No class-level required parameters - they're dynamically determined from channel_list

    def __init__(
        self,
        app,
        instrument: str,
        channel_list,
    ):
        # Validation happens automatically in super().__init__
        super().__init__(app, instrument, instrument)

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
                auto_update=False,
            )
            on_off_but = HCOnOffButton(
                self.app,
                self.instrument,
                f"CH{channel}_ON-OFF",
                label="On/Off",
                label_align="right",
                text_checked="Turn Off",
                text_unchecked=" Turn On",
            )
            # on_off_but.clicked.connect(self.remove_auto_update)
            self.widgets.append(temperature)
            self.widgets.append(curve)
            self.widgets.append(on_off_but)

        # All parameters auto-registered through HC widgets

        self.grid = HCGridLayout(self.widgets)
        self.setLayout(self.grid)

        logger.debug("Initalized")
