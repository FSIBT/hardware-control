import logging
import pkg_resources
from typing import Dict, Optional

from PyQt5.QtWidgets import (
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
)
from PyQt5.QtGui import QPixmap, QDoubleValidator
from PyQt5 import QtCore
from typing import List


logger = logging.getLogger(__name__)


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


class HCMixin:
    """Connect a Qt element to a setting or command in the app.

    This mixin sets the app, instrument, parameter values, connects to
    the app and also defines an hc_update function. The hc_update function
    still needs to be overwritten to connect to the actual widget,
    since there might be custom code needed to do this.

    """

    def __init__(self, **kwargs) -> None:

        app = kwargs.pop("app")
        instrument = kwargs.pop("instrument")
        parameter = kwargs.pop("parameter")
        if "label" in kwargs:
            label = kwargs.pop("label")
            label_align = kwargs.pop("label_align")
            self.add_label = True
        else:
            self.add_label = False

        for arg in [app, instrument, parameter]:
            if arg is None:
                logger.error(
                    f"Widget '{self.name}' does not get correct arguments (app, instrument, parameter)"
                )

        self.app = app
        self.instrument = instrument
        self.parameter = parameter

        super().__init__(**kwargs)

        # create an optional label
        if self.add_label:
            self.name = label
            self.label = QLabel(f"{label}: ")
            if label_align == "right":
                self.label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # connect to app
        self.app.add_widget(self.instrument, self.parameter, self)


class HCLabel(HCMixin, QLabel):
    """A simpel indicator widget for a label(QLabel) and a value (QLabel)."""

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        unit: str = "",
        use_prefix: bool = True,
        label_align: str = "left",
        min_width: int = 10,
    ) -> None:

        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            text="",
        )
        self.unit = unit
        self.use_prefix = use_prefix
        self.min_width = min_width

    def hc_update(self):
        value = self.app.get_instrument_parameter(self.instrument, self.parameter)
        self.setText(value)

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
        super().setText(text)


class HCLineEdit(HCMixin, QLineEdit):
    """A simple control widget with a label (QLabel) and an input box (QLineEdit).

    The control widget can be connected to a generic function, or
    directly to an instrument and a specific setting.

    A validator can also be set for the QLineEdit widget.

    When used directly inside an instrument the ``remote`` should be set to False.

    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        label_align="left",
        validator=QDoubleValidator,
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
        )

        if validator is not None:
            self.setValidator(validator())

        self.setText("----")

        self.editingFinished.connect(self.value_change)

    def value_change(self) -> None:
        value = self.text()
        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def hc_update(self) -> None:
        if self.hasFocus():
            logger.debug(f"'{self.name}' has focus, not updating")
            return
        value = self.app.get_instrument_parameter(
            self.instrument, self.parameter, return_set_value=True
        )
        self.setText(value)


class HCDoubleSpinBox(HCMixin, QDoubleSpinBox):
    """A simple control widget with a label (QLabel) and an input box (QLineEdit).

    The control widget can be connected to a generic function, or
    directly to an instrument and a specific setting.

    A validator can also be set for the QLineEdit widget.

    When used directly inside an instrument the ``remote`` should be set to False.

    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        label_align="left",
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
        )

        self.setValue(0)

        self.editingFinished.connect(self.value_change)

    def value_change(self) -> None:
        value = self.text()
        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def hc_update(self) -> None:
        value = float(
            self.app.get_instrument_parameter(self.instrument, self.parameter)
        )
        self.setValue(value)


