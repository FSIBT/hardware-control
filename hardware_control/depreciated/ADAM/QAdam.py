import time

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
)

from .control import Adam


class AdamCommunication(QObject):
    """handle the communications to the Adam in its own thread to free the GUI"""

    new_values_read = pyqtSignal(float, float, float)
    toggle_enable = pyqtSignal(bool)

    def __init__(self, IP, dummy=False, parent=None):
        super().__init__()
        self.parent = parent
        self.instrument = Adam(IP, dummy=dummy)
        self.online = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.instrument.try_connect)
        self.timer.timeout.connect(self.enabled)
        self.timer.timeout.connect(self.read)
        self.timer.start(1000)

        if self.parent:
            self.parent.write_value.connect(self.write)

    @pyqtSlot()
    def stop_thread(self):
        self.timer.stop()

    @pyqtSlot()
    def enabled(self):
        if self.online != self.instrument.online:
            self.online = self.instrument.online
            self.toggle_enable.emit(self.online)

    @pyqtSlot()
    def read(self):
        if self.online:
            current, voltage, pressure = self.instrument.read()
            # normalize values from raw readout, correct some zero offset
            current = current / 10 * 3e-3 + 8.1e-6  # 10V = 100% = 3mA
            voltage = voltage / 10 * 100e3 + 420  # 10V = 100 kV
            pressure = pressure * 100
            self.new_values_read.emit(current, voltage, pressure)

    @pyqtSlot(int, float)
    def write(self, channel, value):
        if self.online:
            # make sure value is valid
            if value < 0 or value > 80:
                print(
                    "WARNING: Adam: Value out of range! channel:{channel} value={value}"
                )

            # scale value to 0-10 V
            value /= 10

            self.instrument.write(channel, value)


