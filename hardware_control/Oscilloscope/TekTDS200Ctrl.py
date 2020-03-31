# -*- coding: utf-8 -*-

import math
import sys
import time
from collections import defaultdict, deque

import matplotlib.pyplot as plt
import pyvisa
from PyQt5 import QtCore

# from .base import QOnOff, QFixedLabel, FigureTab
from PyQt5.Qt import QMutex
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QWidget,
    QGridLayout,
    QSizePolicy,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.dates import epoch2num
from numpy import *

from .Scope_control_test import Scope
import logging
logger = logging.getLogger(__name__)

rm = pyvisa.ResourceManager()


class QOnOff(QPushButton):
    """An On/Off button with a nice icon for on/off

    Takes two functions that will be called when turning on/off
    starts in an unkown state if not defined otherwise

    if f_off is None: assume that f_on is a signal that can emit a boolian.
    """

    def __init__(self, f_on, f_off=None):
        super().__init__()
        self.setCheckable(True)

        self.onText = "On"
        self.offText = "Off"
        self.unkownText = "status unkown"

        self.onIcon = QIcon("button-power-on.svg")
        self.offIcon = QIcon("button-power-off.svg")
        self.unkownIcon = QIcon("button-power-unkown.svg")

        self.f_on = f_on
        self.f_off = f_off
        self.clicked.connect(self.click)

        self.setText(self.unkownText)
        self.setIcon(self.unkownIcon)
        self.setIconSize(QtCore.QSize(30, 30))

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def click(self):
        # we need a 'not' here since the button internally already
        # changed state at this point
        if not self.isChecked():
            if self.f_off:
                self.f_off()
            else:
                self.f_on.emit(False)
            self.set_icon_off()
        else:
            if self.f_off:
                self.f_on()
            else:
                self.f_on.emit(True)
            self.set_icon_on()

    def on(self):
        if self.f_off:
            self.f_on()
        else:
            self.f_on.emit(True)
        self.set_icon_on()

    def set_icon_on(self):
        """Just set the icon to on. Useful during startup"""
        self.setChecked(True)
        self.setIcon(self.onIcon)
        self.setText(self.onText)

    def off(self):
        if self.f_off:
            self.f_off()
        else:
            self.f_on.emit(False)
        self.set_icon_off()

    def set_icon_off(self):
        """Just set the icon to off. Useful during startup"""
        self.setChecked(False)
        self.setIcon(self.offIcon)
        self.setText(self.offText)

    def isOn(self):
        return self.isChecked()


class ScopeCommunication(QObject):
    """Handles communication with TDS 224 Oscilloscope"""

    values_read = pyqtSignal(float)
    toggle_enable = pyqtSignal(bool)

    def __init__(self, port, dummy=False, parent=None):
        super().__init__()
        self.parent = parent
        self.port = port
        self.s = Scope(self.port, dummy=dummy)
        self.online = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read)
        self.timer.start(2000)
        if self.parent:
            self.parent.write_value.connect(self.read)

    @pyqtSlot()
    def stop_thread(self):
        self.timer.stop()

    @pyqtSlot()
    def enabled(self):
        if self.online != self.s.online:
            self.online = self.s.online
            self.toggle_enable.emit(self.online)

    @pyqtSlot()
    def read(self):
        if self.online:
            # dont know exactly how to read outputs yet putting different options below to try out
            #            channel_1 = self.s.read("CH1")
            #            channel_2 = self.s.read("CH2")
            channel_3 = self.s.read("CH3")
            #            channel_4 = self.s.read("CH4")
            #            self.values_read.emit(channel_1, channel_2, channel_3, channel_4)
            self.values_read.emit(channel_3)
            sys.stdout.flush()
            self.pDebug("channels 3 are reading out")

        else:
            self.pDebug("read loop workiing")
            return


