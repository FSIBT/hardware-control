# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 15:41:12 2019

@author: Schuyler
"""
import time
import pyvisa
import sys
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
    QComboBox,
    QGridLayout,
)

from .DG_control import DelayGenerator

rm = pyvisa.ResourceManager()


class DelayGeneratorCommunication(QObject):
    """Handles communication with the Delay Generator"""

    values_read = pyqtSignal(float)
    toggle_enable = pyqtSignal(bool)

    def __init__(self, port, parent=None, dummy=False):
        super().__init__()
        self.parent = parent
        self.port = port
        self.instrument = DelayGenerator(self.port, self.parent, dummy=dummy)
        self.online = False

        self.timer = QTimer(self)
        # self.timer.timeout.connect(self.instrument.try_connect)
        #        self.timer.timeout.connect(self.enabled)
        self.timer.timeout.connect(self.read)
        self.timer.start(2500)

    #        if self.parent:
    #            self.parent.write_value.connect(self.write)

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
        # dont know what needs to go here yet :(
        data = self.instrument.write("*IDN?")
        print(data)
        return data


#
#    @pyqtSlot()
#    def write(self):
#        if self.online:
#            #dont know what needs to go here yet :(


class DelayGeneratorControl(QGroupBox):
    write_value = pyqtSignal(int, float)

    def __init__(self, port, parent=None, debug=False, dummy=False):
        super().__init__("DelayGenerator")
        self.port = port
        self.instrument = DelayGenerator(self.port, self.parent, dummy=dummy)
        self.parent = parent
        self.dummy = dummy
        self.debug = debug

        self.hbox = QHBoxLayout()
        self.vbox = QVBoxLayout()
        """Create variables/buttons for the necessary functions of the delay generator
        still need to look them up in labview program"""
        self.trigger_mode = QComboBox()
        #        self.trigger_mode.setText("Select Trigger Mode")
        self.trigger_mode.addItem("Int")
        self.trigger_mode.addItem("Ext")
        self.trigger_mode.addItem("SS")
        self.trigger_mode.addItem("Burst")
        self.trigger_mode.currentIndexChanged.connect(self.triggerChange)
        self.single_trigger = QPushButton()
        self.single_trigger.setText("Single Shot")
        self.single_trigger.clicked.connect(self.SingleShot)
        self.trigger_rate = QLineEdit("")
        self.trigger_rate.setFixedWidth(100)
        self.trigger_rate_label = QPushButton("Set Trigger Rate [Hz]")
        self.trigger_rate_label.clicked.connect(self.TriggerRate)
        self.trigger_button = QPushButton("Start/Stop Triggering")
        #        self.trigger_button.clicked.connect(self.StartStopTrigger)
        # Channel settings
        self.ChannelA_label = QLabel("Channel A Settings")
        self.ChannelA_trig = QComboBox()
        self.ChannelA_trig.setFixedWidth(50)
        self.ChannelA_trig.addItem("T")
        self.ChannelA_trig.addItem("B")
        self.ChannelA_trig.addItem("C")
        self.ChannelA_trig.addItem("D")
        self.ChannelA_delay = QLineEdit("Time delay [s]")
        self.ChannelA_delay.setFixedWidth(225)
        self.ChannelA_button = QPushButton("Set Settings")
        self.ChannelA_button.clicked.connect(self.SetSettingsA)
        self.ChannelB_label = QLabel("Channel B Settings")
        self.ChannelB_trig = QComboBox()
        self.ChannelB_trig.addItem("T")
        self.ChannelB_trig.addItem("A")
        self.ChannelB_trig.addItem("C")
        self.ChannelB_trig.addItem("D")
        self.ChannelB_delay = QLineEdit("Time delay [s]")
        self.ChannelB_delay.setFixedWidth(225)
        self.ChannelB_button = QPushButton("Set Settings")
        self.ChannelB_button.clicked.connect(self.SetSettingsB)
        self.ChannelC_label = QLabel("Channel C Settings")
        self.ChannelC_trig = QComboBox()
        self.ChannelC_trig.addItem("T")
        self.ChannelC_trig.addItem("A")
        self.ChannelC_trig.addItem("B")
        self.ChannelC_trig.addItem("D")
        self.ChannelC_delay = QLineEdit("Time delay [s]")
        self.ChannelC_delay.setFixedWidth(225)
        self.ChannelC_button = QPushButton("Set Settings")
        self.ChannelC_button.clicked.connect(self.SetSettingsC)
        self.ChannelD_label = QLabel("Channel D Settings")
        self.ChannelD_trig = QComboBox()
        self.ChannelD_trig.addItem("T")
        self.ChannelD_trig.addItem("A")
        self.ChannelD_trig.addItem("B")
        self.ChannelD_trig.addItem("C")
        self.ChannelD_delay = QLineEdit("Time delay [s]")
        self.ChannelD_delay.setFixedWidth(225)
        self.ChannelD_button = QPushButton("Set Settings")
        self.ChannelD_button.clicked.connect(self.SetSettingsD)

        # command line and button
        if self.debug == True:
            self.hbox2 = QHBoxLayout()
            self.commandLine = QLineEdit("Enter your Command here!")
            self.commandbutton = QPushButton("Send Command")
            self.commandbutton.clicked.connect(self.commandsend)
            self.commandback = QLabel("")
            self.hbox2.addWidget(self.commandLine)
            self.hbox2.addWidget(self.commandbutton)
            self.vbox.addLayout(self.hbox2)
            self.vbox.addWidget(self.commandback)

        # Organize the Trigger Grid
        self.TriggerGrid = QGridLayout()
        self.TriggerGrid.addWidget(self.trigger_mode, 0, 0)
        self.TriggerGrid.addWidget(self.single_trigger, 0, 1)
        self.TriggerGrid.addWidget(self.trigger_rate, 1, 0)
        self.TriggerGrid.addWidget(self.trigger_rate_label, 1, 1)
        self.TriggerGrid.addWidget(self.trigger_button, 2, 1)

        # Organize Channel Settings
        self.ChannelGrid = QGridLayout()
        self.ChannelGrid.addWidget(self.ChannelA_label, 0, 0)
        self.ChannelGrid.addWidget(self.ChannelA_trig, 0, 1)
        self.ChannelGrid.addWidget(self.ChannelA_delay, 0, 2)
        self.ChannelGrid.addWidget(self.ChannelA_button, 0, 3)
        self.ChannelGrid.addWidget(self.ChannelB_label, 1, 0)
        self.ChannelGrid.addWidget(self.ChannelB_trig, 1, 1)
        self.ChannelGrid.addWidget(self.ChannelB_delay, 1, 2)
        self.ChannelGrid.addWidget(self.ChannelB_button, 1, 3)
        self.ChannelGrid.addWidget(self.ChannelC_label, 2, 0)
        self.ChannelGrid.addWidget(self.ChannelC_trig, 2, 1)
        self.ChannelGrid.addWidget(self.ChannelC_delay, 2, 2)
        self.ChannelGrid.addWidget(self.ChannelC_button, 2, 3)
        self.ChannelGrid.addWidget(self.ChannelD_label, 3, 0)
        self.ChannelGrid.addWidget(self.ChannelD_trig, 3, 1)
        self.ChannelGrid.addWidget(self.ChannelD_delay, 3, 2)
        self.ChannelGrid.addWidget(self.ChannelD_button, 3, 3)

        # combine Grids & set Layout

        self.hbox.addLayout(self.ChannelGrid)
        self.hbox.addLayout(self.TriggerGrid)
        self.vbox2 = QVBoxLayout()
        self.vbox2.addLayout(self.hbox)
        self.vbox2.addLayout(self.vbox)

        self.vbox2.addStretch(1)
        self.setLayout(self.vbox2)

        self.comm_thread = QThread()
        self.comm = DelayGeneratorCommunication(self.port, dummy=dummy, parent=self)

        print("Delay Generator Check")
        sys.stdout.flush()

    #        self.comm.values_read(self.read)

    # Place Necessary functions below

    def triggerChange(self):
        # Need to find commands for DG535 to change trigger channel
        if not self.dummy:
            if self.trigger_mode.currentText() == "Int":
                self.instrument.write("TM 0")
            if self.trigger_mode.currentText() == "Ext":
                self.instrument.write("TM 1")
            if self.trigger_mode.currentText() == "SS":
                self.instrument.write("TM 2")
            if self.trigger_mode.currentText() == "Burst":
                self.instrument.write("TM 3")
            else:
                print("Not a valid command!!!!!!!!!!!?")
                return

    def SingleShot(self):
        # Find command to send single trigger shot through selected channel
        if not self.dummy:
            self.instrument.write("TM 2; SS")

    def TriggerRate(self):
        # find command to set continuous trigger rate
        if not self.dummy:
            if self.trigger_mode.currentText() != "Burst":
                self.instrument.write(f"TR 1,{self.trigger_rate.text()}")
            else:
                self.instrument.write(f"TR 2,{self.trigger_rate.text()}")

    #    def StartStopTrigger(self):
    # Find command to start/stop continuous/periodic trigger

    def SetSettingsA(self):
        # find commmand to send settings to Delay Generator
        if not self.dummy:
            if self.ChannelA_trig.currentText() == "T":
                self.instrument.write(f"DT 2,1,{self.ChannelA_delay.text()}")
            if self.ChannelA_trig.currentText() == "B":
                self.instrument.write(f"DT 2,3,{self.ChannelA_delay.text()}")
            if self.ChannelA_trig.currentText() == "C":
                self.instrument.write(f"DT 2,5,{self.ChannelA_delay.text()}")
            if self.ChannelA_trig.currentText() == "D":
                self.instrument.write(f"DT 2,6,{self.ChannelA_delay.text()}")
            else:
                print("ERROR?")
                return
        else:
            print("Setting Channel A settings")
            return

    def SetSettingsB(self):
        if not self.dummy:
            if self.ChannelB_trig.currentText() == "T":
                self.instrument.write(f"DT 3,1,{self.ChannelA_delay.text()}")
            if self.ChannelB_trig.currentText() == "A":
                self.instrument.write(f"DT 3,2,{self.ChannelA_delay.text()}")
            if self.ChannelB_trig.currentText() == "C":
                self.instrument.write(f"DT 3,5,{self.ChannelA_delay.text()}")
            if self.ChannelB_trig.currentText() == "D":
                self.instrument.write(f"DT 3,6,{self.ChannelA_delay.text()}")
            else:
                print("ERROR?")
                return
        else:
            print("Setting Channel B settings")
            return

    def SetSettingsC(self):
        if not self.dummy:
            if self.ChannelC_trig.currentText() == "T":
                self.instrument.write(f"DT 5,1,{self.ChannelA_delay.text()}")
            if self.ChannelC_trig.currentText() == "A":
                self.instrument.write(f"DT 5,2,{self.ChannelA_delay.text()}")
            if self.ChannelC_trig.currentText() == "B":
                self.instrument.write(f"DT 5,3,{self.ChannelA_delay.text()}")
            if self.ChannelC_trig.currentText() == "D":
                self.instrument.write(f"DT 5,6,{self.ChannelA_delay.text()}")
            else:
                print("ERROR?")
                return
        else:
            print("Setting Channel C settings")
            return

    def SetSettingsD(self):
        if not self.dummy:
            if self.ChannelD_trig.currentText() == "T":
                self.instrument.write(f"DT 2,1,{self.ChannelA_delay.text()}")
            if self.ChannelD_trig.currentText() == "A":
                self.instrument.write(f"DT 6,2,{self.ChannelA_delay.text()}")
            if self.ChannelD_trig.currentText() == "B":
                self.instrument.write(f"DT 6,3,{self.ChannelA_delay.text()}")
            if self.ChannelD_trig.currentText() == "C":
                self.instrument.write(f"DT 6,5,{self.ChannelA_delay.text()}")
            else:
                print("ERROR?")
                return
        else:
            print("Setting Channel D settings")
            return

    #        if self.dummy:

    def commandsend(self):
        cmd = self.commandLine.text()
        getback = self.instrument.write(cmd)
        self.commandback.setText(getback)
        return

    @pyqtSlot(float)
    def read(self):
        if not self.dummy:
            print("Channel A settings")
            data = self.instrument.query("DL 1,0,0")
            return data
        else:
            print("Channel A settings: DUMMY")
