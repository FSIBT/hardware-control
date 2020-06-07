from PyQt5 import QtCore
from PyQt5.Qt import QMutex, QMutexLocker
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QPushButton,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
)

from .control import E36313A
from ..base import QOnOff, QFixedLabel


class ChannelDisplay(QVBoxLayout):
    def __init__(self, name, color):
        super().__init__()
        self.name = name
        self.voltage = 0
        self.current = 0

        self.voltage_label = QFixedLabel("+000.0000 xX", color)
        self.current_label = QFixedLabel("+000.0000 xX", color)

        self.addWidget(self.voltage_label)
        self.addWidget(self.current_label)
        self.addStretch(1)

    def update(self, voltage, current):
        self.voltage = float(voltage)
        self.current = float(current)
        if abs(self.voltage) < 1e-3:
            self.voltage_label.setText(f"{voltage*1e3:8.3f} mV")
        else:
            self.voltage_label.setText(f"{voltage:8.3f}  V")
        if abs(self.current) < 1e-3:
            self.current_label.setText(f"{self.current*1e6:8.3f} µA")
        elif abs(self.current) < 1:
            self.current_label.setText(f"{self.current*1e3:8.3f} mA")
        else:
            self.current_label.setText(f"{self.current:8.3f}  A")

    def get_header(self):
        return f"{self.name}-Voltage[V] {self.name}-Current[A]"

    def get_values(self):
        return [self.voltage, self.current]

    def __repr__(self):
        return f"{self.name}: {self.voltage} V {self.current} A"


class KeysightControl(QGroupBox):
    """Control the Keysight"""

    def __init__(self, parent=None, rm=None, dummy=False):
        super().__init__("Keysight")
        self.parent = parent

        self.mutex = QMutex()

        self.hbox = QVBoxLayout()

        self.onoff = QOnOff(self.on, self.off)

        self.hbox.addWidget(self.onoff)

        self.channeldisplay = QGridLayout()
        self.CH1 = ChannelDisplay("Ch1", "maroon")
        self.CH2 = ChannelDisplay("CH2", "green")
        self.CH3 = ChannelDisplay("CH3", "blue")
        self.channels = [self.CH1, self.CH2, self.CH3]
        for i, c in enumerate(self.channels):
            self.channeldisplay.addLayout(c, 1, i)
        self.hbox.addLayout(self.channeldisplay)

        self.heater = QHBoxLayout()

        self.setbutton = QPushButton("Set Heater Current")
        self.setbutton.clicked.connect(self.set)

        self.input = QLineEdit()
        self.input.setText("0")
        self.input.setFixedWidth(100)
        # max 2 amps
        self.input.setValidator(QDoubleValidator(0, 2, 3))
        self.input.returnPressed.connect(self.set)

        self.label = QLabel("")

        self.heater.addWidget(self.label)
        self.heater.addWidget(self.setbutton)
        self.heater.addWidget(self.input)

        self.hbox.addLayout(self.heater)

        if rm is None or dummy:
            self.label.setText("no RM")
            self.Keysight = E36313A(ResourceManager=None, dummy=dummy)
        else:
            self.Keysight = E36313A(rm)
            self.setEnabled(self.Keysight.online)

        # check status of instrument
        if self.Keysight.is_on():
            self.onoff.set_icon_on()
        else:
            self.onoff.set_icon_off()

        # set correct limits
        # first read in current values
        self.read()
        values = self.get_values()
        voltageCH2 = values[2]
        if voltageCH2 > 4.5:
            self.Keysight.setup_preamp(init=False)
        else:
            self.Keysight.setup_preamp(init=True)

        self.setLayout(self.hbox)

        # try to update figures every second
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.try_reconnect)
        timer.start(1000)

    def try_reconnect(self):
        self.Keysight.try_connect()
        self.setEnabled(self.Keysight.online)

    def on(self):
        with QMutexLocker(self.mutex):
            self.Keysight.on()

    def off(self):
        with QMutexLocker(self.mutex):
            self.Keysight.off()

    def set(self):
        value = self.input.text()
        value = float(value)
        with QMutexLocker(self.mutex):
            self.Keysight.set_heater(value)

    def read(self):
        with QMutexLocker(self.mutex):
            I, V = self.Keysight.get_values()

        for ch, i, v in zip(self.channels, I, V):
            ch.update(v, i)

    def get_header(self):
        return " ".join([ch.get_header() for ch in self.channels])

    def get_values(self):
        out = []
        for ch in self.channels:
            out.extend(ch.get_values())
        return out

    def close(self):
        self.Keysight.close()
