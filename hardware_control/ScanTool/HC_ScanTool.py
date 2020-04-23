import json
import json

import pkg_resources
from PyQt5 import QtCore
from PyQt5.QtGui import QPixmap, QProgressBar, QIcon, QApplication
from PyQt5.QtWidgets import (
    QGroupBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QRadioButton,
    QCheckBox,
)
from hardware_control.base import HC_Instrument
import logging

logger = logging.getLogger(__name__)


class HC_ScanTool(HC_Instrument):
    def __init__(
        self,
        window,
        name: str = "Scan Control",
        initialize_with: str = "DEFAULT",
        save_on_close: str = False,
        include_variables: bool = True,
    ):

        super().__init__(window, name)

        self.settings = {}
        self.save_on_close = save_on_close
        self.name = name
        self.app = window.app
        self.ignore = True
        self.include_variables = include_variables

        # # Initialize state to correct values
        # if initialize_with == "INSTRUMENT":
        #     self.save_on_close = False
        #     # Can't save without filename
        #     self.settings = self.initialize_gui_instrument()
        # elif initialize_with == "DEFAULT":
        #     self.save_on_close = False
        #     # Can't save without filename
        self.settings = self.default_state()
        # else:
        #     self.load_state(initialize_with)
        #     self.filename = initialize_with

        # *************************Create GUI************************

        self.arrow_symbol = QLabel()
        self.arrow_symbol.setPixmap(
            QPixmap(
                pkg_resources.resource_filename(
                    "hardware_control", "graphics/arrow.png"
                )
            )
        )
        self.arrow_symbol.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        # ****** DEFINE TEXT BOXES
        #
        self.instrument_label = QLabel("Instrument:")
        self.instrument_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.instrument_drop = QComboBox()
        self.instrument_drop.addItems(["----------"])
        self.instrument_drop.setCurrentText(self.settings["instrument"])
        self.instrument_drop.currentIndexChanged.connect(
            lambda: self.set_instrument(self.instrument_drop.currentText())
        )
        #
        self.parameter_label = QLabel("Parameter:")
        self.parameter_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.parameter_drop = QComboBox()
        self.parameter_drop.addItems(["----------"])
        self.parameter_drop.setCurrentText(self.settings["parameter"])
        self.parameter_drop.currentIndexChanged.connect(
            lambda: self.set_parameter(self.parameter_drop.currentText())
        )

        self.values_select_frame = QGridLayout()
        #
        # self.value_src_label = QLabel("Values source:")
        #
        self.use_list = QRadioButton("List")
        self.use_list.setChecked(True)
        self.use_list.toggled.connect(lambda: self.values_src_set(self.use_list))
        #
        self.use_space = QRadioButton("Spacing")
        self.use_space.toggled.connect(lambda: self.values_src_set(self.use_space))

        self.use_file = QRadioButton("File")
        self.use_file.toggled.connect(lambda: self.values_src_set(self.use_file))

        self.lin_rb = QRadioButton("Linear")
        self.lin_rb.setChecked(True)
        self.lin_rb.toggled.connect(lambda: self.space_rule_set(self.lin_rb))
        #
        self.log_rb = QRadioButton("Logarithmic")
        self.log_rb.toggled.connect(lambda: self.space_rule_set(self.log_rb))
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
        self.spacing_start_label = QLabel("Start: ")
        self.spacing_start_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.spacing_start_edit = QLineEdit()
        self.spacing_start_edit.editingFinished.connect(lambda: self.set_start_value)

        self.spacing_end_label = QLabel("End: ")
        self.spacing_end_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.spacing_end_edit = QLineEdit()
        self.spacing_end_edit.editingFinished.connect(lambda: self.set_end_value)
        #
        self.spacing_log_check = QCheckBox("Log Spacing")
        #
        self.values_file_label = QLabel("Source file:")
        self.values_file_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.values_file_edit = QLineEdit()
        #
        self.values_file_select_button = QPushButton("Browse")
        self.values_file_select_button.clicked.connect(self.browse_values_files)

        self.values_select_frame.addWidget(self.use_list, 0, 0, 1, 1)
        self.values_select_frame.addWidget(self.values_label, 0, 1, 1, 1)
        self.values_select_frame.addWidget(self.values_edit, 0, 2, 1, 6)
        #
        self.values_select_frame.addWidget(self.use_space, 1, 0, 1, 1)
        self.values_select_frame.addWidget(self.spacing_start_label, 1, 1, 1, 1)
        self.values_select_frame.addWidget(self.spacing_start_edit, 1, 2, 1, 3)
        self.values_select_frame.addWidget(self.spacing_end_label, 1, 4, 1, 2)
        self.values_select_frame.addWidget(self.spacing_end_edit, 1, 6, 1, 2)
        self.values_select_frame.addWidget(self.spacing_log_check, 2, 4, 1, 2)
        #
        self.values_select_frame.addWidget(self.use_file, 3, 0, 1, 1)
        self.values_select_frame.addWidget(self.values_file_label, 3, 1, 1, 2)
        self.values_select_frame.addWidget(self.values_file_edit, 3, 3, 1, 3)
        self.values_select_frame.addWidget(self.values_file_select_button, 3, 6, 1, 2)

        #
        self.macro_label = QLabel("Scan Macro:")
        self.macro_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.macro_drop = QComboBox()
        self.macro_drop.addItems(["None"])
        self.macro_drop.setCurrentText(self.settings["macro"])
        self.macro_drop.currentIndexChanged.connect(
            lambda: self.set_macro(self.macro_drop.currentText())
        )
        #

        #
        self.upper_grid = QGridLayout()
        self.middle_grid = QGridLayout()

        # Add widgets to grid layout
        self.upper_grid.addWidget(self.instrument_label, 0, 0)
        self.upper_grid.addWidget(self.instrument_drop, 1, 0)
        self.upper_grid.addWidget(self.arrow_symbol, 1, 1)
        self.upper_grid.addWidget(self.parameter_label, 0, 2)
        self.upper_grid.addWidget(self.parameter_drop, 1, 2)

        self.upper_grid.addLayout(self.values_select_frame, 2, 0, 1, 3)

        self.upper_grid.addWidget(self.macro_label, 3, 0, 1, 2)
        self.upper_grid.addWidget(self.macro_drop, 3, 2)
        # self.middle_grid.addWidget(self.values_label, 2, 0)
        # self.middle_grid.addWidget(self.values_edit, 2, 1, 1, 2)

        self.scan_button = QPushButton()
        self.scan_button.setText("Scan")
        self.scan_button.setIcon(
            QIcon(
                (
                    QPixmap(
                        pkg_resources.resource_filename(
                            "hardware_control", "graphics/scan.png"
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
        self.progress_bar.setValue(float(self.settings["progress"]))

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.upper_grid, 0, 0, 1, 2)
        # self.master_layout.addLayout(self.middle_grid, 1, 0, 1, 2)
        self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 2)
        self.master_layout.addWidget(self.scan_button, 3, 0)
        self.setLayout(self.master_layout)

    def space_rule_set(self, rule):
        pass

    def values_src_set(self, rule):
        pass

    def browse_values_files(self):
        pass

    def set_end_value(self):
        pass

    def set_start_value(self):
        pass

    def set_instrument(self, inst: str):

        logger.debug(f"Instrument set to '{inst}'")

        self.settings["instrument"] = inst

        self.parameter_drop.clear()
        params = []

        # update parameters menu options

        # If set to 'app variables' populate with app variables, not instrument settings
        if inst == "App Variables":

            # Add app variables
            for v in self.app.variables:
                params.append(v)
            self.parameter_drop.addItems(params)

        else:  # Is a real instrument name...

            # Search for instrument....
            found = False
            for instrument in self.app.instruments:
                if instrument.name == inst:
                    instr = instrument
                    found = True

            if found:
                for param in instr.settings:
                    params.append(param)
                self.parameter_drop.addItems(params)
                logger.debug(f"\tAdded {len(params)} items to parameter dropdown.")
            else:
                logger.error(f"Couldn't find instrument '{inst}'")

        self.settings["progress"] = 0
        self.progress_bar.setValue(self.settings["progress"])

    def set_macro(self, mac: str):
        self.settings["macro"] = mac

    def update_macros(self):
        self.macro_drop.clear()
        names = ["None"]
        for m in self.app.macros:
            names.append(m)
        self.macro_drop.addItems(names)

    def set_parameter(self, param: str):
        logger.debug(f"Setting parameter to {param}")
        self.settings["parameter"] = param

        self.settings["progress"] = 0
        self.progress_bar.setValue(self.settings["progress"])

    def set_values(self, new_values: str):
        logger.debug(f"Setting values to {new_values}")
        self.settings["values"] = new_values

        self.settings["progress"] = 0
        self.progress_bar.setValue(self.settings["progress"])

    def scan(self):

        # Get parameters, instrument, etc...
        i = self.settings["instrument"]
        p = self.settings["parameter"]
        m = self.settings["macro"]
        vals = self.settings["values"].split(",")

        logger.debug(
            f"Starting scan\n\tInstrument: {i}\n\tParameter: {p}\n\tValues:{vals}"
        )

        if i != "App variables":  # Is real instrument, not App Variable

            # Find instrument, get current setting for parameter
            found = False
            for instr in self.app.instruments:
                if instr.name == self.settings["instrument"]:
                    scan_instrument = instr
                    found = True
                    break
            if not found:
                logger.errro(f"Failed to find instrument {i}")
                return

            # Scan through values
            count = 0
            for v in vals:

                # Update progress bar
                self.settings["progress"] = str(count / len(vals) * 100)
                logger.debug(f"\tRunning value = '{v}'\t\t{count/len(vals)*100}%")
                self.progress_bar.setValue(float(self.settings["progress"]))
                QApplication.processEvents()

                # Update setting
                if not scan_instrument.set_setting(
                    self.settings["parameter"], v.strip()
                ):
                    logger.error(
                        f"Failed to set parameter '{p}' to value '{v}'. Exiting scan."
                    )
                    return
                count += 1

                if m != "None":
                    logger.debug(f"\t\tRunning macro {m}")
                    self.app.run_macro(self.app.macros[m])

        else:

            # Make sure variable exists
            if not (i in self.app.variables):
                logger.error("Failed to find app variable.")
                return

            # Scan thorugh values
            count = 0
            for v in vals:

                # Update progress bar
                self.settings["progress"] = count / len(vals) * 100
                logger.debug(f"\tRunning value = '{v}'\t\t{count/len(vals)*100}%")
                self.progress_bar.setValue(float(self.settings["progress"]))
                QApplication.processEvents()

                # Change value of variable
                self.app.variables[i] = v.strip()  # Set value
                count += 1

                if m != "None":
                    logger.debug(f"\t\tRunning macro {m}")
                    self.app.run_macro(self.app.macros[m])

        self.settings["progress"] = 100
        self.progress_bar.setValue(self.settings["progress"])
        logger.debug("Finished scan")

    def update_instruments(self):
        self.instrument_drop.clear()
        names = []
        for inst in self.app.instruments:
            if inst.ignore:
                continue
            names.append(inst.name)
        if self.include_variables and not ("App Variables" in names):
            names.append("App Variables")
        self.instrument_drop.addItems(names)

    def load_state(self, filename: str):

        # Get default state - this identifies all required fields
        dflt = self.default_state()

        # Read a state from file
        try:
            with open(filename) as file:
                self.settings = json.load(file)
                logger.debug(
                    f"State for {self.comm.instr.ID} read from file '{filename}'"
                )
        except:
            logger.error(
                f"{self.name} failed to read file '{filename}'. Using defualt case.",
                exc_info=True,
            )
            self.settings = self.default_state()

        # Ensure all fields in default_state are present in the loaded state
        for key in dflt:
            if not (key in self.settings):
                self.settings[key] = dflt[key]

    def save_state(self, filename: str):
        try:
            with open(filename, "w") as file:
                json.dump(self.settings, file)
                logger.debug(
                    f"State for {self.comm.instr.ID} saved to file '{filename}'"
                )
        except Exception as e:
            logger.debug(f"ERROR: Failed to write file '{filename}'. State not saved.")
            logger.debug(f"\t{e}")

    # Update setting is overwritten so hc-commands can set values such as the
    # progress bar.
    #
    def update_setting(self, setting: str, value: str):

        try:
            self.settings[setting] = value
        except Exception as e:
            return

        if setting == "progress":
            try:
                self.progress_bar.setValue(float(self.settings["progress"]))
            except:
                logger.error(f"Can't convert {value} to float.", exc_info=True)

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
        dflt["progress"] = "0"
        dflt["macro"] = "None"

        return dflt
