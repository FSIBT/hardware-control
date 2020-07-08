import json
import logging
import numpy as np
import pkg_resources

import pyqtgraph as pg  # For some reason, without this line QPushButton won't import
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
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
    QFileDialog,
)
from hardware_control.base import HC_Instrument
from hardware_control.widgets.zmq_connection import HC_ZMQConnectionTool
import time
import zmq

logger = logging.getLogger(__name__)


class FakeButton:
    def __init__(self, fakeText):

        self.str = fakeText

    def text(self):
        return self.str


class HC_ScanTool(HC_Instrument):

    sigStartScan = pyqtSignal()

    def __init__(
        self, window, name: str = "Scan Control", include_variables: bool = True,
    ):

        super().__init__(window, name)

        self.settings = {}
        self.name = name
        self.app = window.app
        self.ignore = True
        self.include_variables = include_variables
        self.val_list = []

        self.socket_addr = "tcp://127.0.0.1:5555"

        self.running_scan = False

        self.settings = self.default_state()

        # This ZMQConnectionTool will receive commands from the scan thread
        self.zmq_receiver = HC_ZMQConnectionTool(
            window, f"{self.name}-ZMQ Receiver", self.socket_addr, 100
        )
        self.zmq_receiver.connectionOnOff(FakeButton("Disable Incoming Commands"))

        # *************************Create GUI************************

        self.arrow_symbol = QLabel()
        self.arrow_symbol.setPixmap(
            QPixmap(
                pkg_resources.resource_filename("hardware_control", "icons/arrow.png")
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
        # self.parameter_drop.currentIndexChanged.connect(
        #     lambda: self.set_parameter(self.parameter_drop.currentText())
        # )

        self.values_select_frame = QGridLayout()
        #
        # self.value_src_label = QLabel("Values source:")
        #
        self.use_list = QRadioButton("List")
        self.use_list.setChecked(True)
        # self.use_list.toggled.connect(lambda: self.values_src_set(self.use_list))
        #
        self.use_space = QRadioButton("Spacing")
        # self.use_space.toggled.connect(lambda: self.values_src_set(self.use_space))

        self.use_file = QRadioButton("File")
        # self.use_file.toggled.connect(lambda: self.values_src_set(self.use_file))

        # self.lin_rb = QRadioButton("Linear")
        # self.lin_rb.setChecked(True)
        # self.lin_rb.toggled.connect(lambda: self.space_rule_set(self.lin_rb))
        #
        # self.log_rb = QRadioButton("Logarithmic")
        # self.log_rb.toggled.connect(lambda: self.space_rule_set(self.log_rb))
        #
        self.values_label = QLabel("Values:")
        self.values_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.values_edit = QLineEdit()
        # self.values_edit.editingFinished.connect(
        #     lambda: self.set_values(self.values_edit.text())
        # )
        self.values_edit.setText(str(self.settings["values"]))
        #
        self.spacing_start_label = QLabel("Start: ")
        self.spacing_start_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.spacing_start_edit = QLineEdit()
        # self.spacing_start_edit.editingFinished.connect(lambda: self.set_start_value)

        self.spacing_end_label = QLabel("End: ")
        self.spacing_end_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.spacing_end_edit = QLineEdit()
        # self.spacing_end_edit.editingFinished.connect(lambda: self.set_end_value)

        self.num_points_label = QLabel("steps: ")
        self.num_points_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.num_points_edit = QLineEdit()
        # self.num_points_edit.editingFinished.connect(lambda: self.set_num_points)

        #
        self.spacing_log_check = QCheckBox("Log Spacing")
        #
        self.values_file_label = QLabel("File:")
        self.values_file_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.values_file_edit = QLineEdit()
        #
        self.values_file_select_button = QPushButton("Browse")
        self.values_file_select_button.clicked.connect(self.browse_values_files)

        self.values_select_box = QGroupBox()
        self.values_select_box.setStyleSheet("QGroupBox{padding-top:3px}")

        self.values_select_frame.addWidget(self.use_list, 0, 0, 1, 1)
        self.values_select_frame.addWidget(self.values_label, 0, 1, 1, 1)
        self.values_select_frame.addWidget(self.values_edit, 0, 2, 1, 6)
        #
        self.values_select_frame.addWidget(self.use_space, 1, 0, 1, 1)
        self.values_select_frame.addWidget(self.spacing_start_label, 1, 1, 1, 1)
        self.values_select_frame.addWidget(self.spacing_start_edit, 1, 2, 1, 2)
        self.values_select_frame.addWidget(self.spacing_end_label, 1, 4, 1, 2)
        self.values_select_frame.addWidget(self.spacing_end_edit, 1, 6, 1, 2)
        self.values_select_frame.addWidget(self.num_points_label, 2, 1, 1, 1)
        self.values_select_frame.addWidget(self.num_points_edit, 2, 2, 1, 2)
        self.values_select_frame.addWidget(self.spacing_log_check, 2, 6, 1, 2)
        #
        self.values_select_frame.addWidget(self.use_file, 3, 0, 1, 1)
        self.values_select_frame.addWidget(self.values_file_label, 3, 1, 1, 1)
        self.values_select_frame.addWidget(self.values_file_edit, 3, 2, 1, 2)
        self.values_select_frame.addWidget(self.values_file_select_button, 3, 6, 1, 2)

        self.values_select_box.setLayout(self.values_select_frame)

        #
        self.macro_label = QLabel("Scan Macro:")
        self.macro_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.macro_drop = QComboBox()
        self.macro_drop.addItems(["None"])
        self.macro_drop.setCurrentText(self.settings["macro"])
        self.macro_drop.currentIndexChanged.connect(
            lambda: self.macro_changed(self.macro_drop.currentText())
        )
        #
        #
        self.sync_measdir_check = QCheckBox("Sync Measurements")
        #
        self.upper_grid = QGridLayout()
        self.middle_grid = QGridLayout()

        # Add widgets to grid layout
        self.upper_grid.addWidget(self.instrument_label, 0, 0, 1, 2)
        self.upper_grid.addWidget(self.instrument_drop, 1, 0, 1, 2)
        self.upper_grid.addWidget(self.arrow_symbol, 1, 2)
        self.upper_grid.addWidget(self.parameter_label, 0, 3)
        self.upper_grid.addWidget(self.parameter_drop, 1, 3)

        # self.upper_grid.addLayout(self.values_select_frame, 2, 0, 1, 4)
        self.upper_grid.addWidget(self.values_select_box, 2, 0, 1, 4)

        self.upper_grid.addWidget(self.sync_measdir_check, 3, 3)
        self.upper_grid.addWidget(self.macro_label, 3, 0)
        self.upper_grid.addWidget(self.macro_drop, 3, 1)
        # self.middle_grid.addWidget(self.values_label, 2, 0)
        # self.middle_grid.addWidget(self.values_edit, 2, 1, 1, 2)

        self.scan_button = QPushButton()
        self.scan_button.setText("Scan")
        self.scan_button.setIcon(
            QIcon(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", "icons/scan.png"
                    )
                )
            )
        )
        self.scan_button.setCheckable(False)
        self.scan_button.clicked.connect(self.start_scan_thread)

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

    # def space_rule_set(self, rule):
    #     pass
    #
    # def values_src_set(self, rule):
    #     pass
    #
    def browse_values_files(self):

        filename = ""

        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getOpenFileName()
        filename = name_tuple[0]
        if not filename:  # If cancel bttonw as hit, name will be null
            return

        self.values_file_edit.setText(filename)

    #
    # def set_end_value(self):
    #     pass
    #
    # def set_start_value(self):
    #     pass
    #
    # def set_num_points(self):
    #     pass

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

    def macro_changed(self, new_macro_name: str):
        """ Called when the macro selection is changed. Checks to see if the macro
        submits a measurementrequest, if so, it sets the 'sync with director' check
        to true, otherwise sets it to false. """

        # Quit if macro can't be found
        if new_macro_name not in self.app.macros:
            logger.error(
                f"Failed to find macro {new_macro_name} despite being option in dropdown"
            )
            return

        all_cmds = "".join(self.app.macros[new_macro_name])
        if "MEAS:REQ" in all_cmds.upper():
            self.sync_measdir_check.setChecked(True)
        else:
            self.sync_measdir_check.setChecked(False)

    def update_macros(self):
        self.macro_drop.clear()
        names = ["None"]
        for m in self.app.macros:
            names.append(m)
        self.macro_drop.addItems(names)

    # def set_parameter(self, param: str):
    #     logger.debug(f"Setting parameter to {param}")
    #     self.settings["parameter"] = param
    #
    #     self.settings["progress"] = 0
    #     self.progress_bar.setValue(self.settings["progress"])
    #
    # def set_values(self, new_values: str):
    #     """ Changes the internal values parameter to a new value """
    #
    #     logger.debug(f"Setting values to {new_values}")
    #     self.settings["values"] = new_values
    #
    #     self.settings["progress"] = 0
    #     self.progress_bar.setValue(self.settings["progress"])

    def compute_values(self):
        """ Reads the values of the widgets and computes the values for the scan
        to iterate over. """

        # Get value entry mode from radiobuttons
        mode = None
        if self.use_list.isChecked():
            mode = "list"
        elif self.use_space.isChecked():
            mode = "space"
        elif self.use_file.isChecked():
            mode = "file"

        # Make sure a radiobutton is selected
        if mode is None:

            logger.error("No mode selected in scan tool")
            return False

        if mode == "list":  # Saves as strings

            # Break values at commas
            self.val_list = self.values_edit.text().split(",")

        elif mode == "space":  # Saves as floats

            # Read start, end, num points
            try:
                start = float(self.spacing_start_edit.text())
                end = float(self.spacing_end_edit.text())
                num_points = float(self.num_points_edit.text())
            except:
                logger.error(f"Invalid values for start, end, or num_points")
                return False

            # Generate log/lin spacing
            if self.spacing_log_check.isChecked():

                # Make sure 'start' isn't too low
                if start <= 0:
                    start = 1

                self.val_list = np.logspace(
                    np.log10(start), np.log10(end), int(num_points)
                )
            else:
                self.val_list = np.linspace(start, end, int(num_points))

        elif mode == "file":  # Saves as strings

            filename = self.values_file_edit.text()
            if filename == "":
                logger.error("no filename provided for values file")
                return False

            # Read files
            with open(filename) as file:
                file_str = file.read().replace("\n", "")

            self.val_list = file_str.split(",")

        return True

    def start_scan_thread(self):

        self.zmq_receiver.connectionOnOff(FakeButton("Accept Incoming Commands"))

        # Make sure a scan not already in progress
        if self.running_scan:
            logger.warning("Cannot run scan while a scan is in progress")
            return

        # Compute scan values
        if not self.compute_values():
            return

        # Get parameters, instrument, etc...
        i = self.instrument_drop.currentText()
        p = self.parameter_drop.currentText()
        m = self.macro_drop.currentText()
        sync = self.sync_measdir_check.isChecked()

        # Generate a starting key and a socket address
        key = 10

        self.worker = ScanWorker(i, p, m, sync, self.val_list, key, self.socket_addr)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.finished.connect(self.scan_thread_finished)
        self.sigStartScan.connect(self.worker.run_scan)

        self.scan_button.setEnabled(False)

        self.worker_thread.start()

        self.sigStartScan.emit()

    @pyqtSlot()
    def scan_thread_finished(self):

        print("ending thread")

        self.zmq_receiver.connectionOnOff(FakeButton("Disable Incoming Commands"))

        self.scan_button.setEnabled(True)
        self.worker_thread.quit()

    def scan(self):

        # Compute scan values
        if not self.compute_values():
            return

        # Get parameters, instrument, etc...
        i = self.instrument_drop.currentText()
        p = self.parameter_drop.currentText()
        m = self.macro_drop.currentText()
        sync = self.sync_measdir_check.isChecked()
        # vals = self.settings["values"].split(",")

        logger.debug(
            f"Starting scan\n\tInstrument: {i}\n\tParameter: {p}\n\tValues:{self.val_list}"
        )
        print(
            f"Starting scan\n\tInstrument: {i}\n\tParameter: {p}\n\tValues:{self.val_list}"
        )

        if i != "App Variables":  # Is real instrument, not App Variable

            # Find instrument, get current setting for parameter
            found = False
            for instr in self.app.instruments:
                if instr.name == self.settings["instrument"]:
                    scan_instrument = instr
                    found = True
                    break
            if not found:
                logger.error(f"Failed to find instrument {i}")
                return

            # Scan through values
            count = 0
            for v in self.val_list:

                # Update progress bar
                self.settings["progress"] = str(count / len(self.val_list) * 100)
                logger.debug(
                    f"\tRunning value = '{v}'\t\t{count/len(self.val_list)*100}%"
                )
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

                # Run Macro (if macro selected)
                if m != "None":
                    logger.debug(f"\t\tRunning macro {m}")
                    self.app.run_macro(self.app.macros[m])

                # Sync with director (if box checked)
                if (
                    self.sync_measdir_check.isChecked()
                ):  # Todo: Put this function in new thread, prevent blocking
                    while self.app.director.get_state().upper() == "BUSY":
                        time.sleep(0.1)

        else:

            # Make sure variable exists
            if not (p in self.app.variables):
                logger.error("Failed to find app variable.")
                print(self.app.variables)
                return

            # Scan thorugh values
            count = 0
            for v in self.val_list:

                # Update progress bar
                self.settings["progress"] = count / len(self.val_list) * 100
                logger.debug(
                    f"\tRunning value = '{v}'\t\t{count/len(self.val_list)*100}%"
                )
                self.progress_bar.setValue(float(self.settings["progress"]))
                QApplication.processEvents()

                # Change value of variable
                self.app.variables[p] = v.strip()  # Set value
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


