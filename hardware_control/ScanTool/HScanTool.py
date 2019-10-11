from typing import List
import numpy as np
import json
import pkg_resources

import time

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
from hardware_control.QHelper import HC_Instrument
import copy


class HScanTool(QGroupBox):
    def __init__(
        self,
        window,
        name: str = "Scan Control",
        initialize_with: str = "DEFAULT",
        save_on_close: str = False,
    ):

        super().__init__(name)

        self.settings = {}
        self.save_on_close = save_on_close
        self.name = name
        self.app = window.app
        self.ignore = True

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

        self.arrow_symbol = QLabel()
        self.arrow_symbol.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "ScanTool/graphics/arrow.png"
                )
            )
        )
        self.arrow_symbol.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        # ****** DEFINE TEXT BOXES
        #
        self.instrument_label = QLabel("Instrument:")
        self.instrument_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.instrument_drop = QComboBox()
        self.instrument_drop.addItems(["----------"])
        self.instrument_drop.setCurrentText(self.settings["instrument"])
        self.instrument_drop.currentIndexChanged.connect(
            lambda: self.set_instrument(self.instrument_drop.currentText())
        )
        #
        self.parameter_label = QLabel("Parameter:")
        self.parameter_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.parameter_drop = QComboBox()
        self.parameter_drop.addItems(["----------"])
        self.parameter_drop.setCurrentText(self.settings["parameter"])
        self.parameter_drop.currentIndexChanged.connect(
            lambda: self.set_parameter(self.parameter_drop.currentText())
        )
        #
        self.values_label = QLabel("Values:")
        self.values_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.values_edit = QLineEdit()
        self.values_edit.editingFinished.connect(
            lambda: self.set_values(self.values_edit.text())
        )
        self.values_edit.setText(str(self.settings["values"]))
        #
        self.upper_grid = QGridLayout()
        self.middle_grid = QGridLayout()

        # Add widgets to grid layout
        self.upper_grid.addWidget(self.instrument_label, 0, 0)
        self.upper_grid.addWidget(self.instrument_drop, 1, 0)
        self.upper_grid.addWidget(self.arrow_symbol, 1, 1)
        self.upper_grid.addWidget(self.parameter_label, 0, 2)
        self.upper_grid.addWidget(self.parameter_drop, 1, 2)
        self.middle_grid.addWidget(self.values_label, 2, 0)
        self.middle_grid.addWidget(self.values_edit, 2, 1, 1, 2)

        self.scan_button = QPushButton()
        self.scan_button.setText("Scan")
        self.scan_button.setIcon(
            QIcon(
                (
                    QPixmap(
                        pkg_resources.resource_filename(
                            "hardware_control", "ScanTool/graphics/scan.png"
                        )
                    )
                )
            )
        )
        self.scan_button.setCheckable(False)
        self.scan_button.clicked.connect(self.scan)

        self.progress_grid = QGridLayout()
        #
        self.progress_label = QLabel("Scan Progress")
        self.progress_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.progress_bar = QProgressBar()
        #
        self.progress_grid.addWidget(self.progress_label, 0, 0)
        self.progress_grid.addWidget(self.progress_bar, 0, 1)
        #        self.progress_bar.setGeometry(200, 80, 250, 20);
        #
        self.progress_bar.setValue(self.settings["progress"])

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.upper_grid, 0, 0, 1, 2)
        self.master_layout.addLayout(self.middle_grid, 1, 0, 1, 2)
        self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 3)
        self.master_layout.addWidget(self.scan_button, 3, 0)
        self.setLayout(self.master_layout)

    def set_instrument(self, inst: str):
        print(f"Instrument set to '{inst}'")
        self.settings["instrument"] = inst

        self.parameter_drop.clear()
        params = []

        # update parameters menu options
        found = False
        for instrument in self.app.instruments:
            if instrument.name == inst:
                instr = instrument
                found = True

        if found:
            for param in instr.settings:
                params.append(param)
            self.parameter_drop.addItems(params)
            print(f"\tAdded {len(params)} items to parameter dropdown.")
        else:
            print(f"ERROR: Couldn't find instrument '{inst}'")

        self.settings["progress"] = 0
        self.progress_bar.setValue(self.settings["progress"])

    def set_parameter(self, param: str):
        print(f"Setting parameter to {param}")
        self.settings["parameter"] = param

        self.settings["progress"] = 0
        self.progress_bar.setValue(self.settings["progress"])

    def set_values(self, new_values: str):
        print(f"Setting values to {new_values}")
        self.settings["values"] = new_values

        self.settings["progress"] = 0
        self.progress_bar.setValue(self.settings["progress"])

    def scan(self):

        i = self.settings["instrument"]
        p = self.settings["parameter"]

        vals = self.settings["values"].split(",")
        print(f"Starting scan\n\tInstrument: {i}\n\tParameter: {p}\n\tValues:{vals}")

        # Find instrument, get current setting for parameter
        found = False
        for instr in self.app.instruments:
            if instr.name == self.settings["instrument"]:
                scan_instrument = instr
                found = True
                break
        if not found:
            print(f"ERROR: Failed to find instrument {i}")
            return

        # Scan through values
        count = 0
        for v in vals:
            self.settings["progress"] = count / len(vals) * 100
            print(f"\tRunning value = '{v}'\t\t{count/len(vals)*100}%")
            self.progress_bar.setValue(self.settings["progress"])

            if not scan_instrument.set_setting(self.settings["parameter"], v.strip()):
                print(f"Failed to set parameter '{p}' to value '{v}'. Exiting scan.")
                return
            count += 1

            time.sleep(0.5)

        self.settings["progress"] = 100
        self.progress_bar.setValue(self.settings["progress"])
        print("Finished scan")

    def update_instruments(self):
        self.instrument_drop.clear()
        names = []
        for inst in self.app.instruments:
            if inst.ignore:
                continue
            names.append(inst.name)
        self.instrument_drop.addItems(names)

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
