import json
import json

import pkg_resources
from PyQt5 import QtCore
from PyQt5.QtGui import QPixmap, QProgressBar, QIcon, QApplication, QSpacerItem, QSizePolicy
from PyQt5.QtWidgets import (
    QGroupBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QTableWidget,
    QWidget,
    QCheckBox,
)
from hardware_control.base import HC_Instrument


class HC_LoggerTool(HC_Instrument):
    def __init__(self, window, name: str = "Data Logger"):

        super().__init__(window, name)

        self.settings = {}
        self.name = name
        self.app = window.app
        self.ignore = True

        self.settings = self.default_state()

        # *************************Create GUI************************

        # self.arrow_symbol = QLabel()
        # self.arrow_symbol.setPixmap(QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/graphics/arrow.png")))
        # self.arrow_symbol.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        # # ****** DEFINE TEXT BOXES
        # #

        self.data_select_frame = QWidget()
        self.data_select_layout = QGridLayout()
        #
        self.dispgroup_label = QLabel("Logging Group:")
        self.dispgroup_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.dispgroup_drop = QComboBox()
        self.dispgroup_drop.addItems(["----------"])
        self.dispgroup_drop.setCurrentText(self.settings["display_group"])
        self.dispgroup_drop.currentIndexChanged.connect(lambda: self.set_group(self.dispgroup_drop.currentText()))
        #
        self.sidebar_v_spacer = QSpacerItem(20, 200, QSizePolicy.Minimum, QSizePolicy.Expanding)
        #
        self.data_select_layout.addWidget(self.dispgroup_label, 0, 0)
        self.data_select_layout.addWidget(self.dispgroup_drop, 1, 0)
        self.data_select_layout.addItem(self.sidebar_v_spacer, 2, 0)
        self.data_select_frame.setLayout(self.data_select_layout)

        self.data_disp_frame = QGroupBox("Data")
        #
        self.table = QTableWidget()
        self.table.setRowCount(4)
        self.table.setColumnCount(4)
        #
        self.autosave_check = QCheckBox("Autosave")
        # self.autosave_check.setChecked()
        self.autosave_check.stateChanged.connect(lambda: self.autosave_on_off(self.autosave_check.isChecked()))
        #
        self.save_interval_label = QLabel("Interval Time (s):")
        self.save_interval_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.save_interval_spacer = QSpacerItem(150, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        #
        self.save_interval_edit = QLineEdit()
        self.save_interval_edit.editingFinished.connect(lambda: self.set_interval(self.save_interval_edit.text()))
        # self.save_interval_edit.setText(str(self.settings["values"]))
        #
        self.save_button = QPushButton()
        self.save_button.setText("Save")
        self.save_button.clicked.connect(self.save_data)
        #
        self.clear_button = QPushButton()
        self.clear_button.setText("Erase Group Data")
        self.clear_button.clicked.connect(self.erase_group_data)
        #
        self.disp_frame_layout = QGridLayout()
        self.disp_frame_layout.addWidget(self.table, 0, 0, 1, 4)
        self.disp_frame_layout.addWidget(self.autosave_check, 1, 0)
        self.disp_frame_layout.addItem(self.save_interval_spacer, 1, 1)
        self.disp_frame_layout.addWidget(self.save_interval_label, 1, 2)
        self.disp_frame_layout.addWidget(self.save_interval_edit, 1, 3)
        self.disp_frame_layout.addWidget(self.save_button, 2, 0)
        self.disp_frame_layout.addWidget(self.clear_button, 2, 3)
        self.data_disp_frame.setLayout(self.disp_frame_layout)

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.data_select_frame, 0, 0)
        # self.master_layout.addLayout(self.middle_grid, 1, 0, 1, 2)
        # self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 3)
        self.master_layout.addWidget(self.data_disp_frame, 0, 1)
        self.setLayout(self.master_layout)

    def autosave_on_off(self, state:bool):
        pass

    def set_interval(self, t:str):
        pass

    def save_data(self):
        pass

    def erase_group_data(self):
        pass

    def set_group(self, group):
        pass

    def update_groups(self):

        self.dispgroup_drop.clear()

        names = [];
        for key in self.window.app.data_sets:
            names.append(key)
        self.dispgroup_drop.addItems(names)

    # def set_instrument(self, inst: str):
    #
    #     self.pDebug(f"Instrument set to '{inst}'")
    #
    #     self.settings["instrument"] = inst
    #
    #     self.parameter_drop.clear()
    #     params = []
    #
    #     # update parameters menu options
    #
    #     # If set to 'app variables' populate with app variables, not instrument settings
    #     if inst == "App Variables":
    #
    #         # Add app variables
    #         for v in self.app.variables:
    #             params.append(v)
    #         self.parameter_drop.addItems(params)
    #
    #     else:  # Is a real instrument name...
    #
    #         # Search for instrument....
    #         found = False
    #         for instrument in self.app.instruments:
    #             if instrument.name == inst:
    #                 instr = instrument
    #                 found = True
    #
    #         if found:
    #             for param in instr.settings:
    #                 params.append(param)
    #             self.parameter_drop.addItems(params)
    #             self.pDebug(f"\tAdded {len(params)} items to parameter dropdown.")
    #         else:
    #             self.pDebug(f"ERROR: Couldn't find instrument '{inst}'")
    #
    #     self.settings["progress"] = 0
    #     self.progress_bar.setValue(self.settings["progress"])
    #
    # def set_macro(self, mac: str):
    #     self.settings["macro"] = mac
    #
    # def update_macros(self):
    #     self.macro_drop.clear()
    #     names = ["None"]
    #     for m in self.app.macros:
    #         names.append(m)
    #     self.macro_drop.addItems(names)
    #
    # def set_parameter(self, param: str):
    #     self.pDebug(f"Setting parameter to {param}")
    #     self.settings["parameter"] = param
    #
    #     self.settings["progress"] = 0
    #     self.progress_bar.setValue(self.settings["progress"])
    #
    # def set_values(self, new_values: str):
    #     self.pDebug(f"Setting values to {new_values}")
    #     self.settings["values"] = new_values
    #
    #     self.settings["progress"] = 0
    #     self.progress_bar.setValue(self.settings["progress"])
    #
    # def scan(self):
    #
    #     # Get parameters, instrument, etc...
    #     i = self.settings["instrument"]
    #     p = self.settings["parameter"]
    #     m = self.settings["macro"]
    #     vals = self.settings["values"].split(",")
    #
    #     self.pDebug(f"Starting scan\n\tInstrument: {i}\n\tParameter: {p}\n\tValues:{vals}")
    #
    #     if i != "App variables":  # Is real instrument, not App Variable
    #
    #         # Find instrument, get current setting for parameter
    #         found = False
    #         for instr in self.app.instruments:
    #             if instr.name == self.settings["instrument"]:
    #                 scan_instrument = instr
    #                 found = True
    #                 break
    #         if not found:
    #             self.pDebug(f"ERROR: Failed to find instrument {i}")
    #             return
    #
    #         # Scan through values
    #         count = 0
    #         for v in vals:
    #
    #             # Update progress bar
    #             self.settings["progress"] = str(count / len(vals) * 100)
    #             # if self.app.print_debug:
    #             self.pDebug(f"\tRunning value = '{v}'\t\t{count/len(vals)*100}%")
    #             self.progress_bar.setValue(float(self.settings["progress"]))
    #             QApplication.processEvents()
    #
    #             # Update setting
    #             if not scan_instrument.set_setting(self.settings["parameter"], v.strip()):
    #                 self.pDebug(f"Failed to set parameter '{p}' to value '{v}'. Exiting scan.")
    #                 return
    #             count += 1
    #
    #             if m != "None":
    #                 self.pDebug(f"\t\tRunning macro {m}")
    #                 self.app.run_macro(self.app.macros[m])
    #
    #     else:
    #
    #         # Make sure variable exists
    #         if not (i in self.app.variables):
    #             self.pDebug("Failed to find app variable.")
    #             return
    #
    #         # Scan thorugh values
    #         count = 0
    #         for v in vals:
    #
    #             # Update progress bar
    #             self.settings["progress"] = count / len(vals) * 100
    #             # if self.app.print_debug:
    #             self.pDebug(f"\tRunning value = '{v}'\t\t{count/len(vals)*100}%")
    #             self.progress_bar.setValue(float(self.settings["progress"]))
    #             QApplication.processEvents()
    #
    #             # Change value of variable
    #             self.app.variables[i] = v.strip()  # Set value
    #             count += 1
    #
    #             if m != "None":
    #                 self.pDebug(f"\t\tRunning macro {m}")
    #                 self.app.run_macro(self.app.macros[m])
    #
    #     self.settings["progress"] = 100
    #     self.progress_bar.setValue(self.settings["progress"])
    #     self.pDebug("Finished scan")
    #
    # def update_instruments(self):
    #     self.instrument_drop.clear()
    #     names = []
    #     for inst in self.app.instruments:
    #         if inst.ignore:
    #             continue
    #         names.append(inst.name)
    #     if self.include_variables and not ("App Variables" in names):
    #         names.append("App Variables")
    #     self.instrument_drop.addItems(names)
    #
    # def load_state(self, filename: str):
    #
    #     # Get default state - this identifies all required fields
    #     dflt = self.default_state()
    #
    #     # Read a state from file
    #     try:
    #         with open(filename) as file:
    #             self.settings = json.load(file)
    #             self.pDebug(f"State for {self.comm.instr.ID} read from file '{filename}'")
    #     except:
    #         self.pDebug(f"ERROR: {self.name} failed to read file '{filename}'. Using defualt case.")
    #         self.settings = self.default_state()
    #
    #     # Ensure all fields in default_state are present in the loaded state
    #     for key in dflt:
    #         if not (key in self.settings):
    #             self.settings[key] = dflt[key]
    #
    # def save_state(self, filename: str):
    #     try:
    #         with open(filename, "w") as file:
    #             json.dump(self.settings, file)
    #             self.pDebug(f"State for {self.comm.instr.ID} saved to file '{filename}'")
    #     except Exception as e:
    #         self.pDebug(f"ERROR: Failed to write file '{filename}'. State not saved.")
    #         self.pDebug(f"\t{e}")
    #
    # # Update setting is overwritten so hc-commands can set values such as the
    # # progress bar.
    # #
    # def update_setting(self, setting: str, value: str):
    #
    #     try:
    #         self.settings[setting] = value
    #     except Exception as e:
    #         return
    #
    #     if setting == "progress":
    #         try:
    #             self.progress_bar.setValue(float(self.settings["progress"]))
    #         except:
    #             self.pDebug(f"ERROR: Can't convert {value} to float.")

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        dflt["display_group"] = ""
        # dflt["instrument"] = "----------"
        # dflt["parameter"] = "----------"
        # dflt["action_instrument"] = "----------"
        # dflt["action_parameter"] = "----------"
        # dflt["progress"] = "0"
        # dflt["macro"] = "None"

        return dflt
