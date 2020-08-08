from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton, QSizePolicy

from .utility import load_icon


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

        self.onText = "On"
        self.offText = "Off"
        self.unkownText = "status unkown"

        self.onIcon = QIcon(load_icon("button-power-on.svg"))
        self.offIcon = QIcon(load_icon("button-power-off.svg"))
        self.unkownIcon = QIcon(load_icon("button-power-unkown.svg"))

        self.clicked.connect(self.click)

        self.setText(self.unkownText)
        self.setIcon(self.unkownIcon)
        self.setIconSize(QtCore.QSize(30, 30))

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        def instrument_return_hook(key, value):
            if key == self.name:
                self.update_status(value)

        instrument.update_values_hooks.append(instrument_return_hook)

    def click(self):
        """Toggle the current status."""
        self.instrument.remote_update_setting(
            self.name, not self.instrument.values[self.name]
        )
        current_text = self.getText()
        self.setText(f"{current_text} (change requested)")

    def update_status(self, value):
        if value:
            self.setChecked(True)
            self.setIcon(self.onIcon)
            self.setText(self.onText)
        else:
            self.setChecked(False)
            self.setIcon(self.offIcon)
            self.setText(self.offText)


# class QOnOffIndicator(QSvgWidget):
#     """An On/Off indicator
#
#     Listens to signals for on/off and shows a green or red light with a tooltip for mouse-over events.
#
#     starts in an unkown state (both lights off)"""
#
#     def __init__(self, name):
#         self.name = name
#         self.onIcon = pkg_resources.resource_filename(
#             "hardware_control", "icons/on-off-indicator-on.svg"
#         )
#         self.offIcon = pkg_resources.resource_filename(
#             "hardware_control", "icons/on-off-indicator-off.svg"
#         )
#         self.unkownIcon = pkg_resources.resource_filename(
#             "hardware_control", "icons/on-off-indicator-unkown.svg"
#         )
#
#         super().__init__(self.unkownIcon)
#
#         self.setMouseTracking(True)
#         self.setToolTip(name)
#
#         self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
#
#     def sizeHint(self):
#         return QSize(10, 20)
#
#     def on(self):
#         self.renderer().load(self.onIcon)
#
#     def off(self):
#         self.renderer().load(self.offIcon)
#
#     def set(self, status):
#         if status:
#             self.on()
#         else:
#             self.off()
#
#
# class QFixedLabel(QLabel):
#     """A QLabel that fixes its width to the initial string"""
#
#     def __init__(self, label, color=None):
#         super().__init__(label)
#
#         font = QFont()
#         font.setPointSize(18)
#         font.setBold(False)
#         self.setFont(font)
#
#         fm = QFontMetrics(self.font())
#         self.setFixedWidth(fm.width(self.text()))
#
#         self.setAlignment(QtCore.Qt.AlignCenter)
#         self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
#         if color is not None:
#             self.setStyleSheet(
#                 f"color: white;background-color:{color}; padding: 5px;border: 1px solid black;"
#             )
#
