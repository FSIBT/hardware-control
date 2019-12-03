#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 11:19:14 2019

@author: sky
"""
import random
import sys

import numpy as np
import pyvisa
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
)

from .IonGauge_control_test import IonGauge

rm = pyvisa.ResourceManager()


class IonGaugeCommunication(QObject):
    """Handles Communication with the controller class of the GP 390"""

    # handles communication to the IonGauge in  its own thread
    values_read = pyqtSignal(float)
    toggle_enable = pyqtSignal(bool)

    def __init__(self, port, address, dummy=False, parent=None):
        super().__init__()
        self.parent = parent
        self.port = port
        self.address = address
        self.instrument = IonGauge(self.port, self.address, dummy=dummy)
        self.online = False
        self.dummy = dummy

        self.timer = QTimer(self)
        # self.timer.timeout.connect(self.instrument.try_connect)
        #        self.timer.timeout.connect(self.enabled)
        self.timer.timeout.connect(self.read)
        self.timer.start(2500)
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
        #       if self.online:
        if not self.dummy:
            pressure = self.instrument.read()
            print("in comm read")
            sys.stdout.flush()
            self.values_read.emit(round(pressure, 2))
        else:
            pressure = np.random.normal(0, 900)
            self.values_read.emit(round(pressure, 3))

    @pyqtSlot(int, float)
    def write(self, channel, value):
        if self.online:
            if value < 0 or value >= 9.99e09:
                print("WARNING: Ion Gauge pressure value out of range!")

            self.instrument.write(channel, value)


class QIonGauge(QGroupBox):
    write_value = pyqtSignal(int, float)

    def __init__(
        self, port, address, parent=None, dummy=False, debug=False, pressure_limit=True
    ):
        super().__init__("IonGauge")
        self.port = port
        self.address = address
        self.pressure_setpoint = 0
        self.pressure = 0
        self.pressure_limit = pressure_limit
        self.instrument = IonGauge(self.port, self.address, dummy=dummy)
        self.dummy = dummy
        self.debug = debug

        self.parent = parent
        self.hbox = QHBoxLayout()

        # list of values
        self.value_box = QVBoxLayout()
        self.pressure_label = QLabel("0 Torr")
        self.pressure_label.setAlignment(QtCore.Qt.AlignCenter)
        self.label = QLabel("")
        # add pressure to value box
        self.value_box.addWidget(self.pressure_label)
        self.value_box.addWidget(self.label)
        self.value_box.addStretch(1)

        # controls
        self.refreshbutton = QPushButton("Refresh [in Torr]")
        self.refreshbutton.clicked.connect(self.refresh)
        self.ATMcommand = QLineEdit()
        self.ATMcommand.setText("")
        self.ATMcommand.setFixedWidth(100)
        self.ATMsend_command = QPushButton("Send Command")
        self.ATMsend_command.clicked.connect(self.send_command)
        self.ATMreturn = QLabel("")
        self.ATMcommand.setFont(QFont("Times New Roman", 18))

        # add controls to control layout
        self.controls = QVBoxLayout()
        self.controls.addWidget(self.refreshbutton)
        if self.debug == True:
            self.controls.addWidget(self.ATMcommand)
            self.controls.addWidget(self.ATMsend_command)
            self.controls.addWidget(self.ATMreturn)
        self.controls.addStretch(1)

        self.hbox.addLayout(self.value_box)
        self.hbox.addLayout(self.controls)
        self.hbox.addStretch(1)

        if dummy:
            self.label.setText("dummy")

        self.setLayout(self.hbox)

        # start communication with IonGauge
        self.comm_thread = QThread()
        self.comm = IonGaugeCommunication(
            self.port, self.address, dummy=dummy, parent=self
        )

        print("QATM check")
        sys.stdout.flush()
        # self.comm.toggle_enable.connect(self.toggle_enable)
        self.comm.values_read.connect(self.read)
        # self.parent.prepare_shutdown.connect(self.comm.stop_thread)
        self.comm.moveToThread(self.comm_thread)
        self.comm_thread.start()

        # print("in funct zyx")
        # sys.stdout.flush()

    #        self.timer = QTimer(self)
    #        self.timer.timeout.connect(self.read())
    #        self.timer.start(1000)

    # start out disabled
    # self.toggle_enable(False)

    @pyqtSlot(bool)
    def toggle_enable(self, status):
        self.setEnabled(status)

    def try_reconnect(self):
        self.IonGauge.try_connect()

    @pyqtSlot(float)
    def read(self):

        #        self.pressure = pressure
        #        self.pressure_label.setText(f"{self.pressure} Torr")
        #        print("QATM read", self.pressure)
        if not self.dummy:
            indata = self.instrument.s.query("#02RD")
            print("read was called (IonGauge)", indata)
            self.pressure_label.setText(indata[3:])
            # Need to determine if .encode necessary otherwise use address #02 send read command (RD)
            # indata = self.s.read(self.buf)
            # not sure if above is needed
            data = indata

            try:
                pressure = float(data[4:])

            except ValueError:
                pressure = random.random()
                print(f"Ion Gauge: Error in read values: p={data[3:]}")

        else:
            data = self.pressure + np.random.normal(0, 900)
            pressure = round(data, 2)
            self.pressure_label.setText(f"{pressure}")

        return round(pressure, 3)

    def get_values(self):
        return self.pressure

    def close(self):
        self.IonGauge.close()

    def refresh(self):
        data = self.instrument.read()
        #        data2 = round(float(data), 2)
        #        print("refresh was called", data)
        self.pressure_label.setText(str(data))

    def send_command(self):

        # self.ATMreturn.setText(str(self.ATMcommand.text()))
        if (
            self.ATMcommand.text() != "RST"
            and self.ATMcommand.text() != "RD"
            and self.ATMcommand.text() != "TS"
            and self.ATMcommand.text() != "TZ"
            and self.ATMcommand.text() != "FAC"
            and self.ATMcommand.text() != "RSX"
            and self.ATMcommand.text() != "IGM1"
        ):
            self.ATMreturn.setText("WARNING: Not a Valid Command")

        else:
            text_cmd = self.ATMcommand.text()
            self.instrument.write(text_cmd)
            self.ATMreturn.setText(self.instrument.data[4:])
