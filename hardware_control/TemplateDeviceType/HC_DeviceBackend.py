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
)
import copy
from hardware_control.base import HC_Instrument, HC_Comm, setButtonState


class HC_DeviceType(HC_Instrument):
    def __init__(
        self,
        backend,
        window,
        channels: list,
        name: str = "TemplateDevice",
        initialize_with: str = "INSTRUMENT",
        save_on_close: str = False,
    ):

        super().__init__(window, name)
        
        #ToDo: move into HC_Instrument
        self.settings = {}
        self.save_on_close = save_on_close
        self.backend = backend
        self.comm = HC_Comm(backend, self)
        self.filename = ""

        ### Create UI

        ###

        #Todo:is that needed?
        # Write state to scope - synch scope with GUI
        self.send_state()
        #Todo """"
        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(500)

