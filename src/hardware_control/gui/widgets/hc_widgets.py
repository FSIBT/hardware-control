"""Qt widgets that are well integrate with Hardware Control.

Here you will find versions of Qt widgets, such as QLabel, QPushButton, etc.
that can be connected to a certain instrument parameter and automatically be
updated.

This module also provides some more additional widgets that do not
have equivalent ones in Qt directly.
"""

import logging
from typing import Optional, Union, Callable, Any
import pkg_resources

from PyQt6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QSizePolicy,
)
from PyQt6.QtGui import QPixmap, QIcon, QDoubleValidator, QFont, QFontMetrics
from PyQt6 import QtCore
from ...base.hooks import call_hooks


logger = logging.getLogger(__name__)


def load_pixmap(name: str) -> QPixmap:
    """Load an icon from the installed package location as a QPixmap."""
    return QPixmap(icon_filename(name))


def load_icon(name: str) -> QPixmap:
    """Load an icon from the installed package location as a QIcon."""
    return QIcon(icon_filename(name))


def icon_filename(name: str):
    """Get the icon filename from the installed package location."""
    return pkg_resources.resource_filename("hardware_control", f"icons/{name}")


def convert_prefix(value: str, decimals: int = 3) -> list[str]:
    """Handle units prefix conversions."""
    try:
        value = float(value)
    except ValueError:
        return [value, ""]
    if abs(value) < 1e-9:
        return [f"{round(value*1e12, decimals)}", "p"]
    if abs(value) < 1e-6:
        return [f"{round(value*1e9, decimals)}", "n"]
    if abs(value) < 1e-3:
        return [f"{round(value*1e6, decimals)}", "µ"]
    if abs(value) < 1:
        return [f"{round(value*1e3, decimals)}", "m"]
    if abs(value) < 1e3:
        return [f"{round(value, decimals)}", ""]
    if abs(value) < 1e6:
        return [f"{round(value*1e-3, decimals)}", "k"]
    if abs(value) < 1e9:
        return [f"{round(value*1e-6, decimals)}", "M"]
    if abs(value) < 1e12:
        return [f"{round(value*1e-9, decimals)}", "G"]
    return [f"{value}", ""]


class HCGridLayout(QGridLayout):
    """Places HCwidgets into a Gridlayout.

    This is a 2*columns (columns=1 by default) column grid with the label of the HCWidget in the left
    column and the widget itself in the right column.

    A special case is a HCDoubleSpinComboBox where an additional 3rd
    column is created.
    """

    def __init__(self, HCwidgets: list, offset: int = 0, columns: int = 1) -> None:
        super().__init__()
        has_double_spin = any(isinstance(w, HCDoubleSpinComboBox) for w in HCwidgets)
        width = 3 if has_double_spin else 2

        for i, w in enumerate(HCwidgets):
            col = i % columns
            row = i // columns
            self.addWidget(w.label, row + offset, 0 + col * width)
            if isinstance(w, HCDoubleSpinComboBox):
                self.addWidget(w.spin, row + offset, 1 + col * width)
                self.addWidget(w.combo, row + offset, 2 + col * width)
            else:
                self.addWidget(w, row + offset, 1 + col * width)