class FigureTab(QWidget):
    """A single matplotlib figure"""

    def __init__(self, parent=None, active=True):
        super().__init__()

        self.normalize = False
        self.autoscale = True

        self.fig, self.axes = plt.subplots()
        self.plot = FigureCanvas(self.fig)
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav = NavigationToolbar(self.plot, self)
        self.nav.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # custom toolbar
        self.controls = QHBoxLayout()
        self.normalizebutton = QPushButton("normalize")
        self.normalizebutton.clicked.connect(self.toggle_normalize)
        self.normalizebutton.setCheckable(True)
        self.autoscalebutton = QPushButton("autoscale")
        self.autoscalebutton.clicked.connect(self.toggle_autoscale)
        self.autoscalebutton.setCheckable(True)
        self.autoscalebutton.setChecked(True)
        #        self.controls.addWidget(self.normalizebutton)
        #        self.controls.addWidget(self.autoscalebutton)
        self.controls.addStretch(1)

        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.controls)
        self.vbox.addWidget(self.nav)
        self.vbox.addWidget(self.plot)
        self.vbox.addSpacing(50)

        self.setLayout(self.vbox)

        self.elements_and_name = []
        self.data = defaultdict(deque)

        self.interval = 1000
        self.active = active

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.add_data)

        # always get data
        if self.active:
            self.timer.start(self.interval)

    def add_element(self, element, name):
        self.elements_and_name.append((element, name))

    def add_data(self):
        t = time.time()
        for e, n in self.elements_and_name:
            self.data[n].append([t, getattr(e, n)])

        # only save the last 10000 data points
        for k, v in self.data.items():
            while len(v) > 10000:
                v.popleft()

    def toggle_autoscale(self):
        self.autoscale = not self.autoscale

    def toggle_normalize(self):
        self.normalize = not self.normalize

    def update(self):
        xleft, xright = self.axes.get_xlim()
        ybottom, ytop = self.axes.get_ylim()
        self.axes.clear()
        self.axes.set_xlabel("Time")
        for k, v in self.data.items():
            myX = np.array([x[0] for x in v])
            myY = np.array([x[1] for x in v])
            if self.normalize and len(myY) and myY.max() > 0:
                myY = myY / myY.max()
            self.axes.plot_date(
                epoch2num(myX), myY, "o-", label=k, tz="America/Los_Angeles"
            )
        self.axes.legend(loc="best")
        if not self.autoscale:
            self.axes.set_xlim([xleft, xright])
            self.axes.set_ylim([ybottom, ytop])
        self.plot.draw()


