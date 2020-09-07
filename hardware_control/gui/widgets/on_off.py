from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QPushButton, QSizePolicy
from PyQt5.QtSvg import QSvgWidget

from .utility import load_icon, icon_filename, setButtonState


class QOnOffButton(QPushButton):
    """An On/Off button with a nice icon for on/off

    Clicking on the button will toggle `instrument.settings[setting_name]`.
    Tne button will display the state from `instrument.values[setting_name]`

    Parameters
    ----------
    instrument
        The instrument
    setting_name : str
        The instrument.settings and instrument.values to connect to

    """

    def __init__(self, instrument, setting_name: str):
        super().__init__()

        self.instrument = instrument
        self.name = setting_name

        self.setCheckable(True)

        self.on_text = "On"
        self.off_text = "Off"

        self.on_icon = QIcon(load_icon("button-power-on.svg"))
        self.off_icon = QIcon(load_icon("button-power-off.svg"))

        self.clicked.connect(self.click)
        self.update_status(self.instrument.values[self.name])

        self.setIconSize(QtCore.QSize(30, 30))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        instrument.update_values_hooks[self.name].append(self.instrument_return_hook)

    def instrument_return_hook(self, setting, value):
        self.update_status(value)
        return value

    def click(self):
        """Toggle the current status."""
        toggled_value = str(self.instrument.values[self.name] != "True")
        self.instrument.remote_update_setting(self.name, toggled_value)

    def update_status(self, value):
        if value == "True":
            self.setChecked(True)
            self.setIcon(self.on_icon)
            self.setText(self.on_text)
        else:
            self.setChecked(False)
            self.setIcon(self.off_icon)
            self.setText(self.off_text)


class QOnOffIndicator(QSvgWidget):
    """Small On/Off indicator.

    Starts in an unknown state (both lights off)

    Parameters
    ----------
    instrument
        The instrument
    setting_name : str
        The instrument.settings and instrument.values to connect to

    """

    def __init__(self, instrument, setting_name):
        self.name = setting_name
        self.instrument = instrument
        self.on_icon = icon_filename("on-off-indicator-on.svg")
        self.off_icon = icon_filename("on-off-indicator-off.svg")
        self.unknown_icon = icon_filename("on-off-indicator-unknown.svg")

        self.status = "unknown"

        super().__init__(self.unknown_icon)

        self.setMouseTracking(True)
        self.setToolTip(self.name)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.instrument.update_values_hooks[self.name].append(self.update_hook)

    def update_hook(self, setting, value):
        self.set(value)
        return value

    def sizeHint(self):
        return QSize(10, 20)

    def set(self, status):
        if status != self.status:
            self.status = status
            if status:
                self.renderer().load(self.on_icon)
            else:
                self.renderer().load(self.off_icon)
