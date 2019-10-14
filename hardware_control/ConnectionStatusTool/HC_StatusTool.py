from typing import List
import numpy as np
import json
import pkg_resources

import time  # Get rid of this guy!

import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QDoubleValidator, QPixmap, QProgressBar, QIcon
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
from hardware_control.base import HC_Instrument
import copy


class HC_StatusTool(QGroupBox):
    def __init__(
        self,
        window,
        name: str = "Connection Status",
        initialize_with: str = "DEFAULT",
        save_on_close: str = False,
    ):

        super().__init__(name)

        self.settings = {}
        self.save_on_close = save_on_close
        self.name = name
        self.app = window.app
        self.ignore = True

        self.green_indicator = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", "ConnectionStatusTool/graphics/ind_green.png"
            )
        )
        self.grey_indicator = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", "ConnectionStatusTool/graphics/ind_grey.png"
            )
        )
        self.red_indicator = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", "ConnectionStatusTool/graphics/ind_red.png"
            )
        )

        # Initialize state to correct values
        if initialize_with == "INSTRUMENT":
            self.save_on_close = False
            # Can't save without filename
            self.settings = self.initialize_gui_instrument()
        elif initialize_with == "DEFAULT":
            self.save_on_close = False
            # Can't save without filename
            self.settings = self.default_state()
        else:
            self.load_state(initialize_with)
            self.filename = initialize_with

        # *************************Create GUI************************

        #        self.arrow_symbol = QLabel();
        #        self.arrow_symbol.setPixmap(QPixmap(pkg_resources.resource_filename('hardware_control', 'ScanTool/graphics/arrow.png')));
        #        self.arrow_symbol.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        #
        self.instruments_label = QLabel()
        self.instruments_label.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "ConnectionStatusTool/graphics/status_label.png"
                )
            )
        )
        self.instruments_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        #
        self.instrument_grid = QGridLayout()

        # Add widgets to grid layout
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.instruments_label, 0, 0, 1, 1)
        self.master_layout.addLayout(self.instrument_grid, 1, 0, 1, 1)
        self.setLayout(self.master_layout)

        # Connect timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)
        # 1s period

    def update_instruments(self):

        # Clear layout
        for i in reversed(range(self.instrument_grid.count())):
            self.instrument_grid.itemAt(i).widget().setParent(None)

        row = 0
        for inst in self.app.instruments:

            if inst.ignore:
                continue

            label = QLabel(inst.name)
            indicator = QLabel()
            indicator.setPixmap(self.grey_indicator)
            indicator.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            self.instrument_grid.addWidget(label, row, 0)
            self.instrument_grid.addWidget(indicator, row, 1)
            row += 1

    def update_status(self):

        for i in range(self.instrument_grid.count()):
            if i % 2 == 0:  # Only want even indecies - these are instrument names

                for instr in self.app.instruments:
                    if (
                        instr.name == self.instrument_grid.itemAt(i).widget().text()
                    ):  # Found instrument....
                        if instr.status:
                            self.instrument_grid.itemAt(i + 1).widget().setPixmap(
                                self.green_indicator
                            )
                        else:
                            self.instrument_grid.itemAt(i + 1).widget().setPixmap(
                                self.red_indicator
                            )

    def load_state(self, filename: str):

        # Get default state - this identifies all required fields
        dflt = self.default_state()

        # Read a state from file
        try:
            with open(filename) as file:
                self.settings = json.load(file)
                print(f"State for {self.comm.instr.ID} read from file '{filename}'")
        except:
            print(f"ERROR: Failed to read file '{filename}'. Using defualt case.")
            self.settings = self.default_state()

        # Ensure all fields in default_state are present in the loaded state
        for key in dflt:
            if not (key in self.settings):
                self.settings[key] = dflt[key]

    def save_state(self, filename: str):
        try:
            with open(filename, "w") as file:
                json.dump(self.settings, file)
                print(f"State for {self.comm.instr.ID} saved to file '{filename}'")
        except Exception as e:
            print(f"ERROR: Failed to write file '{filename}'. State not saved.")
            print(f"\t{e}")

    #
    # Close connection
    #
    def close(self, filename: str = ""):

        # Save state if asked
        if self.save_on_close:
            self.save_state(self.filename)

        # Tell scope to close
        self.comm.close()

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        dflt["values"] = ""
        dflt["instrument"] = "----------"
        dflt["parameter"] = "----------"
        dflt["action_instrument"] = "----------"
        dflt["action_parameter"] = "----------"
        dflt["progress"] = 0

        return dflt