class ScanWorker(QObject):

    finished = pyqtSignal()

    def __init__(self, instr, param, macro, sync, vals, key, socket_addr):

        super().__init__()

        self.instr = instr
        self.param = param
        self.macro = macro
        self.sync = sync
        self.vals = vals

        self.socket_addr = socket_addr

        context = zmq.Context()
        print("Connecting to Control")
        self.socket = context.socket(zmq.REQ)
        self.socket.connect(self.socket_addr)

        # Make sure vals is a list
        if type(vals) != list:
            logger.error("Scan thread received single value instead of list")
            self.vals = [self.vals]

    def send_hc(self, command_str: str):
        """ Sends an HC Command to the  """

        # print(f"Sending {command_str}")
        self.socket.send(str.encode(command_str))
        rval = self.socket.recv()
        # print("\t"+str(rval));

    def is_busy(self):
        req_str = "MEAS:GETSTATE"
        socket.send(str.encode(req_str))
        rval = socket.recv()
        return rval == "Busy"

    @pyqtSlot()
    def run_scan(self):

        for val in self.vals:

            print(val)

            # First set parameter to value
            self.send_hc(f"SET:{self.instr}:{self.param}:{str(val)}")

            # Second, run macro (if requested)
            if self.macro != "None":
                pass
                self.send_hc(f"FUNC:run:{self.macro}")

            time.sleep(1)

            # Third, sync w/ MeasDir (if requested)
            if self.sync:
                while True:
                    if not self.is_busy():
                        break

        print("done")

        # End thread
        self.finished.emit()
