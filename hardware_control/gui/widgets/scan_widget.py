import json
import logging
import time

import numpy as np
import zmq

import pyqtgraph as pg  # For some reason, without this line QPushButton won't import
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QProgressBar, QIcon, QApplication, QIntValidator
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
    QSizePolicy,
)

from ..base import Instrument
from .zmq_connection import ZMQConnectionTool
from .utility import load_icon

logger = logging.getLogger(__name__)


class FakeButton:
    def __init__(self, fakeText):

        self.str = fakeText

    def text(self):
        return self.str


class ScanWidget(Instrument):

    sigStartScan = pyqtSignal()

    def __init__(
        self, window, name: str = "Scan Control", include_variables: bool = True,
    ):

        super().__init__(window, name)

        self.settings = {}
        self.name = name
        self.app = window.app
        self.ignore = True
        self.ignore_control = True
        self.include_variables = include_variables
        self.val_list = []

        self.socket_addr = "tcp://127.0.0.1:5959"

        self.running_scan = False

        self.settings = self.default_state()

        # This ZMQConnectionTool will receive commands from the scan thread
        self.zmq_receiver = ZMQConnectionTool(
            window, f"{self.name}-ZMQ Receiver", self.socket_addr, 100
        )
        self.zmq_receiver.connectionOnOff(FakeButton("Disable Incoming Commands"))

        # *************************Create GUI************************
        self.arrow_symbol = QLabel()
        self.arrow_symbol.setPixmap(load_icon("arrow.png"))
        self.arrow_symbol.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        # ****** DEFINE TEXT BOXES
        self.instrument_label = QLabel("Instrument:")
        self.instrument_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.instrument_drop = QComboBox()
        self.instrument_drop.addItems(["----------"])
        self.instrument_drop.setCurrentText(self.settings["instrument"])
        self.instrument_drop.currentIndexChanged.connect(
            lambda: self.set_instrument(self.instrument_drop.currentText())
        )

        self.parameter_label = QLabel("Parameter:")
        self.parameter_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.parameter_drop = QComboBox()
        self.parameter_drop.addItems(["----------"])
        self.parameter_drop.setCurrentText(self.settings["parameter"])
        self.parameter_drop.currentIndexChanged.connect(
            lambda: self.update_local_setting(
                "parameter", self.parameter_drop.currentText()
            )
        )

        self.values_select_frame = QGridLayout()
        self.use_list = QRadioButton("List")
        self.use_space = QRadioButton("Spacing")
        self.use_file = QRadioButton("File")
        self.use_list.setChecked(True)

        self.values_label = QLabel("Values:")
        self.values_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.values_edit = QLineEdit()
        self.values_edit.textChanged.connect(
            lambda: self.update_local_setting("values", self.values_edit.text())
        )
        self.values_edit.setText(str(self.settings["values"]))

        self.spacing_start_label = QLabel("Start: ")
        self.spacing_start_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.spacing_start_edit = QLineEdit()

        self.spacing_end_label = QLabel("End: ")
        self.spacing_end_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.spacing_end_edit = QLineEdit()

        self.step_size_label = QLabel("step size: ")
        self.step_size_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.step_size_edit = QLineEdit()

        # self.spacing_log_check = QCheckBox("Log Spacing")

        self.values_file_label = QLabel("File:")
        self.values_file_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.values_file_edit = QLineEdit()

        self.values_file_select_button = QPushButton("Browse")
        self.values_file_select_button.clicked.connect(self.browse_values_files)

        self.values_select_box = QGroupBox()
        self.values_select_box.setStyleSheet("QGroupBox{padding-top:3px}")

        self.values_select_frame.addWidget(self.use_list, 0, 0, 1, 1)
        self.values_select_frame.addWidget(self.values_label, 0, 1, 1, 1)
        self.values_select_frame.addWidget(self.values_edit, 0, 2, 1, 6)

        self.values_select_frame.addWidget(self.use_space, 1, 0, 1, 1)
        self.values_select_frame.addWidget(self.spacing_start_label, 1, 1, 1, 1)
        self.values_select_frame.addWidget(self.spacing_start_edit, 1, 2, 1, 2)
        self.values_select_frame.addWidget(self.spacing_end_label, 1, 4, 1, 2)
        self.values_select_frame.addWidget(self.spacing_end_edit, 1, 6, 1, 2)
        self.values_select_frame.addWidget(self.step_size_label, 2, 1, 1, 1)
        self.values_select_frame.addWidget(self.step_size_edit, 2, 2, 1, 2)
        # self.values_select_frame.addWidget(self.spacing_log_check, 2, 6, 1, 2)

        self.values_select_frame.addWidget(self.use_file, 3, 0, 1, 1)
        self.values_select_frame.addWidget(self.values_file_label, 3, 1, 1, 1)
        self.values_select_frame.addWidget(self.values_file_edit, 3, 2, 1, 2)
        self.values_select_frame.addWidget(self.values_file_select_button, 3, 6, 1, 2)

        self.values_select_box.setLayout(self.values_select_frame)

        self.scan_opt_box = QGroupBox()
        self.scan_opt_box.setStyleSheet("QGroupBox{padding-top:3px}")
        self.scan_opt_frame = QGridLayout()

        self.macro_label = QLabel("Scan Action:")
        self.macro_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.action_drop = QComboBox()
        self.action_drop.addItems(["None"])
        self.action_drop.setCurrentText(self.settings["action"])
        self.action_drop.currentIndexChanged.connect(
            lambda: self.macro_changed(self.action_drop.currentText())
        )

        self.sync_measdir_check = QCheckBox("Sync Measurements")

        self.pause_label_before = QLabel("Pause before (sec):")
        self.pause_label_after = QLabel("Pause after (sec):")
        self.pause_timer_label_before = QLabel("0")
        self.pause_timer_label_after = QLabel("0")
        self.pause_label_before.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.pause_label_after.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.pause_timer_label_before.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.pause_timer_label_after.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )

        self.pause_edit_before = QLineEdit()
        self.pause_edit_before.setText("10")
        self.pause_edit_before.setValidator(QIntValidator())
        self.pause_edit_after = QLineEdit()
        self.pause_edit_after.setText("10")
        self.pause_edit_after.setValidator(QIntValidator())

        self.scan_opt_frame.addWidget(self.macro_label, 0, 0)
        self.scan_opt_frame.addWidget(self.action_drop, 0, 1)
        self.scan_opt_frame.addWidget(self.sync_measdir_check, 0, 3)
        self.scan_opt_frame.addWidget(self.pause_label_before, 1, 0)
        self.scan_opt_frame.addWidget(self.pause_label_after, 2, 0)
        self.scan_opt_frame.addWidget(self.pause_edit_before, 1, 1)
        self.scan_opt_frame.addWidget(self.pause_edit_after, 2, 1)
        self.scan_opt_frame.addWidget(self.pause_timer_label_before, 1, 3)
        self.scan_opt_frame.addWidget(self.pause_timer_label_after, 2, 3)

        self.scan_opt_box.setLayout(self.scan_opt_frame)

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

        self.upper_grid.addWidget(self.scan_opt_box, 3, 0, 1, 4)
        # self.middle_grid.addWidget(self.values_label, 2, 0)
        # self.middle_grid.addWidget(self.values_edit, 2, 1, 1, 2)

        self.scan_button = QPushButton()
        self.scan_button.setText("Scan")
        self.scan_button.setIcon(QIcon(load_icon("scan.png")))
        self.scan_button.setCheckable(False)
        self.scan_button.clicked.connect(self.start_scan_thread)
        self.scan_button.setSizePolicy(
            QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        )

        self.stop_button = QPushButton()
        self.stop_button.setText("Stop")
        self.stop_button.setIcon(QIcon(load_icon("stop.svg")))
        self.stop_button.setCheckable(False)
        self.stop_button.setSizePolicy(
            QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        )
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_scan)

        self.progress_grid = QGridLayout()

        self.progress_label = QLabel("Scan Progress")
        self.progress_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.progress_bar = QProgressBar()

        self.progress_grid.addWidget(self.progress_label, 0, 0)
        self.progress_grid.addWidget(self.progress_bar, 0, 1)

        self.progress_bar.setValue(float(self.settings["progress"]))

        # ******* DEFINE OVERALL LAYOUT
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.upper_grid, 0, 0, 1, 2)
        self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 2)
        self.master_layout.addWidget(self.scan_button, 3, 0)
        self.master_layout.addWidget(
            self.stop_button, 3, 1, alignment=QtCore.Qt.AlignRight
        )
        self.setLayout(self.master_layout)

    def update_local_setting(self, setting: str, value: str):

        self.settings[setting] = value

    def settings_to_UI(self):
        self.values_edit.setText(str(self.settings["values"]))
        self.instrument_drop.setCurrentText(self.settings["instrument"])
        self.parameter_drop.setCurrentText(self.settings["parameter"])
        self.progress_bar.setValue(float(self.settings["progress"]))
        self.action_drop.setCurrentText(self.settings["action"])
        self.pause_timer_label_before.setText(self.settings["before_countdown"])
        self.pause_timer_label_after.setText(self.settings["after_countdown"])

    def stop_scan(self):

        self.zmq_receiver.connectionOnOff(FakeButton("Disable Incoming Commands"))

    def browse_values_files(self):

        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getOpenFileName()
        filename = name_tuple[0]
        if not filename:  # If cancel bttonw as hit, name will be null
            return

        self.values_file_edit.setText(filename)

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

        self.settings["action"] = new_macro_name

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

    def update_actions(self):
        self.action_drop.clear()
        names = ["None"]
        for m in self.app.function_handles:
            names.append(m)
        self.action_drop.addItems(names)

    def compute_values(self):
        """ Reads the values of the widgets and computes the values for the scan
        to iterate over. """

        if self.use_list.isChecked():
            self.val_list = self.values_edit.text().split(",")
        elif self.use_space.isChecked():
            try:
                start = float(self.spacing_start_edit.text())
                end = float(self.spacing_end_edit.text())
                step_size = float(self.step_size_edit.text())
            except:
                logger.error("Invalid values for start, end, or step_size")
                return False

            self.val_list = [
                str(v) for v in np.arange(start, end + step_size, step_size)
            ]

        elif self.use_file.isChecked():
            filename = self.values_file_edit.text()
            if filename == "":
                logger.error("no filename provided for values file")
                return False

            # Read files
            with open(filename) as file:
                file_str = file.read().replace("\n", "")

            self.val_list = file_str.split(",")
        else:
            logger.error("No mode selected in scan tool")
            return False

        return True

    def start_scan_thread(self):

        # Make sure a scan not already in progress
        if self.running_scan:
            logger.warning("Cannot run scan while a scan is in progress")
            return

        self.zmq_receiver.restart_port()
        self.zmq_receiver.connectionOnOff(FakeButton("Accept Incoming Commands"))

        # Compute scan values
        if not self.compute_values():
            logger.warning("Failed to compute scan values")
            return

        # Get parameters, instrument, etc...
        i = self.instrument_drop.currentText()
        p = self.parameter_drop.currentText()
        m = self.action_drop.currentText()
        sync = self.sync_measdir_check.isChecked()
        delay_before = self.pause_edit_before.text()
        delay_after = self.pause_edit_after.text()

        # Generate a starting key and a socket address
        key = 10

        self.worker = ScanWorker(
            i,
            p,
            m,
            sync,
            self.val_list,
            key,
            self.socket_addr,
            int(delay_before),
            int(delay_after),
            self.name,
        )
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.finished.connect(self.scan_thread_finished)
        self.sigStartScan.connect(self.worker.run_scan)

        self.scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self.worker_thread.start()

        self.sigStartScan.emit()

    @pyqtSlot()
    def scan_thread_finished(self):

        self.zmq_receiver.connectionOnOff(FakeButton("Disable Incoming Commands"))

        self.scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.worker_thread.quit()

    def scan(self):

        # Compute scan values
        if not self.compute_values():
            return

        # Get parameters, instrument, etc...
        i = self.instrument_drop.currentText()
        p = self.parameter_drop.currentText()
        m = self.action_drop.currentText()
        sync = self.sync_measdir_check.isChecked()
        # vals = self.settings["values"].split(",")

        logger.debug(
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
            if p not in self.app.variables:
                logger.error("Failed to find app variable.")
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
            if inst.ignore_control:
                continue
            names.append(inst.name)
        if self.include_variables and ("App Variables" not in names):
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
            if key not in self.settings:
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
        except Exception:
            return

        if setting == "progress":
            try:
                self.progress_bar.setValue(float(self.settings["progress"]))
            except:
                logger.error(f"Can't convert {value} to float.", exc_info=True)

    def default_state(self):
        return {
            "values": "",
            "instrument": "----------",
            "parameter": "----------",
            "progress": "0",
            "action": "None",
            "macro": "None",
            "before_countdown": "10",
            "after_countdown": "10",
        }


class ScanWorker(QObject):

    finished = pyqtSignal()

    def __init__(
        self,
        instr,
        param,
        action,
        sync,
        vals,
        key,
        socket_addr,
        pause_before: int,
        pause_after: int,
        scan_tool_name,
    ):

        super().__init__()

        logger.info("Creating scan thread")

        self.instr = instr
        self.param = param
        self.action = action
        self.running = True
        self.sync = sync
        self.vals = vals
        self.pause_before = int(pause_before)
        self.pause_after = int(pause_after)
        self.scan_tool_name = scan_tool_name

        self.socket_addr = socket_addr

        self.timeout = 2e3

        context = zmq.Context()
        self.socket = context.socket(zmq.REQ)
        self.socket.connect(self.socket_addr)

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

        # Make sure vals is a list
        if not isinstance(vals, list):
            logger.error("Scan thread received single value instead of list")
            self.vals = [self.vals]

    def send_hc(self, command_str: str):
        """ Sends an hc Command to the  """

        self.socket.send_string(command_str)

        events = self.poller.poll(self.timeout)
        if len(events) < 1:
            return False

        rval = self.socket.recv_string()

        return True

    def is_busy(self):
        req_str = "MEAS:GETSTATE"
        self.socket.send(str.encode(req_str))
        rval = self.socket.recv()
        return rval == "Busy"

    @pyqtSlot()
    def run_scan(self):

        num_vals = len(self.vals)
        for idx, val in enumerate(self.vals):

            logger.debug(f"Using value {val}")

            # First set parameter to value
            if not self.send_hc(f"SET_UI:{self.instr}:{self.param}:{str(val)}"):
                break

            start_time = time.time()
            while time.time() - start_time < self.pause_before:
                time_elapsed = time.time() - start_time
                countdown_time = "{:05.1f}".format(self.pause_before - time_elapsed)
                if not self.send_hc(
                    f"SET_UI:{self.scan_tool_name}:before_countdown:{countdown_time}"
                ):
                    self.finished.emit()
                    return
                time.sleep(0.1)

            if not self.send_hc(f"SET_UI:{self.scan_tool_name}:before_countdown:{0}"):
                break

            # Second, run macro (if requested)
            if self.action != "None":
                if not self.send_hc(f"FUNC:{self.action}"):
                    break

            # Pause if requested
            start_time = time.time()
            while time.time() - start_time < self.pause_after:
                time_elapsed = time.time() - start_time
                countdown_time = "{:05.1f}".format(self.pause_after - time_elapsed)
                if not self.send_hc(
                    f"SET_UI:{self.scan_tool_name}:after_countdown:{countdown_time}"
                ):
                    self.finished.emit()
                    return
                time.sleep(0.1)

            if not self.send_hc(f"SET_UI:{self.scan_tool_name}:after_countdown:{0}"):
                break

            # Third, sync w/ MeasDir (if requested)
            if self.sync:
                while True:
                    if not self.is_busy():
                        break

            if not self.send_hc(
                f"SET_UI:{self.scan_tool_name}:progress:{100.0*(idx+1.0)/num_vals}"
            ):
                break

        # End thread
        self.finished.emit()