class AdamControl(QGroupBox):
    """Control the Adam"""

    write_value = pyqtSignal(int, float)

    def __init__(self, IP, parent=None, dummy=False, hvlimit=True):
        super().__init__("Adam")
        self.IP = IP
        self.voltage_setpoint = 0
        self.voltage_setpoint_last = 0
        self.voltage = 0
        self.current = 0
        self.pressure = 0
        self.interlocked = False
        self.hvlimit = hvlimit
        self.ramp_rate = 0.5  # kV/s
        self.last_ramp = time.time()

        self.parent = parent
        self.hbox = QHBoxLayout()

        # list values
        self.value_box = QVBoxLayout()
        self.voltage_label = QLabel("0 V")
        self.current_label = QLabel("0 A")
        self.voltage_label.setAlignment(QtCore.Qt.AlignCenter)
        self.current_label.setAlignment(QtCore.Qt.AlignCenter)

        self.pressure_label = QLabel("0 mTorr")
        self.pressure_label.setAlignment(QtCore.Qt.AlignCenter)

        self.value_box.addWidget(self.voltage_label)
        self.value_box.addWidget(self.current_label)
        self.value_box.addWidget(self.pressure_label)
        self.value_box.addStretch(1)

        # controls
        self.setbutton = QPushButton("Set [in kV]")
        self.setbutton.clicked.connect(self.set)

        self.setbutton_zero = QPushButton("Set to 0 kV")
        self.setbutton_zero.clicked.connect(self.set_to_zero)

        self.input = QLineEdit()
        self.input.setText("0")
        self.input.setFixedWidth(100)
        if self.hvlimit:
            # during operation, one should alwyas stay above 40
            self.input.setValidator(QDoubleValidator(40, 80, 3))
        else:
            self.input.setValidator(QDoubleValidator(0, 80, 3))
        self.input.returnPressed.connect(self.set)

        self.label = QLabel("")

        self.controls = QVBoxLayout()

        self.controls.addWidget(self.input)
        self.controls.addWidget(self.setbutton)
        self.controls.addWidget(self.setbutton_zero)
        self.controls.addWidget(self.label)
        self.controls.addStretch(1)

        # indicators
        self.indicators = QVBoxLayout()
        self.interlock_label = QLabel("not-interlocked")
        self.indicators.addWidget(self.interlock_label)

        self.hbox.addLayout(self.value_box)
        self.hbox.addLayout(self.controls)
        self.hbox.addLayout(self.indicators)
        self.hbox.addStretch(1)

        if dummy:
            self.label.setText("dummy")

        self.setLayout(self.hbox)

        # start communication thread in the background
        self.comm_thread = QThread()
        self.comm = AdamCommunication(IP, dummy=dummy, parent=self)
        self.comm.toggle_enable.connect(self.toggle_enable)
        self.comm.new_values_read.connect(self.read)
        self.parent.prepare_shutdown.connect(self.comm.stop_thread)
        self.comm.moveToThread(self.comm_thread)
        self.comm_thread.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.ramp)
        self.timer.start(200)

        # start out disabled
        self.toggle_enable(False)

    @pyqtSlot(bool)
    def toggle_enable(self, status):
        self.setEnabled(status)

    def ramp(self):
        """adjust the voltage, so that we only get a gentle ramp up/down

        use a ramp rate of max 500 per step, only ramp, iff we are >50V off from the setpoint.

        some values are in kV, some in V, so we need to adjust accordingly
        """

        # update time
        current_time = time.time()
        dt = current_time - self.last_ramp
        self.last_ramp = current_time

        # check if ramping is needed
        if abs(self.voltage_setpoint_last - self.voltage_setpoint) < 10e-3:
            return

        # no need to ramp for small values
        if self.voltage_setpoint <= 30:
            self.write_value.emit(0, self.voltage_setpoint)
            self.voltage_setpoint_last = self.voltage_setpoint
            return

        if self.voltage_setpoint_last < 30:
            self.write_value.emit(0, 30)
            self.voltage_setpoint_last = 30
            return

        # calculate increase, set some max/min values in kV/s
        ramp_rate = min(self.ramp_rate * dt, 0.5)

        diff = self.voltage_setpoint - self.voltage_setpoint_last
        diff = min(ramp_rate, diff)
        diff = max(-ramp_rate, diff)

        new_value = self.voltage_setpoint_last + diff
        self.write_value.emit(0, new_value)  # in kV
        self.voltage_setpoint_last = new_value

    def set(self):
        self.voltage_setpoint = float(self.input.text())

    def set_to_zero(self):
        self.input.setText("0")
        self.write_value.emit(0, 0)
        self.voltage_setpoint = 0
        self.voltage_setpoint_last = 0

    def try_reconnect(self):
        # self.Adam.try_connect()
        # self.setEnabled(self.Keysight.online)
        pass

    def set_interlock(self, value):
        """Interlock the voltage setting capability

        no-op if the value hasn't changed
        """
        if value == self.interlocked:
            return

        self.interlocked = value
        if self.interlocked:
            self.interlock_label.setText("interlocked")
            self.set_to_zero()
            self.input.setEnabled(False)
            self.setbutton.setEnabled(False)
        else:
            self.interlock_label.setText("non-interlocked")
            self.input.setEnabled(True)
            self.setbutton.setEnabled(True)

    @pyqtSlot(float, float, float)
    def read(self, current, voltage, pressure):

        self.voltage = voltage
        self.current = current
        self.pressure = pressure

        if abs(self.voltage) > 1e3:
            self.voltage_label.setText(f"{self.voltage*1e-3:.3f} kV")
        else:
            self.voltage_label.setText(f"{self.voltage:.3f} V")

        if abs(self.current) < 1e-3:
            self.current_label.setText(f"{self.current*1e6:.3f} µA")
        elif abs(self.current) < 1:
            self.current_label.setText(f"{self.current*1e3:.3f} mA")
        else:
            self.current_label.setText(f"{self.current:.3f} A")
        self.pressure_label.setText(f"{self.pressure:.3f} mTorr")

    def get_header(self):
        return "HV-Voltage[V] HV-Current[A] Pressure[mTorr]"

    def get_values(self):
        return self.voltage, self.current, self.pressure

    def close(self):
        self.Adam.close()
