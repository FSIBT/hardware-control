"""HC aware versions of Qt widgets.

Here you find version of Qt widgets, such as QLabel, QPushButton, etc.
that connect to a certain instrument and parameter and automatic update.

This module also provides some more additional widgets that do not
have equivalent ones in Qt directly.

"""


import logging
import pkg_resources
from typing import Dict, Optional, Union

from PyQt5.QtWidgets import (
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap, QDoubleValidator, QFont, QFontMetrics
from PyQt5 import QtCore
from typing import List


logger = logging.getLogger(__name__)


def load_icon(name: str) -> QPixmap:
    """Load an icon from the installed package location as a QPixmap"""
    return QPixmap(icon_filename(name))


def icon_filename(name: str):
    """Get the icon filename from the installed package location"""
    return pkg_resources.resource_filename("hardware_control", f"icons/{name}")


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
            elif label_align == "left":
                self.label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            elif label_align == "center":
                self.label.setAlignment(QtCore.Qt.AlignCenter)

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
        self.value = self.app.get_instrument_parameter(self.instrument, self.parameter)
        self.setText(self.value)

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
        self.validator = validator

        if self.validator is not None:
            self.setValidator(validator())

        self.setText("----")

        self.editingFinished.connect(self.value_change)

    def value_change(self) -> None:
        self.value = self.text()
        self.app.set_instrument_parameter(self.instrument, self.parameter, self.value)

    def hc_update(self) -> None:
        if self.hasFocus():
            logger.debug(f"'{self.name}' has focus, not updating")
            return
        self.value = self.app.get_instrument_parameter(
            self.instrument, self.parameter, return_set_value=True
        )
        self.setText(self.value)


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
        self.value = self.text()
        self.app.set_instrument_parameter(self.instrument, self.parameter, self.value)

    def hc_update(self) -> None:
        self.value = float(
            self.app.get_instrument_parameter(self.instrument, self.parameter)
        )
        self.setValue(self.value)


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


class HCOnOffButton(HCMixin, QPushButton):
    """Similar to HCPushButton, but also have graphical indicators for on/off state."""

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str = "",
        show_icon: bool = False,
        icon_checked: str = "button-power-on.svg",
        icon_unchecked: str = "button-power-off.svg",
        show_text: bool = True,
        text_checked: str = "On",
        text_unchecked: str = "Off",
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            text=label,
        )

        self.icon_checked = load_icon(icon_checked)
        self.icon_unchecked = load_icon(icon_unchecked)
        self.icon_unknown = load_icon("button-power-unknown.svg")

        self.clicked.connect(self.value_change)
        self.setCheckable(True)

        # set default to unkown state
        if show_icon:
            self.setIcon(self.icon_unknown)
        if show_text:
            self.setText("unkown")

    def is_true(self, value: Union[bool, str]) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value in ["True", "TRUE"]:
                return True
        return False

    def set_state(self, value):
        if self.show_icon:
            if value:
                self.setIcon(self.icon_checked)
            else:
                self.setIcon(self.icon_unchecked)

        if self.show_text:
            if value:
                self.setText(self.text_checked)
            else:
                self.setText(self.text_unchecked)

    def value_change(self) -> None:
        value = self.isChecked()
        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

        self.set_state(value)

    def hc_update(self):
        value = self.app.get_instrument_parameter(
            self.instrument,
            self.parameter,
        )

        self.set_state(value)


