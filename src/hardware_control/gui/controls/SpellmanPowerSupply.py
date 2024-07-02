"""
    .. image:: /images/SpellmanSL120P300.png
"""
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import QGroupBox, QLabel, QMessageBox, QCheckBox, QPushButton
from PyQt6.QtCore import Qt

from hardware_control.gui.widgets import HCFixedLabel, HCLineEdit, HCGridLayout
from hardware_control.base.hooks import scaling_converter, add_offset, Ramp

"""Reads out: voltage, current, interlock status and sets the voltage"""



class SpellmanPowerSupply(QGroupBox):
    """Control program for a Spellman Power Supply.

    See Also
    --------
    hardware_control.instruments.spellman.Spellman_SL
    """


    def __init__(
        self,
        app,
        instrument_name: str,
        widget_name: str = "Spellman Power Supply",
        #milliamps?, https://www.spellmanhv.com/en/high-voltage-power-supplies/SL
        max_current=2.5,
    ):
        super().__init__(widget_name)

        self.app = app
        self.instrument = instrument_name
        self.max_current = max_current
        self.showed_cooling_warning = False
        self.interlocked = False

        # Interlock variables
        self.bypass_target_HV = False
        self.HV_reason = []
        self.i = 0  # a counter for the update_interlock function
        self.interlock_timer = QTimer()
        self.interlock_timer.timeout.connect(self.update_interlock)
        self.interlock_timer.start(100)

        # Current readout
        self.current_read = HCFixedLabel(
            self.app,
            self.instrument,
            "I_OUT",
            init_label="+0.000000  A",
            unit="A",
            label_align="left",
        )
        self.app.add_hook(
            self.instrument,
            "I_OUT",
            "post_read_hooks",
            scaling_converter(3e-4),
        )
        self.app.add_hook(
            self.instrument, "I_OUT", "post_read_hooks", add_offset(6.9e-6)
        )
        self.app.add_hook(
            self.instrument,
            "I_OUT",
            "post_read_hooks",
            self.max_current_check,
        )

        # Voltage readout
        self.voltage_read = HCFixedLabel(
            self.app,
            self.instrument,
            "V_OUT",
            init_label="+0.000000 kV",
            unit="kV",
            use_prefix=False,
            label_align="left",
        )
        self.app.add_hook(
            self.instrument,
            "V_OUT",
            "post_read_hooks",
            scaling_converter(120.0 / 10.0),
        )
        self.app.add_hook(
            self.instrument, "V_OUT", "post_read_hooks", add_offset(0.2)
        )

        # Voltage setters
        # Lineedit that sets voltage value
        self.voltage_input = HCLineEdit(
            self.app,
            self.instrument,
            "V_SET",
            "Voltage",
        )
        # Button that zeroes voltage
        self.zero_voltage_btn = QPushButton("Zero Voltage")
        self.zero_voltage_btn.clicked.connect(self.zero_voltage)

        # Add a warning hook when ramping up from zero
        self.app.add_hook(
            self.instrument, "V_SET", "pre_set_hooks", self.setter_warning()
        )
        # Convert voltage input into the power supply's units
        high_voltage_ramp = Ramp(
            self.app,
            "Spellman",
            set_parameter="V_SET",
            read_parameter="V_OUT",
            ramp_speed=1,
            timer_step=500,
            min_value=30,
            epsilon=0.1,
        )
        self.app.add_hook(
            self.instrument, "SET_VOLTAGE", "pre_set_hooks", high_voltage_ramp
        )
        self.app.add_hook(
            self.instrument,
            "V_SET",
            "pre_set_hooks",
            scaling_converter(10 / 120.0),
        )

        self.voltage_input.setValidator(QDoubleValidator(0, 101, 3))

        # Interlock widgets
        self.interlock_label = QLabel("Ready to operate")
        self.HV = QLabel("HV not-interlocked")
        self.target_bypass = QCheckBox("Suppressor-HV bypass")

        # Set layout of the Spellman main app
        self.main_layout = HCGridLayout([self.voltage_input])
        self.main_layout.addWidget(self.voltage_read, 0, 2, 1, 1)
        self.main_layout.addWidget(self.zero_voltage_btn, 0, 3, 1, 1)
        self.main_layout.addWidget(self.target_bypass, 1, 0, 1, 3)
        self.main_layout.addWidget(self.current_read, 1, 2)
        self.main_layout.addWidget(self.interlock_label, 2, 0, 1, 3)
        self.main_layout.addWidget(self.HV, 3, 0, 1, 3)
        self.setLayout(self.main_layout)

        self.update_readout()

    def update_readout(self):
        """Update the readout values from the Spellman."""
        self.app.add_auto_update_instrument_parameter(
            self.instrument, f"I_OUT"
        )
        self.app.add_auto_update_instrument_parameter(
            self.instrument, f"V_OUT"
        )

    def zero_voltage(self):
        """Immediately set high voltage to zero."""
        self.app.set_instrument_parameter(
            self.instrument,
            "V_SET",
            0,
            priority=2,
        )
        self.voltage_input.setText("0.0")

    def setter_warning(self):
        """Throw a warning (via a hook) when ramping up the Spellman voltage from zero."""

        def warning_hook(value):
            new_value = float(value)
            if not self.showed_cooling_warning and new_value > 0.0:
                msg = QMessageBox(
                    QMessageBox.Warning,
                    "Warning",
                    "Air, Fluorinert, and Water need to be on!",
                    parent=self,
                )
                msg.exec()
                self.showed_cooling_warning = True
            elif new_value == 0 and self.showed_cooling_warning:
                self.showed_cooling_warning = False  # need to show again
            return value

        return warning_hook

    def set_interlock(self, value):
        """Interlock the voltage setting capability.

        This command does nothing if value of self.interlocked has not changed.
        """
        if value == self.interlocked:
            return

        self.interlocked = value
        if self.interlocked:
            self.interlock_label.setText("Blocked by suppressor")
            self.app.set_instrument_parameter(self.instrument, "V_SET", 0)
            self.voltage_input.setEnabled(False)
            self.voltage_input.setStyleSheet("background-color: grey")
        else:
            self.interlock_label.setText("Ready to operate")
            self.voltage_input.setEnabled(True)
            self.voltage_input.setStyleSheet("background-color: white")

    def update_interlock(self):
        """Check for interlocks.

        This function should be fast and most functions should be no-ops if
        nothing has changed.
        """
        self.i += 1

        self.bypass_target_HV = self.target_bypass.checkState()
        if self.bypass_target_HV == Qt.CheckState.Checked:
            self.set_interlock(False)
            if " Bypass" not in self.HV_reason:
                self.HV_reason.insert(0, " Bypass")
        else:
            if " Bypass" in self.HV_reason:
                self.HV_reason.remove(" Bypass")
            try:
                value = float(self.app.get_instrument_parameter("caen", "CH3_V_OUT"))
            except TypeError:
                value = 0

            if value < 200:
                self.set_interlock(True)
                if " Target not biased above 200 V" not in self.HV_reason:
                    self.HV_reason.append(" Target not biased above 200 V")
            else:
                self.set_interlock(False)
                if " Target not biased above 200 V" in self.HV_reason:
                    self.HV_reason.remove(" Target not biased above 200 V")

        if self.i % 20 == 0:
            self.i = 0
            if self.HV_reason:
                reasons = ", ".join(self.HV_reason)
                self.HV.setText(f"HV interlocked because: {reasons}")
            else:
                self.HV.setVisible(False)

    def max_current_check(self, value):
        """If current is greater than max current change background color."""
        if value >= self.max_current:
            self.zero_voltage()

        return value