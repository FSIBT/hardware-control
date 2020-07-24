import pkg_resources

from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QPixmap


def load_icon(name: str):
    return QPixmap(pkg_resources.resource_filename("hardware_control", f"icons/{name}"))


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