class HCMixin:
    """Connect a Qt element to a setting or command in the app.

    This mixin sets the app, instrument, and parameter values; connects to
    the app; and defines an hc_update function. The hc_update function
    still needs to be overwritten to connect to the actual widget
    since there might be custom code needed to do this.

    HCwidgets generally inherit from this class.

    Any parameter listed here will be automatically added to the app's
    auto_update list

    Parameters
    ----------
    app
       The main app
    instrument
       The name of the instrument
    parameter
       The name of the parameter
    auto_update
       Should the variable be added to the auto_update function. Set this
       to `False` in case you want to run this on a different schedule. In this
       case you need to create your own timer though and call the appropiate
       update function.
    """

    def __init__(self, **kwargs) -> None:
        app = kwargs.pop("app")
        instrument = kwargs.pop("instrument")
        parameter = kwargs.pop("parameter")
        auto_update = kwargs.pop("auto_update", True)

        self._visible = app.is_parameter(instrument, parameter)

        label = kwargs.pop("label", "")
        label_align = kwargs.pop("label_align", "center")
        colon = kwargs.pop("colon", True)
        if colon and label:
            label = f"{label}: "

        for arg in [app, instrument, parameter]:
            if arg is None:
                logger.error(
                    f"Widget '{label}' does not get correct arguments (app, instrument, parameter)"
                )

        self.app = app
        self.instrument = instrument
        self.parameter = parameter
        self.widget_hooks = []
        self.return_set_value = False

        super().__init__(**kwargs)

        self.name = label
        self.label = QLabel(label)

        if label_align == "right":
            self.label.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif label_align == "left":
            self.label.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif label_align == "center":
            self.label.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignCenter
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )

        if self._visible:
            # connect to app
            self.app.add_widget(self.instrument, self.parameter, self)
            if auto_update:
                self.app.add_auto_update_instrument_parameter(instrument, parameter)
        else:
            # hide widget, put parameter on list to skip when auto-updating
            logger.info(
                f"widget for {self.instrument}:{self.parameter} does not exist, hiding it."
            )
            self.app.add_skip_update_instrument_parameter(
                self.instrument, self.parameter
            )
            self.label.hide()
            self.hide()

    def add_widget_hook(self, function: Callable[[Any], Any]):
        """Add a hook function to be called when a value in a widgets gets updated from app._data."""

        self.widget_hooks.append(function)

    def hc_update(self):
        """Get the HC widget parameter value from the instrument and apply hooks to that value.

        When this function finishes running it calls the widget_update function which should be
        written for each HC widget. If this function has not been defined the default widget_update
        function raises an AttributeError.
        """

        # Don't update an HC widget if the focus is on the widget (if the widget has a focus)
        # This does not apply to HCOnOffButtons
        if (
            hasattr(self, "hasFocus")
            and self.hasFocus()
            and self.__class__.__name__ != "HCOnOffButton"
        ):
            logger.debug(f"'{self.name}' has focus, not updating")
            return

        value = self.app.get_instrument_parameter(
            self.instrument, self.parameter, return_set_value=self.return_set_value
        )
        value = call_hooks(self.widget_hooks, value)

        if value is None:
            logger.warning(
                f"Widget update for '{self.instrument}:{self.parameter}' failed."
            )
            return

        # every HCwidget has the following function to update itself.
        self.widget_update(value)

    def widget_update(self, value):
        raise AttributeError(
            f"HC widget for instrument {self.instrument}, parameter {self.parameter} "
            f"needs to define a update_widget function"
        )


class HCLabel(HCMixin, QLabel):
    """A simple indicator widget for a label (QLabel) and a value (QLabel)."""

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
        auto_update=True,
    ) -> None:
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            text="",
            auto_update=auto_update,
        )
        self.unit = unit
        self.use_prefix = use_prefix
        self.min_width = min_width

    def widget_update(self, value) -> None:
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
        else:
            text = str(text)
        if self.min_width:
            text = text.rjust(self.min_width)
        super().setText(text)