class ScopeControls(QGroupBox):
    write_value = pyqtSignal(int, float)

    def __init__(self, port, dummy=False, debug=False, parent=None):
        super().__init__("Scope")
        self.parent = parent
        self.port = port
        self.scope = Scope(self.port, dummy=dummy)
        self.mutex = QMutex()

        #        self.onoff = QOnOff(self.on, self.off)
        self.chbox = QVBoxLayout()
        #        self.chbox.addWidget(self.onoff)
        self.channeldisplay = QGridLayout()
        self.dummy = dummy
        self.debug = debug
        self.hbox = QHBoxLayout()

        # Buttons/Controls
        self.control_box = QVBoxLayout()
        self.label = QLabel("")
        self.standard_controls = QPushButton("Set Standard Scope Settings")
        self.standard_controls.clicked.connect(self.set_standards)
        self.set_trigger = QLineEdit()
        self.set_trigger.setText("")
        self.set_trigger.setFont(QFont("Times New Roman", 18))
        self.set_trigger.setFixedWidth(100)
        self.set_trigger_button = QPushButton("Set Trigger")
        self.set_trigger_button.clicked.connect(self.setTrigger)
        self.voltage_range1 = QLineEdit()
        self.voltage_range1.setText("Channel 1 Range [V]")
        self.voltage_range1.setFont(QFont("Times New Roman", 18))
        self.voltage_range_button1 = QPushButton("Set Channel 1 Voltage range")
        self.voltage_range_button1.clicked.connect(lambda: self.set_voltage_range(1))
        self.voltage_range2 = QLineEdit()
        self.voltage_range2.setText("Channel 2 Range [V]")
        self.voltage_range2.setFont(QFont("Times New Roman", 18))
        self.voltage_range_button2 = QPushButton("Set Channel 2 Voltage range")
        self.voltage_range_button2.clicked.connect(lambda: self.set_voltage_range(2))
        self.voltage_range3 = QLineEdit()
        self.voltage_range3.setText("Channel 3 Range [V]")
        self.voltage_range3.setFont(QFont("Times New Roman", 18))
        self.voltage_range_button3 = QPushButton("Set Channel 3 Voltage range")
        self.voltage_range_button3.clicked.connect(lambda: self.set_voltage_range(3))
        self.voltage_range4 = QLineEdit()
        self.voltage_range4.setText("Channel 4 Range [V]")
        self.voltage_range_button4 = QPushButton("Set Channel 4 Voltage range")
        self.voltage_range_button4.clicked.connect(lambda: self.set_voltage_range(4))
        self.voltage_range4.setFont(QFont("Times New Roman", 18))
        self.send_command = QLineEdit("Write Command Here!")
        self.send_command_button = QPushButton("Send Command")
        self.send_command_button.clicked.connect(self.command)
        self.command_response = QLabel("")
        self.OnOff_1 = QOnOff(self.on1, self.off1)
        self.OnOff_2 = QOnOff(self.on2, self.off2)
        self.OnOff_3 = QOnOff(self.on3, self.off3)
        self.OnOff_4 = QOnOff(self.on4, self.off4)
        self.OnOff_1.setFixedWidth(200)
        self.OnOff_2.setFixedWidth(200)
        self.OnOff_3.setFixedWidth(200)
        self.OnOff_4.setFixedWidth(200)
        self.OnOff_1.setFont(QFont("Times New Roman", 12))
        self.OnOff_2.setFont(QFont("Times New Roman", 12))
        self.OnOff_3.setFont(QFont("Times New Roman", 12))
        self.OnOff_4.setFont(QFont("Times New Roman", 12))
        self.OnOffButtons = [self.OnOff_1, self.OnOff_2, self.OnOff_3, self.OnOff_4]
        i = 0
        while i <= 3:
            self.OnOffButtons[i].offText = "CH" + str(i + 1) + " OFF"
            self.OnOffButtons[i].onText = "CH" + str(i + 1) + " ON"
            i += 1

        self.control_box.addWidget(self.label)
        self.control_box.addWidget(self.standard_controls)
        self.control_box.addWidget(self.set_trigger)
        self.control_box.addWidget(self.set_trigger_button)
        self.hbox2 = QHBoxLayout()
        self.subvbox = QVBoxLayout()
        self.subvbox2 = QVBoxLayout()
        self.subvbox.addWidget(self.voltage_range1)
        self.subvbox.addWidget(self.voltage_range_button1)
        self.subvbox.addWidget(self.voltage_range2)
        self.subvbox.addWidget(self.voltage_range_button2)
        self.subvbox.addWidget(self.voltage_range3)
        self.subvbox.addWidget(self.voltage_range_button3)
        self.subvbox.addWidget(self.voltage_range4)
        self.subvbox.addWidget(self.voltage_range_button4)
        self.subvbox2.addWidget(self.OnOff_1)
        self.subvbox2.addWidget(self.OnOff_2)
        self.subvbox2.addWidget(self.OnOff_3)
        self.subvbox2.addWidget(self.OnOff_4)
        self.hbox2.addLayout(self.subvbox)
        self.hbox2.addLayout(self.subvbox2)
        self.control_box.addLayout(self.hbox2)
        self.subhbox = QHBoxLayout()
        if self.debug == True:
            self.subhbox.addWidget(self.send_command)
            self.subhbox.addWidget(self.send_command_button)
            self.control_box.addLayout(self.subhbox)
            self.control_box.addWidget(self.command_response)
        self.control_box.addStretch(1)
        self.scope_plot = FigureTab()

        if dummy:
            self.label.setText("dummy")
        # add controls and plot to layout then set layout
        self.hbox.addLayout(self.control_box)
        self.hbox.addWidget(self.scope_plot)
        #        self.hbox.addLayout(self.chbox)
        # self.hbox.addLayout(self.plot_box)
        self.hbox.addStretch(1)
        self.setLayout(self.hbox)

        self.comm_thread = QThread()
        self.comm = ScopeCommunication(self.port, dummy=dummy, parent=self)
        self.pDebug("QScope check")
        sys.stdout.flush()
        self.comm.values_read.connect(self.read)
        self.read(2)

    def on1(self):
        n = 0
        if not self.dummy:
            data = self.read(n)
            self.update(data, n)
            self.pDebug("Scope Reading channel, CH1")
            return data
        else:
            self.read(0)
            self.pDebug("dummy read CH1")
            return

    def off1(self):
        if not self.dummy:
            n = 0
            stop_cmd = "DAT:STOP"
            self.scope.cmd(n, stop_cmd)
            self.pDebug("Scope stopped reading data, CH1")

    def on2(self):
        if not self.dummy:
            n = 1
            data = self.read(n)
            self.update(data, n)
            self.pDebug("Scope Reading channel, CH2")
            return data
        else:
            self.read(1)
            self.pDebug("dummy read CH2")
            return

    def off2(self):
        if not self.dummy:
            n = 1
            stop_cmd = "DAT:STOP"
            self.scope.cmd(n, stop_cmd)
            self.pDebug("Scope stopped reading data, CH2")

    def on3(self):
        if not self.dummy:
            n = 2
            data = self.read(n)
            self.update(data, n)
            self.pDebug("Scope Reading channel, CH3")
            return data
        else:
            self.read(2)
            self.pDebug("dummy read CH3")
            return

    def off3(self):
        if not self.dummy:
            n = 2
            stop_cmd = "DAT:STOP"
            self.scope.cmd(n, stop_cmd)
            self.pDebug("Scope stopped reading data, CH3")

    def on4(self):
        if not self.dummy:
            n = 3
            data = self.read(n)
            self.update(data, n)
            self.pDebug("Scope Reading channel, CH4")
            return data
        else:
            self.read(3)
            self.pDebug("dummy read CH4")
            return

    def off4(self):
        if not self.dummy:
            n = 3
            stop_cmd = "DAT:STOP"
            self.scope.cmd(n, stop_cmd)
            self.pDebug("Scope stopped reading data, CH4")

    def get_values(self):
        out = []
        for ch in self.channels:
            out.extend(ch.get_values())
        return out

    def get_header(self):
        return " ".join([ch.get_header() for ch in self.channels])

    def set_standards(self):
        # set the basic trigger channel, voltage range, probe attenuation, vertical offset, trigger slope/coupling etc...
        if not self.dummy:
            trigger_settings = self.scope.s.write(
                ":TRIG:MAIN:TYP EDGE:SOU CH1:SLO RIS:COUP AC:"
            )  # colons may need to be changed to semicolons and vice versa
            self.set_trigger.setText("trigger_settings: Standard")
            #            self.scope.s.write(')
            self.pDebug(trigger_settings)
            self.pDebug("set_standards was called")
            n = 1
            while n <= 4:
                # these commands were taken from the Labview Code need to test and see how they work, may need to break up into multiple lines
                self.scope.s.write(
                    "CH"
                    + str(n)
                    + ":COUP DC; POS "
                    + str(0.0)
                    + "; PRO "
                    + str(10)
                    + "; SCA "
                    + str(10)
                    + ":SEL: CH"
                    + str(n)
                    + " ON;"
                )
                volt_range = self.scope.s.write("CH" + str(n) + ":; SCA" + str(10))
                self.pDebug(volt_range)
                if n == 1:
                    self.voltage_range1.setText("10 V")
                if n == 2:
                    self.voltage_range2.setText("10 V")
                if n == 3:
                    self.voltage_range3.setText("10 V")
                if n == 4:
                    self.voltage_range4.setText("10 V")
                n += 1
            self.pDebug("Channels 1-4 have been set")
            self.scope.s.write("INITIATE_CLEAR")
            self.scope.s.write("CHECK_CLEAR_STATUS")

        else:
            random_val = round(np.random.normal(0, 10), 2)
            self.voltage_range1.setText(str(random_val))
            self.voltage_range2.setText(str(random_val))
            self.voltage_range3.setText(str(random_val))
            self.voltage_range4.setText(str(random_val))

    def setTrigger(self):
        trigger_settings = self.scope.read("CH1:TRIG:MAIN:SLO RIS:COUP AC:")
        self.set_trigger.setText(f"{trigger_settings}")

    def set_voltage_range(self, i):
        if i == 1:
            value = self.voltage_range1.text()
            self.scope.cmd("CH1", "SCA " + str(value))
            return
        if i == 2:
            value = self.voltage_range2.text()
            self.scope.cmd("CH2", "SCA " + str(value))
            return
        if i == 3:
            value = self.voltage_range3.text()
            self.scope.cmd("CH3", "SCA " + str(value))
            return
        if i == 4:
            value = self.voltage_range4.text()
            self.scope.cmd("CH4", "SCA " + str(value))
            return
        else:
            self.pDebug("Not a Valid Channel")

    @pyqtSlot(bool)
    def toggle_enable(self, status):
        self.setEnabled(status)

    def try_reconnect(self):
        self.scope.connect()

    @pyqtSlot(float)
    def read(self, n):
        n = n
        channels = ("CH1", "CH2", "CH3", "CH4")
        if (
            not self.dummy
        ):  # bottom method below reads all channels and updates all plots iteratly
            # first method is one channel at a time
            data = self.scope.read(channels[n])
            #            self.update(data, n)
            self.update2(data, n)
            self.pDebug(f"Scope Reading channel, {channels[n]}")
            return data
        else:
            x = 0
            y = 0
            data = self.update2(x, y)

    #        #below is for all outputs being on same plot
    def update(self, data, n):
        data = data
        n = n
        if n == 0:
            self.parent.scope_plot.axes.plot(data[0], data[1], "b-", label="CH1 V")
            self.parent.scope_plot.plot.draw()
            self.pDebug(len(data), len(data[0]))
        if n == 1:
            self.parent.scope_plotCH2.axes.plot(data[0], data[1], "r-", label="CH2 V")
            self.parent.scope_plotCH2.plot.draw()
        if n == 2:
            self.parent.scope_plotCH3.axes.plot(data[0], data[1], "g-", label="CH3 V")
            self.parent.scope_plotCH3.plot.draw()
        if n == 3:
            self.parent.scope_plotCH4.axes.plot(data[0], data[1], "y-", label="CH4 V")
            self.parent.scope_plotCH4.plot.draw()
        #        self.main.scope_plot.plot.plt.show()
        self.pDebug("updating channels")

    def update2(self, data, n):
        data = data
        n = n
        if not self.dummy:
            if n == 0:
                self.scope_plot.axes.plot(data[0], data[1], "b-", label="CH1 V")

                self.pDebug(len(data), len(data[0]))
            if n == 1:
                self.scope_plot.axes.plot(data[0], data[1], "r-", label="CH2 V")
                #                self.scope_plot.plot.draw()
                self.pDebug(len(data), len(data[0]))
            if n == 2:
                self.scope_plot.axes.plot(data[0], data[1], "g-", label="CH3 V")
                #                self.scope_plot.plot.draw()
                self.pDebug(len(data), len(data[0]))
            if n == 3:
                self.scope_plot.axes.plot(data[0], data[1], "y-", label="CH4 V")
                #                self.scope_plot.plot.draw()
                self.pDebug(len(data), len(data[0]))
            self.pDebug("Updating Channels")
            self.scope_plot.plot.draw()

        else:
            t = linspace(0, 2 * math.pi, 400)
            a = sin(t)
            b = cos(t)
            c = a + b
            self.scope_plot.axes.plot(t, a, "r-", label="Random Plot")
            self.scope_plot.axes.plot(t, b, "g-")
            self.scope_plot.axes.plot(t, c, "b-")
            self.pDebug("generating random plot points :D")
            self.scope_plot.plot.draw()
        self.scope_plot.plot.draw()

    def command(self):
        if not self.dummy:
            response = self.scope.s.read(self.send_command.text())
            self.pDebug(response)
            self.command_response.setText(response)
            return
        else:
            self.command_response.setText(
                "LOL you can't send commands to a dummy, dummy!"
            )
