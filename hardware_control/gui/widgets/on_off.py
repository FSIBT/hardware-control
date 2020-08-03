# needs to be updated to work with latest version

# class QOnOff(QPushButton):
#     """An On/Off button with a nice icon for on/off
#
#     Takes two functions that will be called when turning on/off
#     starts in an unkown state if not defined otherwise
#
#     if f_off is None: assume that f_on is a signal that can emit a boolian.
#     """
#
#     def __init__(self, f_on, f_off=None):
#         super().__init__()
#         self.setCheckable(True)
#
#         self.onText = "On"
#         self.offText = "Off"
#         self.unkownText = "status unkown"
#
#         self.onIcon = QIcon(
#             pkg_resources.resource_filename(
#                 "hardware_control", "icons/button-power-on.svg"
#             )
#         )
#         self.offIcon = QIcon(
#             pkg_resources.resource_filename(
#                 "hardware_control", "icons/button-power-off.svg"
#             )
#         )
#         self.unkownIcon = QIcon(
#             pkg_resources.resource_filename(
#                 "hardware_control", "icons/button-power-unkown.svg"
#             )
#         )
#
#         self.f_on = f_on
#         self.f_off = f_off
#         self.clicked.connect(self.click)
#
#         self.setText(self.unkownText)
#         self.setIcon(self.unkownIcon)
#         self.setIconSize(QtCore.QSize(30, 30))
#
#         self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
#
#     def click(self):
#         # we need a 'not' here since the button internally already
#         # changed state at this point
#         if not self.isChecked():
#             if self.f_off:
#                 self.f_off()
#             else:
#                 self.f_on.emit(False)
#             self.set_icon_off()
#         else:
#             if self.f_off:
#                 self.f_on()
#             else:
#                 self.f_on.emit(True)
#             self.set_icon_on()
#
#     def on(self):
#         if self.f_off:
#             self.f_on()
#         else:
#             self.f_on.emit(True)
#         self.set_icon_on()
#
#     def set_icon_on(self):
#         """Just set the icon to on. Useful during startup"""
#         self.setChecked(True)
#         self.setIcon(self.onIcon)
#         self.setText(self.onText)
#
#     def off(self):
#         if self.f_off:
#             self.f_off()
#         else:
#             self.f_on.emit(False)
#         self.set_icon_off()
#
#     def set_icon_off(self):
#         """Just set the icon to off. Useful during startup"""
#         self.setChecked(False)
#         self.setIcon(self.offIcon)
#         self.setText(self.offText)
#
#     def isOn(self):
#         return self.isChecked()


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
