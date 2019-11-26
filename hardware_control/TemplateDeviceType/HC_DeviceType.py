from typing import List
import numpy as np
import json
import pkg_resources

import time  # Get rid of this guy!

import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator, QPixmap
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QWidget,
    QFormLayout,
    QGridLayout,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
)
import copy
from hardware_control.base import HC_Instrument, HC_Comm, setButtonState

class HC_DeviceType(HC_Instrument):
    # Convention: __init__(self, backend, window . . . )
    def __init__(
            self,
            backend,
            window,
            channels: list,
            name: str = "TemplateDevice",
            initialize_with: str = "INSTRUMENT",
            save_on_close: str = False,
    ):
        # initalizing
        super().__init__(window, name)
        self.settings = {}  # A dict to store all possible settings
        self.save_on_close = save_on_close
        self.backend = backend
        self.comm = HC_Comm(backend, self)
        #self.filename = ""  # currently not in use

        ### Create UI - example
        self.lineEdit = QLineEdit()
        self.lineEdit.setText("10")
        self.lineEdit.editingFinished.connect(lambda: self.command(self.lineEdit.text()))

        self.text = QLabel()
        self.text.setText("123")

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(0, 10)
        self.spinbox.setSingleStep(0.15)
        self.spinbox.editingFinished.connect((lambda: self.update_setting("Volt_Channel1", str(self.spinbox.value()))))

        self.layout = QGridLayout()
        self.layout.addWidget(self.lineEdit, 0, 0)
        self.layout.addWidget(self.text, 0, 1)
        self.layout.addWidget(self.spinbox, 1, 0)
        self.setLayout(self.layout)
        ###

        ### add your specific settings
        self.settings["Volt_Channel1"] = 123
        self.settings["Volt_Channel2"] = 456

        # Create timer to query
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(500)

        # Write state to Backend
        # this sends all settings, which are stored in the settings dictionary to the backend
        self.send_state()

    # Updates the readout
    def update_readout(self):
        self.command("RND")             #Sends readout command (for example)
        mess = self.read_message("RND") #recived messige will be stored, once available this will read it out, that way the UI wont freeze
        if mess:
            self.text.setText(mess)
