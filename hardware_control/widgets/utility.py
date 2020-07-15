from PyQt5.QtWidgets import QPushButton


def setButtonState(button: QPushButton, value):
    """Sets the state of a QPushButton to checked
    or unchecked, accoridng to 'value'. Only applicable
    to QPushButtons with field 'checkable' set to true."""
    if type(value) == bool:
        if value:
            if not button.isChecked():
                button.toggle()
        else:
            if button.isChecked():
                button.toggle()
    elif type(value) == str:
        if value == "True" or value == "TRUE":
            if not button.isChecked():
                button.toggle()
        else:
            if button.isChecked():
                button.toggle()