class HCLineEdit(HCMixin, QLineEdit):
    """A simple control widget with a label (QLabel) and an input box (QLineEdit).

    Parameters
    ----------
    return_set_value
        If True, retain the input in the HCLinEdit; if False, periodiccaly update
        the input with the parameter readout
    validator
        A QValidator object to be used to validate the lineedit input
    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        label_align: str = "left",
        return_set_value: bool = False,
        default_txt: str = "----",
        validator="default",
        auto_update=True,
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            auto_update=auto_update,
        )

        if validator == "default":
            self.validator = QDoubleValidator()
        else:
            self.validator = validator
        self.return_set_value = return_set_value

        if self.validator is not None:
            self.setValidator(self.validator)

        self.setText(default_txt)

        self.editingFinished.connect(self.value_change)

    def value_change(self) -> None:
        # https://forum.qt.io/topic/105335/qlineedit-editingfinished-called-twice-if-press-enter-key-actual-bug/8
        # Ignore second signal.
        # seems to be fixed in newer version, so we might be able to remove this eventually
        if not self.isModified():
            return
        self.setModified(False)

        value = self.text()
        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def widget_update(self, value) -> None:
        self.setText(value)


class HCDoubleSpinBox(HCMixin, QDoubleSpinBox):
    """A simple control widget with a label (QLabel) and an input box (QDoubleSpinBox)."""

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        label_align="left",
        auto_update=True,
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            auto_update=auto_update,
        )

        self.setValue(0)

        self.editingFinished.connect(self.value_change)

    def value_change(self) -> None:
        value = self.text()
        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def widget_update(self, value) -> None:
        self.setValue(float(value))


class HCPushButton(HCMixin, QPushButton):
    """A simple control widget with a push-button (QPushButton)."""

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
            auto_update=False,
        )

        self.clicked.connect(self.value_change)

    def value_change(self) -> None:
        self.app.call_instrument_command(self.instrument, self.parameter)

    def widget_update(self, value) -> None:
        pass


class HCOnOffButton(HCMixin, QPushButton):
    """A simple control widget with a push-button (QPushButton) with graphical indicators for on/off state.

    One also has the option of (only or additionally) introducing text to indicate
    on-off status.

    Parameters
    ----------
    show_text : bool
        Option to show a text indicator of the on-off status
    show_icon : bool
        Option to show an icon indicator of the on-off status
    text_checked : str
        Text to show when instrument parameter is 'On'
    text_unchecked : str
        Text to show when instrument parameter is 'Off'
    icon_checked : str
        Icon to show when instrument parameter is 'On'
    icon_unchecked : str
        Icon to show when instrument parameter is 'Off'
    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str = "",
        label_align: str = "left",
        show_text: bool = True,
        show_icon: bool = False,
        text_checked: str = "On",
        text_unchecked: str = "Off",
        text_pretext: str = "",
        icon_checked: str = "button-power-on.svg",
        icon_unchecked: str = "button-power-off.svg",
        show_set_text: bool = False,
        auto_update=True,
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            colon=False,
            auto_update=auto_update,
        )

        self.show_icon = show_icon
        self.show_text = show_text
        self.show_set_text = show_set_text

        if self.show_icon:
            self.icon_checked = load_icon(icon_checked)
            self.icon_unchecked = load_icon(icon_unchecked)
            self.icon_unknown = load_icon("button-power-unknown.svg")

        if self.show_text:
            self.text_checked = f"{text_pretext} {text_checked}"
            self.text_unchecked = f"{text_pretext} {text_unchecked}"
            self.text_unknown = f"{text_pretext} Unknown"

        self.clicked.connect(self.value_change)
        self.setCheckable(False)

        # set default to unkown state
        if self.show_icon:
            self.setIcon(self.icon_unknown)
        if self.show_text:
            self.setText(self.text_unknown)

    def is_true(self, value: Union[bool, str]) -> bool:
        """Handle multiple versions (of different data type and case) of the option 'True'."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value in ["True", "TRUE"]:
                return True
        return False

    def set_btn_state(self, value):
        """Change the icon and/or text display."""
        if self.show_icon:
            if self.is_true(value):
                self.setIcon(self.icon_checked)
            elif not self.is_true(value):
                self.setIcon(self.icon_unchecked)

        if self.show_text:
            if self.is_true(value):
                self.setText(self.text_checked)
            elif not self.is_true(value):
                self.setText(self.text_unchecked)

    def value_change(self) -> None:
        """Change value to opposite of current value."""
        value = self.app.get_instrument_parameter(self.instrument, self.parameter)
        new_value = not (value == "True")
        self.app.set_instrument_parameter(self.instrument, self.parameter, new_value)
        if self.show_set_text:
            self.set_btn_state(new_value)

    def widget_update(self, value):
        if not self.show_set_text:
            self.set_btn_state(value)


class HCOnOffIndicator(HCMixin, QLabel):
    """A simple control widget with a label (QLabel) image or text that indicates on/off state.

    Parameters
    ----------
    show_text : bool
        Option to show a text indicator of the on-off status; if show_text is
        True, the show_icon option will be ignored
    show_icon : bool
        Option to show an icon indicator of the on-off status
    text_checked : str
        Text to show when instrument parameter is 'On'
    text_unchecked : str
        Text to show when instrument parameter is 'Off'
    icon_checked : str
        Icon to show when instrument parameter is 'On'
    icon_unchecked : str
        Icon to show when instrument parameter is 'Off'
    tooltip : str
        Optional text to be displayed when mousing over the indicator
    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str = "",
        label_align: str = "left",
        show_text: bool = False,
        show_icon: bool = False,
        text_checked: str = "On",
        text_unchecked: str = "Off",
        icon_checked: str = "on-off-indicator-on.svg",
        icon_unchecked: str = "on-off-indicator-off.svg",
        tooltip: str = "",
        auto_update=True,
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            text=label,
            auto_update=auto_update,
        )

        self.label = QLabel(label)
        self.show_icon = show_icon
        self.show_text = show_text
        self.text_checked = text_checked
        self.text_unchecked = text_unchecked

        self.icon_checked = load_pixmap(icon_checked)
        self.icon_unchecked = load_pixmap(icon_unchecked)
        self.icon_unknown = load_pixmap("on-off-indicator-unknown.svg")

        # set default to unkown state
        if self.show_icon:
            self.setPixmap(self.icon_unknown)
        if self.show_text:
            self.setText("unkown")

        self.setMouseTracking(True)
        self.setToolTip(tooltip)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def sizeHint(self):
        if self.show_icon and not self.show_text:
            return QtCore.QSize(10, 20)
        return super().sizeHint()

    def is_true(self, value: Union[bool, str]) -> bool:
        """Handle multiple versions (of different data type and case) of the option 'True'."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value in ["True", "TRUE"]:
                return True
        return False

    def set_state(self, value):
        """Change the icon and/or text display."""
        if self.show_icon:
            if value == "True":
                self.setPixmap(self.icon_checked)
            elif value == "False":
                self.setPixmap(self.icon_unchecked)

        if self.show_text:
            if value == "True":
                self.setText(self.text_checked)
            elif value == "False":
                self.setText(self.text_unchecked)

    def widget_update(self, value):
        self.set_state(value)


class HCComboBox(HCMixin, QComboBox):
    """A simple control widget with a label (QLabel) and an input box (QComboBox).

    Parameters
    ----------
    items : list
        List of options to be place in the HCComboBox
    lookuptable : dict
        An optional table that can be used to convert the items in the HCComboBox
        into values to be sent to the instrument
    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        items: list,
        label_align: str = "left",
        lookuptable: Optional[dict] = None,
        upper: bool = False,
        auto_update=True,
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            auto_update=auto_update,
        )
        self.items = items
        self.upper = upper

        self.addItems(self.items)
        self.setCurrentText(self.items[0])

        self.lookuptable = lookuptable
        if self.lookuptable is not None:
            self.inverse_lookuptable = {
                value: key for key, value in lookuptable.items()
            }

        self.currentIndexChanged.connect(self.value_change)

    def value_change(self) -> None:
        value = self.currentText()
        if self.upper:
            value = value.upper()
        if self.lookuptable:
            value = self.lookuptable[value]
        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def widget_update(self, value) -> None:
        if self.lookuptable:
            value = self.inverse_lookuptable[value]
        for i in self.items:
            if value.casefold() == i.casefold():
                self.setCurrentText(i)
                break
        else:
            # try float values
            try:
                float(value)
            except (ValueError, TypeError):
                logger.error(
                    f"HCComboBox for '{self.parameter}': could not find '{value}' in item list and cannot test for float number."
                )
                return
            for i in self.items:
                if float(value) == float(i):
                    self.setCurrentText(i)
                    break
            else:
                logger.error(
                    f"HCComboBox for '{self.parameter}': could not find '{value}' in item list."
                )


