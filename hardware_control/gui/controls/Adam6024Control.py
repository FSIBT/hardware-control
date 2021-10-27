from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QGroupBox,
    QGridLayout,
    QLabel,
    QMessageBox,
)

from ..widgets import HCFixedLabel, HCLineEdit
from ...base.hooks import add_offset, scaling_converter


class Adam6024Control(QGroupBox):
    """Control the Adam"""

    def __init__(
        self,
        app,
        instrument_name: str,
        widget_name: str = "Adam 6024",
    ):
        super().__init__(widget_name)

        self.app = app
        self.instrument = instrument_name
        self.voltage_setpoint = 0
        self.interlocked = False

        # Pressure readout
        self.pressure_read = HCFixedLabel(
            self.app,
            self.instrument,
            "CH0_READ_VOLTAGE",
            init_label="+0.000 xXxxx",
            label_align="left",
        )
        # Current readout
        self.current_read = HCFixedLabel(
            self.app,
            self.instrument,
            "CH1_READ_VOLTAGE",
            init_label="+0.000 xX",
            label_align="left",
        )
        # Voltage readout
        self.voltage_read = HCFixedLabel(
            self.app,
            self.instrument,
            "CH2_READ_VOLTAGE",
            init_label="+0.000 xX",
            label_align="left",
        )

        # Pressure setter
        self.pressure_input = HCLineEdit(
            self.app,
            self.instrument,
            "CH0_SET_VOLTAGE",
            "Pressure",
        )
        self.app.add_hook(
            self.instrument,
            "CH0_SET_VOLTAGE",
            "pre_set_hooks",
            lambda value: self.scale(100, value),
        )

        # Current setter
        self.current_input = HCLineEdit(
            self.app,
            self.instrument,
            "CH1_SET_VOLTAGE",
            "Current",
        )
        self.app.add_hook(
            self.instrument,
            "CH1_SET_VOLTAGE",
            "pre_set_hooks",
            lambda value: self.scale(3e-4, value),
        )
        self.app.add_hook(
            self.instrument,
            "CH1_SET_VOLTAGE",
            "pre_set_hooks",
            lambda value: self.add_offset(8.1e-6, value),
        )

        # Voltage setter
        self.voltage_input = HCLineEdit(
            self.app,
            self.instrument,
            "CH2_SET_VOLTAGE",
            "Voltage",
        )
        self.app.add_hook(
            self.instrument,
            "CH2_SET_VOLTAGE",
            "pre_set_hooks",
            lambda value: self.scale(1e4, value),
        )
        self.app.add_hook(
            self.instrument,
            "CH2_SET_VOLTAGE",
            "pre_set_hooks",
            lambda value: self.add_offset(420, value),
        )

        # Interlock indicator
        self.interlock_label = QLabel("Not Interlocked")

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.pressure_input.label, 0, 0)
        self.main_layout.addWidget(self.pressure_input, 0, 1)
        self.main_layout.addWidget(self.pressure_read, 0, 2)
        self.main_layout.addWidget(self.current_input.label, 1, 0)
        self.main_layout.addWidget(self.current_input, 1, 1)
        self.main_layout.addWidget(self.current_read, 1, 2)
        self.main_layout.addWidget(self.voltage_input.label, 2, 0)
        self.main_layout.addWidget(self.voltage_input, 2, 1)
        self.main_layout.addWidget(self.voltage_read, 2, 2)
        self.main_layout.addWidget(self.interlock_label, 3, 0)
        self.setLayout(self.main_layout)

        # Create timer to query instrument
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.app.globalRefreshRate)

    def setter_warning(self):
        if self.voltage_setpoint == 0:
            msg = QMessageBox(
                QMessageBox.Warning,
                "Warning",
                "Air, Fluorinert, and Water need to be on!",
                parent=self,
            )
            msg.exec_()

    def set_interlock(self, value):
        """Interlock the voltage setting capability.

        Does nothing if value of self.interlocked has not changed.
        """
        if value == self.interlocked:
            return

        self.interlocked = value
        if self.interlocked:
            self.interlock_label.setText("Interlocked")
            self.app.set_instrument_parameter(
                self.instrument, f"CH{channel}_SET_VOLTAGE", 0
            )
            self.voltage_input.setEnabled(False)
            self.voltage_input.setStyleSheet("background-color: grey")
        else:
            self.interlock_label.setText("Not Interlocked")
            self.voltage_input.setEnabled(True)
            self.voltage_input.setStyleSheet("background-color: white")

    def update_readout(self):
        for channel in [0, 1, 2]:
            self.app.update_instrument_parameter(
                self.instrument, f"CH{channel}_READ_VOLTAGE"
            )

        voltage_val = float(self.voltage_read.text()[:-3])
        self.voltage_setpoint = voltage_val
        if abs(voltage_val) > 1e3:
            self.voltage_read.unit = "kV"
            self.voltage_read.setText(f"{voltage_val*1e-3:.3f}")
        else:
            self.voltage_read.unit = " V"
            self.voltage_read.setText(f"{voltage_val:.3f}")

        current_val = float(self.current_read.text()[:-3])
        if abs(current_val) < 1e-3:
            self.current_read.unit = "µA"
            self.current_read.setText(f"{current_val*1e6:.3f}")
        elif abs(current_val) < 1:
            self.current_read.unit = "mA"
            self.current_read.setText(f"{current_val*1e3:.3f}")
        else:
            self.current_read.unit = " A"
            self.current_read.setText(f"{current_val:.3f}")

        pressure_val = float(self.pressure_read.text()[:-6])
        self.pressure_read.unit = "mTorr"
        self.pressure_read.setText(f"{pressure_val:.3f}")

    def add_offset(self, offset, value):
        """Convert `value` to float and add `offset` to it."""
        value = float(value) + float(offset)
        return value

    def scale(self, scale_factor, value):
        """Convert `value` to float and add `offset` to it."""
        value = float(value) * float(scale_factor)
        return value
