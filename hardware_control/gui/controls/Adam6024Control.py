from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QGroupBox,
    QLabel,
    QMessageBox,
)

from ..widgets import HCFixedLabel, HCLineEdit, HCGridLayout
from ...base.hooks import scaling_converter, add_offset


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
            init_label="+0.000  Torr",
            unit="Torr",
            label_align="left",
        )
        # Current readout
        self.current_read = HCFixedLabel(
            self.app,
            self.instrument,
            "CH1_READ_VOLTAGE",
            init_label="+0.000  A",
            unit="A",
            label_align="left",
        )
        # Voltage readout
        self.voltage_read = HCFixedLabel(
            self.app,
            self.instrument,
            "CH2_READ_VOLTAGE",
            init_label="+0.000  V",
            unit="V",
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
            self.instrument, "CH0_SET_VOLTAGE", "pre_set_hooks", scaling_converter(100)
        )

        # Current setter
        self.current_input = HCLineEdit(
            self.app,
            self.instrument,
            "CH1_SET_VOLTAGE",
            "Current",
        )
        self.app.add_hook(
            self.instrument, "CH1_SET_VOLTAGE", "pre_set_hooks", scaling_converter(3e-4)
        )
        self.app.add_hook(
            self.instrument,
            "CH1_SET_VOLTAGE",
            "pre_set_hooks",
            add_offset(8.1e-6),
        )

        # Voltage setter
        self.voltage_input = HCLineEdit(
            self.app,
            self.instrument,
            "CH2_SET_VOLTAGE",
            "Voltage",
        )
        self.app.add_hook(
            self.instrument, "CH2_SET_VOLTAGE", "pre_set_hooks", scaling_converter(1e4)
        )
        self.app.add_hook(
            self.instrument,
            "CH2_SET_VOLTAGE",
            "pre_set_hooks",
            add_offset(420),
        )

        # Interlock indicator
        self.interlock_label = QLabel("Not Interlocked")

        self.main_layout = HCGridLayout(
            [self.pressure_input, self.current_input, self.voltage_input]
        )
        self.main_layout.addWidget(self.pressure_read, 0, 2)
        self.main_layout.addWidget(self.current_read, 1, 2)
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
        # here we query the instrument manually, this could also be
        # done using functionallity int the app.
        for channel in [0, 1, 2]:
            self.app.update_instrument_parameter(
                self.instrument, f"CH{channel}_READ_VOLTAGE"
            )