class HCPushButton(HCMixin, QPushButton):
    """A simple control widget with a label (QLabel) and an input box (QLineEdit).

    The control widget can be connected to a generic function, or
    directly to an instrument and a specific setting.

    A validator can also be set for the QLineEdit widget.

    When used directly inside an instrument the ``remote`` should be set to False.

    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str = "",
        label_align: str = "left",
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            text=label,
        )

        self.clicked.connect(self.value_change)

    def value_change(self) -> None:
        self.app.call_instrument_command(self.instrument, self.parameter)

    def hc_update(self) -> None:
        pass


class HCToggleButton(HCMixin, QPushButton):
    """A simple control widget with a label (QLabel), a button (QPushButton), and an optional indicator (QLabel).

    The control widget can be connected to a generic function, or
    directly to an instrument and a specific setting.

    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        button_label: str = "",
        show_indicator: bool = False,
        icon_1: Optional[str] = None,
        icon_2: Optional[str] = None,
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            text=button_label,
        )

        self.show_indicator = show_indicator
        if self.show_indicator:
            self.icon_1 = load_icon(icon_1)
            self.icon_2 = load_icon(icon_2)
            self.indic_label = QLabel()
            self.indic_label.setPixmap(load_icon("na_label.svg"))

        self.clicked.connect(self.value_change)
        self.setCheckable(True)
        setButtonState(self, False)

    def value_change(self) -> None:
        self.app.set_instrument_parameter(
            self.instrument, self.parameter, self.isChecked()
        )

        if self.show_indicator:
            if self.isChecked():
                self.indic_label.setPixmap(self.icon_1)
            else:
                self.indic_label.setPixmap(self.icon_2)

    def hc_update(self):
        pass


class HCComboBox(HCMixin, QComboBox):
    """A simple control widget with a label (QLabel) and an input box (QComboBox).

    The control widget can be connected to a generic function, or
    directly to an instrument and a specific setting.

    When used directly inside an instrument the ``remote`` should be set to False.

    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        items,
        label_align: str = "left",
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
        )
        self.items = items

        self.addItems(self.items)
        self.setCurrentText(self.items[0])

        self.currentIndexChanged.connect(self.value_change)

    def value_change(self) -> None:
        value = self.currentText().upper()
        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def hc_update(self) -> None:
        value = self.app.get_instrument_parameter(self.instrument, self.parameter)
        for i in self.items:
            if value.casefold() == i.casefold():
                self.setCurrentText(i)
                break
        else:
            logger.error(f"HCControlCombo: could not find '{value}' in item list")


class HCDoubleSpinComboBox(HCMixin):
    """A simple control widget with a label (QLabel) and two input boxes (QSpinBox, QComboBox).

    The control widget can be connected to a generic function, or
    directly to an instrument and a specific setting.

    When used directly inside an instrument the ``remote`` should be set to False.

    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        units: Dict[str, float],
        label_align: str = "left",
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
        )

        self.units = units
        self.spin = QDoubleSpinBox()
        self.combo = QComboBox()

        # Set spinbox value
        self.spin.setValue(0)

        # Set combobox values
        self.combo.addItems(self.units.keys())

        # Connect spinbox and combobox to the function that sets the instrument parameter
        self.spin.editingFinished.connect(self.value_change)
        self.combo.currentIndexChanged.connect(self.value_change)

    def value_change(self) -> None:
        combo_value = self.units[self.combo.currentText()]
        spin_value = float(self.spin.text())
        value = spin_value * combo_value

        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def hc_update(self) -> None:
        value = float(
            self.app.get_instrument_parameter(self.instrument, self.parameter)
        )
        combo_value = self.units[self.combo.currentText()]
        value *= combo_value

        self.spin.setValue(value)


class HCSpinBox(HCMixin, QSpinBox):
    """A simple control widget with a label (QLabel) and an input box (QSpinBox)."""

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        label_align: str = "left",
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
        )

        self.valueChanged.connect(self.value_change)

    def value_change(self) -> None:
        value = self.value()
        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def hc_update(self) -> None:
        value = float(
            self.app.get_instrument_parameter(self.instrument, self.parameter)
        )
        self.setValue(value)


class HCHeader(QLabel):
    """Display an image as a header"""

    def __init__(self, icon_name):
        super().__init__()
        self.setPixmap(load_icon(icon_name))
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
