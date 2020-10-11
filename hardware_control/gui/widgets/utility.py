import pkg_resources

from PyQt5.QtWidgets import QPushButton, QLabel, QLineEdit, QComboBox
from PyQt5.QtGui import QPixmap, QDoubleValidator
from PyQt5 import QtCore
from typing import List


def load_icon(name: str) -> QPixmap:
    """Load an icon from the installed package location as a QPixmap"""
    return QPixmap(icon_filename(name))


def icon_filename(name: str):
    """Get the icon filename from the installed package location"""
    return pkg_resources.resource_filename("hardware_control", f"icons/{name}")


def setButtonState(button: QPushButton, value):
    """Sets the state of a QPushButton to checked
    or unchecked, accoridng to 'value'. Only applicable
    to QPushButtons with field 'checkable' set to true."""
    if isinstance(value, bool):
        if value:
            if not button.isChecked():
                button.toggle()
        else:
            if button.isChecked():
                button.toggle()
    elif isinstance(value, str):
        if value in ["True", "TRUE"]:
            if not button.isChecked():
                button.toggle()
        else:
            if button.isChecked():
                button.toggle()


def convert_prefix(value: str, decimals: int = 3) -> List[str]:
    try:
        value = float(value)
    except:
        return value, ""
    if abs(value) < 1e-9:
        return f"{round(value*1e12, decimals)}", "p"
    if abs(value) < 1e-6:
        return f"{round(value*1e9, decimals)}", "n"
    if abs(value) < 1e-3:
        return f"{round(value*1e6, decimals)}", "µ"
    if abs(value) < 1:
        return f"{round(value*1e3, decimals)}", "m"
    if abs(value) < 1e3:
        return f"{round(value, decimals)}", ""
    if abs(value) < 1e6:
        return f"{round(value*1e-3, decimals)}", "k"
    if abs(value) < 1e9:
        return f"{round(value*1e-6, decimals)}", "M"
    if abs(value) < 1e12:
        return f"{round(value*1e-9, decimals)}", "G"


class QIndicator:
    """A simpel indicator widget for a label(QLabel) and a value (QLabel)."""

    def __init__(
        self,
        instrument,
        label: str,
        unit: str = "",
        use_prefix: bool = True,
        label_align: str = "left",
        min_width: int = 10,
        remote=None,
    ) -> None:
        self.instrument = instrument
        self.name = label
        self.unit = unit
        self.use_prefix = use_prefix
        self.min_width = min_width
        self.remote = remote

        self.label = QLabel(f"{label}: ")
        self.value = QLabel("")
        if label_align == "right":
            self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.instrument.UIs.append(self)

    def setText(self, text: str) -> None:
        if self.unit:
            if self.use_prefix:
                text, prefix = convert_prefix(text)
                text = f"{text} {prefix}{self.unit}"
            else:
                try:
                    text = f"{float(text):.3g} {self.unit}"
                except:
                    text = f"{text} {self.unit}"
        if self.min_width:
            text = text.rjust(self.min_width)
        self.value.setText(text)


class QControl:
    """A simple control widget with a label (QLabel) and an input box (QLineEdit).

    The control widget can be connected to a generic function, or
    directly to an instrument and a specific setting.

    A validator can also be set for the QLineEdit widget.

    When used directly inside an instrument the ``remote`` should be set to False.

    """

    def __init__(
        self,
        inst,
        setting,
        label: str,
        label_align="left",
        validator=QDoubleValidator,
        update_function=None,
        remote=None,
    ):

        self.instrument = inst
        self.setting = setting
        self.name = label
        self.remote = remote
        if remote:
            self.remote_instrument, self.remote_setting = remote
        self.pre_update_hook = []
        self.update_function = update_function

        self.label = QLabel(f"{label}: ")
        if label_align == "right":
            self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.value = QLineEdit()
        if validator is not None:
            self.value.setValidator(validator())

        # self.instrument.settings might not be initialized correctly
        if self.setting in self.instrument.settings:
            self.value.setText(self.instrument.settings[self.setting])
        else:
            self.value.setText("----")

        self.value.editingFinished.connect(self.value_change)

        self.instrument.UIs.append(self)
        self.instrument.control_UIs.append(self)

    def value_change(self) -> None:
        value = self.value.text()
        setting = self.setting

        for f in self.pre_update_hook:
            setting, value = f(setting, value)
        if value is None:
            return

        if self.update_function:
            self.update_function(setting, value)
            return
        self.instrument.update_setting(setting, value)
        if self.remote:
            self.remote_instrument.remote_update_setting(self.remote_setting, value)

    def update_from_remote(self) -> None:
        if self.remote is None:
            return
        value = self.remote_instrument.settings[self.remote_setting]
        self.setText(value)

    def text(self) -> str:
        return self.value.text()

    def setText(self, text: str) -> None:
        self.value.setText(text)

    def settings_to_UI(self) -> None:
        self.value.setText(self.instrument.settings[self.setting])

    def setEnabled(self, value: bool) -> None:
        self.value.setEnabled(value)


class QControlCombo:
    """A simple control widget with a label (QLabel) and an input box (QComboBox).

    The control widget can be connected to a generic function, or
    directly to an instrument and a specific setting.

    When used directly inside an instrument the ``remote`` should be set to False.

    """

    def __init__(
        self,
        inst,
        setting,
        label: str,
        items,
        label_align: str = "left",
        update_function=None,
        remote=None,
    ):

        self.instrument = inst
        self.setting = setting
        self.name = label
        self.items = items

        self.pre_update_hook = []
        self.update_function = update_function
        self.remote = remote
        if remote:
            self.remote_instrument, self.remote_setting = remote

        self.label = QLabel(f"{label}: ")
        if label_align == "right":
            self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.value = QComboBox()

        self.value.addItems(self.items)
        self.value.setCurrentText(self.items[0])

        self.value.currentIndexChanged.connect(self.value_change)
        self.instrument.UIs.append(self)

    def value_change(self) -> None:
        value = self.value.currentText().upper()
        setting = self.setting

        for f in self.pre_update_hook:
            setting, value = f(setting, value)
        if value is None:
            return

        if self.update_function:
            self.update_function(setting, value)
            return
        if self.remote:
            self.instrument.remote_update_setting(setting, value)
            return
        self.instrument.update_setting(setting, value)

    def currentText(self) -> str:
        return self.value.currentText()

    def setCurrentText(self, text: str) -> None:
        self.value.setCurrentText(text)

    def settings_to_UI(self) -> None:
        self.value.setCurrentText(self.instrument.settings[self.setting])

    def setEnabled(self, value: bool) -> None:
        self.value.setEnabled(value)


class QHeader(QLabel):
    """Display an image as a header"""

    def __init__(self, icon_name):
        super().__init__()
        self.setPixmap(load_icon(icon_name))
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
