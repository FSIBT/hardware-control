import json
import logging
import time

import numpy as np

import pyqtgraph as pg  # For some reason, without this line QPushButton won't import
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QObject
from PyQt5.QtGui import QProgressBar, QIcon, QApplication, QIntValidator, QGroupBox
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
from .utility import load_icon

logger = logging.getLogger(__name__)


class ScanWidget(QGroupBox):
    def __init__(self, app, name, actions, regressor=None, measure_value=None):
        """
        Parameters
        ----------
        app :
            The main app
        name : str
            The name of the groupbox
        actions : dict
            A dictionary with names of the action as keys and function to call during the scan
        """

        super().__init__(name)

        self.app = app

        self.actions = actions

        self.scan_instrument = None
        self.scan_parameter = None
        self.scan_action = None
        self.scan_progress = 0

        self.values = ""
        self.val_list = []
        self.count = 0
        self.number_of_values = 0
        self.GPRegressor = regressor

        if self.GPRegressor:
            self.measure_value = self.app.main_window.tab7.get_measured_values

        # *************************Create GUI************************
        self.arrow_symbol = QLabel()
        self.arrow_symbol.setPixmap(load_icon("arrow.png"))
        self.arrow_symbol.setAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        # ****** DEFINE TEXT BOXES
        self.instrument_label = QLabel("Instrument:")
        self.instrument_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.instrument_drop = QComboBox()
        self.instrument_drop.addItems(["----------"])
        self.instrument_drop.currentIndexChanged.connect(
            lambda: self.set_instrument(self.instrument_drop.currentText())
        )

        self.parameter_label = QLabel("Parameter:")
        self.parameter_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.parameter_drop = QComboBox()
        self.parameter_drop.addItems(["----------"])
        self.parameter_drop.currentIndexChanged.connect(
            lambda: self.set_parameter(self.parameter_drop.currentText())
        )

        self.values_select_frame = QGridLayout()
        self.use_GP = QRadioButton("GP")
        self.use_list = QRadioButton("List")
        self.use_space = QRadioButton("Spacing")
        self.use_file = QRadioButton("File")
        self.use_space.setChecked(True)

        self.n_queries_label = QLabel("GP Queries:")
        self.n_queries_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.n_queries_edit = QLineEdit()
        self.n_queries_edit.setText("20")

        self.values_label = QLabel("Values:")
        self.values_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.values_edit = QLineEdit()
        self.values_edit.textChanged.connect(
            lambda: self.set_values(self.values_edit.text())
        )
        self.values_edit.setText(self.values)

        self.spacing_start_label = QLabel("Start:")
        self.spacing_start_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.spacing_start_edit = QLineEdit()

        self.spacing_end_label = QLabel("End:")
        self.spacing_end_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.spacing_end_edit = QLineEdit()

        self.step_size_label = QLabel("Step:")
        self.step_size_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.step_size_edit = QLineEdit()

        # self.spacing_log_check = QCheckBox("Log Spacing")

        self.values_file_label = QLabel("File:")
        self.values_file_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.values_file_edit = QLineEdit()

        self.values_file_select_button = QPushButton("Browse")
        self.values_file_select_button.clicked.connect(
            self.browse_values_files)

        self.values_select_box = QGroupBox()
        self.values_select_box.setStyleSheet("QGroupBox{padding-top:3px}")
        if self.GPRegressor:
            self.values_select_frame.addWidget(self.use_GP, 0, 0, 1, 1)
            self.values_select_frame.addWidget(
                self.n_queries_label, 0, 1, 1, 1)
            self.values_select_frame.addWidget(self.n_queries_edit, 0, 2, 1, 1)
        self.values_select_frame.addWidget(self.use_list, 1, 0, 1, 1)
        self.values_select_frame.addWidget(self.values_label, 1, 1, 1, 1)
        self.values_select_frame.addWidget(self.values_edit, 1, 2, 1, 6)

        self.values_select_frame.addWidget(self.use_space, 2, 0, 1, 1)
        self.values_select_frame.addWidget(
            self.spacing_start_label, 2, 1, 1, 1)
        self.values_select_frame.addWidget(self.spacing_start_edit, 2, 2, 1, 1)
        self.values_select_frame.addWidget(self.spacing_end_label, 2, 3, 1, 1)
        self.values_select_frame.addWidget(self.spacing_end_edit, 2, 4, 1, 1)
        self.values_select_frame.addWidget(self.step_size_label, 2, 5, 1, 1)
        self.values_select_frame.addWidget(self.step_size_edit, 2, 6, 1, 1)
        # self.values_select_frame.addWidget(self.spacing_log_check, 2, 6, 1, 2)

        self.values_select_frame.addWidget(self.use_file, 3, 0, 1, 1)
        self.values_select_frame.addWidget(self.values_file_label, 3, 1, 1, 1)
        self.values_select_frame.addWidget(self.values_file_edit, 3, 2, 1, 2)
        self.values_select_frame.addWidget(
            self.values_file_select_button, 3, 6, 1, 2)

        self.values_select_box.setLayout(self.values_select_frame)

        self.scan_opt_box = QGroupBox()
        self.scan_opt_box.setStyleSheet("QGroupBox{padding-top:3px}")
        self.scan_opt_frame = QGridLayout()

        self.macro_label = QLabel("Scan Action:")
        self.macro_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.action_drop = QComboBox()
        self.action_drop.addItems(self.actions.keys())
        self.action_drop.currentIndexChanged.connect(
            lambda: self.action_changed(self.action_drop.currentText())
        )

        self.pause_label_before = QLabel("Pause before (sec):")
        self.pause_label_after = QLabel("Pause after (sec):")
        self.pause_timer_label_before = QLabel("0.0")
        self.pause_timer_label_after = QLabel("0.0")
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

        self.upper_grid.addWidget(self.values_select_box, 2, 0, 1, 4)

        self.upper_grid.addWidget(self.scan_opt_box, 3, 0, 1, 4)

        self.scan_button = QPushButton()
        self.scan_button.setText("New Scan")
        self.scan_button.setIcon(QIcon(load_icon("scan.png")))
        self.scan_button.setCheckable(False)
        self.scan_button.clicked.connect(self.new_scan)
        self.scan_button.setSizePolicy(
            QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        )
        self.continue_scan_button = QPushButton()
        self.continue_scan_button.setText("Continue Scan")
        self.continue_scan_button.setCheckable(False)
        self.continue_scan_button.clicked.connect(self.continue_scan)
        self.continue_scan_button.setSizePolicy(
            QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        )
        self.continue_scan_button.setEnabled(False)
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
        self.progress_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.progress_bar = QProgressBar()

        self.progress_grid.addWidget(self.progress_label, 0, 0)
        self.progress_grid.addWidget(self.progress_bar, 0, 1)

        self.scan_button_grid = QGridLayout()
        self.scan_button_grid.addWidget(self.scan_button, 0, 0)
        self.scan_button_grid.addWidget(self.continue_scan_button, 0, 1)

        self.scan_button_grid.addWidget(
            self.stop_button, 0, 2, alignment=QtCore.Qt.AlignRight
        )
        self.progress_bar.setValue(float(self.scan_progress))

        # ******* DEFINE OVERALL LAYOUT
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.upper_grid, 0, 0, 1, 2)
        self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 2)
        self.master_layout.addLayout(self.scan_button_grid, 3, 0, 1, 2)

        self.setLayout(self.master_layout)

        # might need to call this manually again in the main app, if instruments get defined
        # after the scan widget
        self.update_instruments()

        # Create timer to do scan
        self.scan_timer = QTimer(self)

    def browse_values_files(self) -> None:
        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getOpenFileName()
        filename = name_tuple[0]
        if not filename:  # If cancel bttonw as hit, name will be null
            return

        self.values_file_edit.setText(filename)

    def set_instrument(self, inst: str) -> None:
        """Update the list of parameterts that can be scanned."""
        self.parameter_drop.clear()
        params = []

        self.scan_instrument = self.app.get_instrument_by_name(inst)

        if self.scan_instrument:
            params = list(x.name for x in self.scan_instrument.control_UIs)
            logger.debug(f"Added {len(params)} items to parameter dropdown.")
        else:
            logger.error(f"Couldn't find instrument '{inst}'")

        self.parameter_drop.addItems(params)
        self.scan_progress = 0
        self.progress_bar.setValue(self.scan_progress)

    def set_parameter(self, parameter: str) -> None:
        if self.scan_instrument is None:
            return
        for ui in self.scan_instrument.control_UIs:
            if ui.name == parameter:
                self.scan_parameter = ui.setting

    def set_values(self, values: str) -> None:
        self.values = values

    def action_changed(self, action: str) -> None:
        self.scan_action = self.actions[action]

    def compute_values(self):
        """ Reads the values of the widgets and computes the values for the scan
        to iterate over. """

        if self.use_list.isChecked():
            if self.continue_scan:
                self.val_list += self.values_edit.text().split(",")
            else:
                self.val_list = self.values_edit.text().split(",")
        elif self.use_space.isChecked():
            try:
                start = float(self.spacing_start_edit.text())
                end = float(self.spacing_end_edit.text())
                step_size = float(self.step_size_edit.text())
            except:
                logger.error("Invalid values for start, end, or step_size")
                return False
            if self.continue_scan:
                self.val_list += [
                    str(v) for v in np.arange(start, end + step_size, step_size)
                ]            
            else:
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
            if self.continue_scan:
                self.val_list += file_str.split(",")
            else:
                self.val_list = file_str.split(",")

        elif self.use_GP.isChecked():
            if self.n_queries_edit.text() == "":
                self.n_queries_edit.setText("20")
            self.n_queries = float(self.n_queries_edit.text())

            if self.continue_scan:
                self.number_of_values += self.n_queries
                self.val_list = np.append(
                    self.val_list, np.zeros(int(self.n_queries)))
            else:
                self.number_of_values = self.n_queries + self.GPRegressor.pre_scan_num
                self.val_list = np.append(
                    self.first_pre_scans, np.zeros(int(self.n_queries)))

            return True
        else:
            logger.error("No mode selected in scan tool")
            return False

        self.number_of_values = len(self.val_list)
        return True

    def set_instrument_setting(self):
        if self.use_GP.isChecked():
            # For when the count is past the initial scan, get the measured value from the GP widget
            if self.count < self.GPRegressor.pre_scan_num and self.count > 0 and not self.continue_scan:
                self.measure_value()
                self.GPRegressor.regressor.teach(self.val_list[self.count-1].reshape(
                    1, -1), self.app.main_window.tab7.faraday_voltage_list[self.count-1].reshape(1, -1))
                self.GPRegressor.plotGP()
                self.app.main_window.tab7.plotScan()
            # For once the count is past the pre scans or if it is a continued scan
            # Get the measured value, and set the next value to scan
            if self.count >= self.GPRegressor.pre_scan_num or self.continue_scan:
                self.measure_value()
                self.GPRegressor.regressor.teach(self.val_list[self.count-1].reshape(
                    1, -1), self.app.main_window.tab7.faraday_voltage_list[self.count-1].reshape(1, -1))
                query_idx, query_instance = self.GPRegressor.regressor.query(
                    self.val_list.reshape(-1, 1))
                self.val_list[self.count] = query_instance  # next to measure
                self.GPRegressor.plotGP()
                self.app.main_window.tab7.plotScan()
        else:  # if not GP
            if self.count > 0:
                self.measure_value()
                self.app.main_window.tab7.plotScan()

        v = self.val_list[self.count]
        if type(v) == str:
            v = v.strip()
        self.scan_instrument.remote_update_setting(self.scan_parameter, str(v))

    def pause_before_after(self):
        start_time = time.time()
        if self.pause_before:
            dt = float(self.pause_edit_before.text())
        else:
            dt = float(self.pause_edit_after.text())
        end_time = start_time + dt

        def pause():
            time_left = end_time - time.time()
            if time_left > 0:
                if self.pause_before:
                    self.pause_timer_label_before.setText(f"{time_left:.1f}")
                else:
                    self.pause_timer_label_after.setText(f"{time_left:.1f}")
            else:
                if self.pause_before:
                    self.pause_timer_label_before.setText("0.0")
                else:
                    self.pause_timer_label_after.setText("0.0")
                self.scan_timer.stop()
                if self.pause_before:
                    self.scan()
                else:
                    self.start_cycle()

        try:
            self.scan_timer.timeout.disconnect()
        except TypeError:
            pass
        self.scan_timer.timeout.connect(pause)
        self.scan_timer.start(100)

    def start_cycle(self):
        self.count += 1
        self.scan_progress = str(self.count / self.number_of_values * 100)
        self.progress_bar.setValue(float(self.scan_progress))
        QApplication.processEvents()
        if self.count == self.number_of_values:
            logger.debug("Finished scan")
            self.stop_scan()
        else:
            self.set_instrument_setting()
            self.pause_before = True
            self.pause_before_after()

    def stop_scan(self):
        self.scan_timer.stop()
        self.pause_timer_label_before.setText("0.0")
        self.pause_timer_label_after.setText("0.0")
        self.scan_button.setEnabled(True)
        self.continue_scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(float(self.scan_progress))

    def start_scan(self):
        if self.scan_instrument is None:
            logger.error(
                f"Failed to find instrument {self.instrument_drop.currentText()}"
            )
            return
        if not self.compute_values():
            return
        i = self.instrument_drop.currentText()
        p = self.parameter_drop.currentText()
        m = self.action_drop.currentText()
        logger.debug(
            f"Starting scan\n\tInstrument: {i}\n\tParameter: {p}\n\tValues:{self.val_list}"
        )
        self.scan_button.setEnabled(False)
        self.continue_scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.set_instrument_setting()
        self.pause_before = True
        self.pause_before_after()

    def new_scan(self):
        self.count = 0
        if self.use_GP.isChecked():
            self.GPRegressor.initialize_GPR()
            bias_range = self.GPRegressor.end_bias - self.GPRegressor.start_bias
            self.first_pre_scans = np.linspace(self.GPRegressor.start_bias + 0.1*bias_range,
                                               self.GPRegressor.end_bias - 0.1*bias_range, self.GPRegressor.pre_scan_num)
        self.new_scan_time = ""
        self.continue_scan = False
        self.start_scan()

    def continue_scan(self):
        self.continue_scan = True
        self.start_scan()

    def scan(self):
        m = self.action_drop.currentText()
        func = self.actions.get(m, None)
        if func is not None:
            logger.debug(f"\t\tRunning scan function {m}")
            func()
        self.first_run = False
        self.pause_before = False
        self.pause_before_after()

    def update_instruments(self):
        self.instrument_drop.clear()
        names = []
        for inst in self.app.instruments:
            if inst.ignore_control:
                continue
            if not inst.control_UIs:
                continue
            names.append(inst.name)
        self.instrument_drop.addItems(names)