class HCOnOffIndicator(HCMixin, QLabel):
    """Similar to HCPushbutton, but only indicates an  on/off state."""

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str = "",
        show_icon: bool = False,
        icon_checked: str = "on-off-indicator-on.svg",
        icon_unchecked: str = "on-off-indicator-off.svg",
        show_text: bool = True,
        text_checked: str = "On",
        text_unchecked: str = "Off",
        tooltip: str = "",
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            text=label,
        )

        self.icon_checked = load_icon(icon_checked)
        self.icon_unchecked = load_icon(icon_unchecked)
        self.icon_unknown = load_icon("on-off-indicator-unknown.svg")

        # set default to unkown state
        if show_icon:
            self.setIcon(self.icon_unknown)
        if show_text:
            self.setText("unkown")

        self.setMouseTracking(True)
        self.setToolTip(self.label)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def sizeHint(self):
        if self.show_icon and not self.show_text:
            return QSize(10, 20)
        else:
            return super().sizeHint()

    def is_true(self, value: Union[bool, str]) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value in ["True", "TRUE"]:
                return True
        return False

    def set_state(self, value):
        if self.show_icon:
            if value:
                self.setIcon(self.icon_checked)
            else:
                self.setIcon(self.icon_unchecked)

        if self.show_text:
            if value:
                self.setText(self.text_checked)
            else:
                self.setText(self.text_unchecked)

    def hc_update(self):
        value = self.app.get_instrument_parameter(
            self.instrument,
            self.parameter,
        )

        self.set_state(value)


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
        self.value = self.currentText().upper()
        self.app.set_instrument_parameter(self.instrument, self.parameter, self.value)

    def hc_update(self) -> None:
        self.value = self.app.get_instrument_parameter(self.instrument, self.parameter)
        for i in self.items:
            if self.value.casefold() == i.casefold():
                self.setCurrentText(i)
                break
        else:
            logger.error(f"HCControlCombo: could not find '{self.value}' in item list")


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

        # Set combobox values
        self.combo.addItems(self.units.keys())

        # Connect spinbox and combobox to the function that sets the instrument parameter
        self.spin.editingFinished.connect(self.value_change)
        self.combo.currentIndexChanged.connect(self.value_change)

    def value_change(self) -> None:
        combo_value = self.units[self.combo.currentText()]
        spin_value = float(self.spin.text())
        self.value = spin_value * combo_value

        self.app.set_instrument_parameter(self.instrument, self.parameter, self.value)

    def hc_update(self) -> None:
        self.value = float(
            self.app.get_instrument_parameter(self.instrument, self.parameter)
        )
        combo_value = self.units[self.combo.currentText()]
        self.value *= combo_value

        self.spin.setValue(self.value)


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
        # Rename QSpinBox method for getting current value to avoid naming conflicts
        self.get_current_value = self.value

        self.valueChanged.connect(self.value_change)

    def value_change(self) -> None:
        self.value = self.get_current_value()
        self.app.set_instrument_parameter(self.instrument, self.parameter, self.value)

    def hc_update(self) -> None:
        self.value = float(
            self.app.get_instrument_parameter(self.instrument, self.parameter)
        )
        self.setValue(self.value)


class HCHeader(QLabel):
    """Display an image as a header."""

    def __init__(self, icon_name):
        super().__init__()
        self.setPixmap(load_icon(icon_name))
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)


class HCFixedLabel(HCMixin, QLabel):
    """A QLabel that fixes its width to the initial string."""

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        init_label: str = "",
        unit: str = "",
        color: str = None,
        fontsize: int = 18,
        bold: bool = False,
        label_align: str = "center",
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
        )

        self.unit = unit
        self.value = init_label

        self.setText(self.value + " " + self.unit)

        font = QFont()
        font.setPointSize(fontsize)
        font.setBold(bold)
        self.setFont(font)

        fm = QFontMetrics(self.font())
        self.setFixedWidth(fm.width(self.text()))

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if color is not None:
            self.setStyleSheet(
                f"color: white;background-color:{color}; padding: 5px;border: 1px solid black;"
            )

        # Align the label
        if label_align == "right":
            self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        elif label_align == "left":
            self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        elif label_align == "center":
            self.setAlignment(QtCore.Qt.AlignCenter)

    def hc_update(self):
        self.value = self.app.get_instrument_parameter(self.instrument, self.parameter)
        self.setText(self.value)

    def setText(self, text: str) -> None:
        if self.unit:
            try:
                text = f"{float(text):.3g} {self.unit}"
            except:
                text = f"{text} {self.unit}"
        else:
            try:
                text = f"{float(text):.3g}"
            except:
                text = f"{text}"
        super().setText(text)