class HCDoubleSpinComboBox(HCMixin):
    """A simple control widget with a label (QLabel) and two input boxes (QSpinBox, QComboBox).

    Parameters
    ----------
    units : dict
        A dictionary with keys that are units (str) and values that are the corresponding
        scale factors (float) to convert to the fundamental unit
    """

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        label: str,
        units: dict[str, float],
        label_align: str = "left",
        auto_update=True,
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            auto_update=auto_update,
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
        value = spin_value * combo_value

        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def widget_update(self, value) -> None:
        # Don't update an HC widget if the focus is on either the combobox or the spinbox
        if self.spin.hasFocus() or self.combo.hasFocus():
            logger.debug(f"'{self.name}' has focus, not updating")
            return

        combo_value = self.units[self.combo.currentText()]
        value = float(value) / combo_value
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
        auto_update=True,
    ):
        super().__init__(
            app=app,
            instrument=instrument,
            parameter=parameter,
            label=label,
            label_align=label_align,
            auto_update=auto_update,
        )

        self.valueChanged.connect(self.value_change)

    def value_change(self) -> None:
        value = self.value()
        self.app.set_instrument_parameter(self.instrument, self.parameter, value)

    def widget_update(self, value) -> None:
        self.setValue(int(value))


class HCHeader(QLabel):
    """Display an image as a header."""

    def __init__(self, icon_name):
        super().__init__()
        self.setPixmap(load_pixmap(icon_name))
        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignHCenter
        )


class HCFixedLabel(HCMixin, QLabel):
    """A simple control widget with a label (QLabel)that fixes its width to the given initial string."""

    def __init__(
        self,
        app,
        instrument: str,
        parameter: str,
        init_label: str = "",
        unit: str = "",
        use_prefix: bool = True,
        color: str = None,
        fontsize: int = 18,
        bold: bool = False,
        label_align: str = "center",
        auto_update=True,
    ):
        super().__init__(
            app=app, instrument=instrument, parameter=parameter, auto_update=auto_update
        )

        self.unit = unit
        self.use_prefix = use_prefix

        super().setText(f"{init_label}")

        font = QFont()
        font.setPointSize(fontsize)
        font.setBold(bold)
        self.setFont(font)

        fm = QFontMetrics(self.font())
        self.setFixedWidth(fm.width(init_label))

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if color is not None:
            self.setStyleSheet(
                f"color: white;background-color:{color}; padding: 5px;border: 1px solid black;"
            )

        # Align the label
        if label_align == "right":
            self.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif label_align == "left":
            self.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        elif label_align == "center":
            self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def widget_update(self, value) -> None:
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
        super().setText(text)
