import pkg_resources

from PyQt5.QtWidgets import QPushButton, QLabel, QLineEdit, QComboBox
from PyQt5.QtGui import QPixmap
from PyQt5 import QtCore


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


class QIndicator:
    """A simpel indicator widget for a label(QLabel) and a value (QLabel)."""

    def __init__(self, label: str, label_align: str = "left") -> None:
        self.name = label
        self.label = QLabel(f"{label} :")
        self.value = QLabel("")
        if label_align == "right":
            self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def setText(self, text: str) -> None:
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
        validator=None,
        update_function=None,
        remote=True,
    ):

        self.instrument = inst
        self.setting = setting
        self.name = label

        self.label = QLabel(f"{label}: ")
        if label_align == "right":
            self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.edit = QLineEdit()
        if validator:
            self.edit.setValidator(validator)

        self.edit.setText(self.instrument.settings[self.setting])

        if update_function:
            self.edit.editingFinished.connect(update_function)
        else:
            if remote:
                self.edit.editingFinished.connect(
                    lambda: self.instrument.remote_update_setting(
                        self.setting, self.edit.text()
                    )
                )
            else:
                self.edit.editingFinished.connect(
                    lambda: self.instrument.update_setting(
                        self.setting, self.edit.text()
                    )
                )

    def text(self) -> str:
        return self.edit.text()

    def setText(self, text: str) -> None:
        self.edit.setText(text)

    def settings_to_UI(self):
        self.edit.setText(self.instrument.settings[self.setting])

    def setEnabled(self, value: bool) -> None:
        self.edit.setEnabled(value)


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
        remote: bool = True,
    ):

        self.instrument = inst
        self.setting = setting
        self.name = label
        self.items = items

        self.pre_update_hook = []
        self.update_function = update_function
        self.remote = remote

        self.label = QLabel(f"{label}: ")
        if label_align == "right":
            self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.combo = QComboBox()

        self.combo.addItems(self.items)
        self.combo.setCurrentText(self.items[0])

        self.combo.currentIndexChanged.connect(self.value_change)

    def value_change(self) -> None:
        value = self.combo.currentText().upper()
        setting = self.setting

        for f in self.pre_update_hook:
            value, setting = f(value, setting)
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
        return self.combo.currentText()

    def setCurrentText(self, text: str) -> None:
        self.combo.setCurrentText(text)

    def settings_to_UI(self) -> None:
        self.combo.setCurrentText(self.instrument.settings[self.setting])

    def setEnabled(self, value: bool) -> None:
        self.combo.setEnabled(value)


class QHeader(QLabel):
    """Display an image as a header"""

    def __init__(self, icon_name):
        super().__init__()
        self.setPixmap(load_icon(icon_name))
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
