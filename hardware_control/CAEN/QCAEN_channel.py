import visa

from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QGroupBox, QFormLayout, QLabel, QLineEdit, QHBoxLayout
from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot, QObject

from .control import CAEN_connector
from ..QHelper import QOnOff, QOnOffIndicator


class CAENcommunication(QObject):
    """Handle the communication with the instrument in a separate thread"""

    new_values_read = pyqtSignal(int, float, float, float, dict)
    toggle_enable = pyqtSignal(bool)

    def __init__(self, dummy=False, parent=None):
        super().__init__()
        self.parent = parent
        self.rm = visa.ResourceManager()
        self.instrument = CAEN_connector(self.rm, dummy=dummy)
        self.online = False

        self.channels = {}
        self.GUIs = {}
        self.setpoints = {}
        self.voltages = {}
        self.currents = {}
        self.status = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.instrument.try_connect)
        self.timer.timeout.connect(self.enabled)
        self.timer.timeout.connect(self.read)
        self.timer.start(1000)

    def connect(self):
        for name, qtelement in self.GUIs.items():
            qtelement.write_value.connect(self.write)
            # self.parent.toggle_on_off.connect(self.toggle_on_off)
            # self.parent.toggle_autotuning_on_off.connect(self.toggle_autotune)

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
            for name, c in self.channels.items():
                self.setpoints[c] = self.instrument.read_vset(c)
                self.voltages[c] = self.instrument.read_voltage(c)
                self.currents[c] = self.instrument.read_current(c)
                self.status[c] = self.instrument.read_status(c)
                self.new_values_read.emit(int(c), self.setpoints[c], self.voltages[c],
                                          self.currents[c], self.status[c])

    @pyqtSlot(int, str, float)
    def write(self, channel, name, value):
        if self.online:
            if name == 'maxV':
                self.instrument.set_maxV(channel, value)
            elif name == 'current':
                self.instrument.set_current(channel, value)
            elif name == 'voltage':
                self.instrument.set_voltage(channel, value)
            elif name == 'rampup':
                self.instrument.set_current(channel, value)
            elif name == 'rampdown':
                self.instrument.set_current(channel, value)
            elif name == 'enable_channel':
                if value == 1:
                    self.instrument.enable_channel(channel)
                else:
                    self.instrument.disable_channel(channel)


class CAENControl(QGroupBox):
    """A QtWidget for a single channel

    If several of these are used in the same app, only a single
    CAENcommunication instance should be used with all widgets.
    """

    write_value = pyqtSignal(int, str, float)

    def __init__(self, channel, name, connector=None, dummy=False):
        super().__init__(name)
        self.name = name
        self.connector = connector
        self.channel = channel
        self.dummy = dummy
        self.setpoint = 0
        self.voltage = 0
        self.current = 0
        self.maxV = 0
        self.maxI = 0
        self.init = False
        self.rampspeed = 100
        self.status = {}

        self.grid = QFormLayout()

        self.connector.new_values_read.connect(self.read_values)

        # ON/OFF SWITCH
        self.onoff = QOnOff(self.on_click, self.off_click)

        self.Vlabel = QLabel('')
        self.Ilabel = QLabel('')
        self.MaxVlabel = QLabel('')
        self.MaxIlabel = QLabel('')

        # status
        self.status = QHBoxLayout()
        self.status_trip = QOnOffIndicator('Trip')
        self.status_enabled = QOnOffIndicator('Enabled')
        self.status_ramping = QOnOffIndicator('Ramping')
        self.status.addWidget(self.status_trip)
        self.status.addWidget(self.status_enabled)
        self.status.addWidget(self.status_ramping)

        # VOLTAGE INPUT
        self.voltage_input = QLineEdit()
        self.voltage_input.setText('')
        self.voltage_input.setValidator(QDoubleValidator(0, self.maxV, 3))
        self.voltage_input.setFixedWidth(75)
        self.voltage_input.returnPressed.connect(self.set_voltage)

        self.grid.addRow('On/off', self.onoff)
        self.grid.addRow('Set Voltage [V]', self.voltage_input)
        self.grid.addRow('Read Voltage [V]', self.Vlabel)
        self.grid.addRow('Current [uA]', self.Ilabel)
        self.grid.addRow('Max Current[uA]', self.MaxIlabel)
        self.grid.addRow('Max Voltage[V]', self.MaxVlabel)
        self.grid.addRow('Status', self.status)

        self.setLayout(self.grid)

        # set default ramp up/down speed
        self.set_ramp(self.rampspeed)

    def on_click(self):
        self.write_value.emit(self.channel, 'enable_channel', 1)

    def off_click(self):
        self.write_value.emit(self.channel, 'enable_channel', 0)

    @pyqtSlot(int, float, float, float, dict)
    def read_values(self, channel, setpoint, voltage, current, status):
        if channel == self.channel:
            self.setpoint = setpoint
            self.voltage = voltage
            self.current = current
            self.status = status

            # only read setpoint at startup
            if not self.init:
                self.voltage_input.setText(f'{self.setpoint}')
                if self.status['on_off']:
                    self.onoff.set_icon_on()
                else:
                    self.onoff.set_icon_off()
                self.init = True
            self.Vlabel.setText(f'{self.voltage}')
            self.Ilabel.setText(f'{self.current}')
            self.status_trip.set(self.status['tripped'])
            self.status_ramping.set(self.status['ramping_up'] + self.status['ramping_down'])
            self.status_enabled.set(not self.status['disabled'])

    def set_voltage(self):
        if self.voltage_input.text() == '':
            print(f'Caen channel{self.channel}: invalid value for voltage')
        else:
            self.write_value.emit(self.channel, 'voltage', float(self.voltage_input.text()))

    def get_header(self):
        return f'CAEN-{self.channel}-Voltage[V] CAEN-{self.channel}-Current[A]'

    def get_values(self):
        return self.voltage, self.current

    def set_maxV(self, voltage):
        self.maxV = voltage
        self.write_value.emit(self.channel, 'maxV', voltage)
        self.MaxVlabel.setText(f'{voltage}')

        self.voltage_input.setValidator(QDoubleValidator(0, self.maxV, 3))

    def set_maxI(self, current):
        # todo: ensure that current is within limits
        self.write_value.emit(self.channel, 'current', current)
        self.MaxIlabel.setText(f'{current}')

    def set_ramp(self, volts_per_sec):
        self.rampspeed = volts_per_sec
        self.write_value.emit(self.channel, 'rampup', self.rampspeed)
        self.write_value.emit(self.channel, 'rampdown', self.rampspeed)
