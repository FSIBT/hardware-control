# -*- coding: utf-8 -*-
from .control import Sairem

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QSizePolicy, QFormLayout,
                             QPushButton, QHBoxLayout, QLabel, QLineEdit)
from PyQt5.Qt import QMutex, QMutexLocker

from ..QHelper import QOnOff


class SairemCommunication(QObject):
    """Handle the communication with the instrument in a separate thread"""

    new_values_read = pyqtSignal(float, float, float, float, bool, bool, bool)
    toggle_enable = pyqtSignal(bool)

    def __init__(self, dummy=False, parent=None):
        super().__init__()
        self.parent = parent
        self.instrument = Sairem(dummy=dummy)
        self.online = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.instrument.try_connect)
        self.timer.timeout.connect(self.enabled)
        self.timer.timeout.connect(self.read)
        self.timer.start(500)

        if self.parent:
            self.parent.write_value.connect(self.write)
            self.parent.toggle_on_off.connect(self.toggle_on_off)
            self.parent.toggle_autotuning_on_off.connect(self.toggle_autotune)

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
            setpoint = self.instrument.read_power()
            frequency = self.instrument.read_frequency()
            forward_power = self.instrument.read_forward_power()
            reflected_power = self.instrument.read_reflected_power()
            mw_on = self.instrument.is_on()
            faults = self.instrument.read_fault_status()
            auto_on = self.instrument.is_autotuning()

            if faults:
                # check modbus address to get error detail
                for i in [104,105, 108,109]:
                    out = self.instrument.read(i)
                    if i == 109:
                        if out & 4:
                            print('ERROR: Sairem: max reflected power reached!')
                            value = self.instrument.read_reflected_power()
                            print(f'    reflected power currently set to {value}')
                        elif out & 8:
                            print('ERROR: Sairem: communication error!')

            self.new_values_read.emit(setpoint, frequency, forward_power,
                                      reflected_power, mw_on, faults, auto_on)

    @pyqtSlot(str, float)
    def write(self, name, value):
        if self.online:
            if name == 'power':
                self.instrument.set_power(value)
            elif name == 'frequency':
                self.instrument.set_frequency(value)
            elif name == 'reset_faults':
                self.instrument.reset_faults()
            elif name == 'reflected_power':
                self.instrument.set_reflected_power(value)

    @pyqtSlot(bool)
    def toggle_on_off(self, status):
        if status:
            # setting the reflected power over here to 100, since
            # trying to set it at startup resulted in communication
            # errors and the command never executed
            self.instrument.set_reflected_power(100)
            self.instrument.on()
        else:
            self.instrument.off()

    @pyqtSlot(bool)
    def toggle_autotune(self, status):
        if status:
            self.instrument.autotuning_on()
        else:
            self.instrument.autotuning_off()


class SairemControl(QGroupBox):
    """Control the Sairem"""

    write_value = pyqtSignal(str, float)
    toggle_on_off = pyqtSignal(bool)
    toggle_autotuning_on_off = pyqtSignal(bool)

    def __init__(self, parent=None, dummy=False):
        super().__init__('Sairem')

        self.parent = parent
        self.setpoint = 0
        self.frequency = 2450.0
        self.forward = 0
        self.reflected = 0
        self.faults = None
        self.mw_on = False
        self.autotune_value = False
        self.init = False

        # start communication thread in the background
        self.comm_thread = QThread()
        self.comm = SairemCommunication(dummy=dummy, parent=self)
        self.comm.toggle_enable.connect(self.toggle_enable)
        self.comm.new_values_read.connect(self.read)
        self.parent.prepare_shutdown.connect(self.comm.stop_thread)
        self.comm.moveToThread(self.comm_thread)
        self.comm_thread.start()

        self.hbox = QVBoxLayout()
        self.top = QHBoxLayout()

        self.onoff = QOnOff(self.toggle_on_off)
        self.onoff.offText = 'MW off'
        self.onoff.onText = 'MW on'
        self.top.addWidget(self.onoff)

        self.faults_indicator = QLabel('no faults')
        self.reset_faults_button = QPushButton('Reset Faults')
        self.reset_faults_button.clicked.connect(self.reset_faults)

        self.top.addWidget(self.faults_indicator)
        self.top.addWidget(self.reset_faults_button)
        self.hbox.addLayout(self.top)

        self.inputs = QFormLayout()

        self.power_input = QLineEdit()
        self.power_input.setValidator(QIntValidator(0, 200))
        self.power_input.returnPressed.connect(self.set_power)

        self.frequency_input = QLineEdit()
        self.frequency_input.setText('2450')
        self.frequency_input.setValidator(QDoubleValidator(2400, 2500, 1))
        self.frequency_input.returnPressed.connect(self.set_frequency)

        self.power_indicator = QLabel('123')
        self.reflected_indicator = QLabel('321')
        self.forward_indicator = QLabel('321')
        self.frequency_indicator = QLabel('321')

        self.inputs.addRow('Power (set)', self.power_input)
        self.inputs.addRow('Frequency (set)', self.frequency_input)
        self.inputs.addRow('Power', self.power_indicator)
        self.inputs.addRow('Reflected Power', self.reflected_indicator)
        self.inputs.addRow('Forward Power', self.forward_indicator)
        self.inputs.addRow('Frequency', self.frequency_indicator)

        self.hbox.addLayout(self.inputs)

        self.autotune = QOnOff(self.toggle_autotuning_on_off)
        self.autotune.offText = 'Autotune off'
        self.autotune.onText = 'Autotune on'
        self.hbox.addWidget(self.autotune)

        self.hbox.addStretch(1)

        self.setLayout(self.hbox)

        # start out disabled
        self.toggle_enable(False)

        self.write_value.emit('reflected_power', 100)

    @pyqtSlot(bool)
    def toggle_enable(self, status):
        self.setEnabled(status)

    def reset_faults(self):
        self.write_value.emit('reset_faults', 0)

    def set_power(self):
        value = int(self.power_input.text())
        self.write_value.emit('power', value)

    def set_frequency(self):
        value = float(self.frequency_input.text())
        self.write_value.emit('frequency', value)

    @pyqtSlot(float, float, float, float, bool, bool, bool)
    def read(self, setpoint, frequency, forward, reflected, mw_on, faults, autotune):
        self.setpoint = setpoint
        self.frequency = frequency
        self.forward = forward
        self.reflected = reflected
        self.mw_on = mw_on
        self.faults = faults
        self.autotune_value = autotune

        self.reflected_indicator.setText(f'{self.reflected} W')
        self.forward_indicator.setText(f'{self.forward} W')
        self.frequency_indicator.setText(f'{self.frequency} MHz')
        self.power_indicator.setText(f'{self.setpoint} W')
        if self.faults:
            self.faults_indicator.setText('fault')
        else:
            self.faults_indicator.setText('no fault')

        # only read at startup
        if not self.init:
            self.power_input.setText(f'{self.setpoint}')
            if mw_on:
                self.onoff.set_icon_on()
            else:
                self.onoff.set_icon_off()
            if autotune:
                self.autotune.set_icon_on()
            else:
                self.autotune.set_icon_off()
            self.init = True


    def get_header(self):
        return 'MW-setpoint[W] MW-freq[MHz] MW-forward[W] MW-reflected[W] MW-status[on/off]'

    def get_values(self):
        out = [self.setpoint, self.frequency, self.forward, self.reflected, self.mw_on]
        return out
