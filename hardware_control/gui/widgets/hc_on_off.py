from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QPushButton, QSizePolicy
from PyQt5.QtSvg import QSvgWidget

from .hc_widgets import load_icon, icon_filename, setButtonState, HCPushButton, HCLabel


class HCOnOffButton(HCPushButton):
    """An On/Off button with a nice icon for on/off

    Clicking on the button will toggle `instrument.settings[setting_name]`.
    Tne button will display the state from `instrument.values[setting_name]`

    Parameters
    ----------
    app
        The main app
    instrument
        The instrument name
    parameter
        The parameter name

    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str = "",
        label_align: str = "left",
        on_text: str = "On",
        off_text: str = "Off",
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
        )
        self.setCheckable(True)

        self.on_text = on_text
        self.off_text = off_text

        self.on_icon = QIcon(load_icon("button-power-on.svg"))
        self.off_icon = QIcon(load_icon("button-power-off.svg"))

        self.update()
        self.setIconSize(QtCore.QSize(30, 30))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def update(self):
        if not self.app.dummy:
            value = float(
                self.app.get_instrument_parameter(self.instrument, self.parameter)
            )
            self.setValue(value)
        else:
            value = "False"

        if value == "True":
            self.setChecked(True)
            self.setIcon(self.on_icon)
            self.setText(self.on_text)
        else:
            self.setChecked(False)
            self.setIcon(self.off_icon)
            self.setText(self.off_text)


class HCOnOffIndicator(HCLabel):
    """Small On/Off indicator.

    Starts in an unknown state (both lights off)

    Parameters
    ----------
    app
        The main app
    instrument
        The instrument name
    parameter
        The parameter name

    """

    def __init__(self, app, instrument, parameter, label, label_align):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            unit="",
            use_prefix=False,
        )

        self.on_icon = icon_filename("on-off-indicator-on.svg")
        self.off_icon = icon_filename("on-off-indicator-off.svg")
        self.unknown_icon = icon_filename("on-off-indicator-unknown.svg")

        self.status = "unknown"

        self.setMouseTracking(True)
        self.setToolTip(self.label)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def sizeHint(self):
        return QSize(10, 20)

    def hc_update(self):
        value = self.app.get_instrument_parameter(self.instrument, self.parameter)
        self.setText(value)
        if status != self.status:
            self.status = status
            if status:
                self.renderer().load(self.on_icon)
            else:
                self.renderer().load(self.off_icon)
