"""
    .. image:: /images/widgets/scan_widget.png
      :height: 400
"""

import logging
import time
from typing import Callable, Optional, Dict

import warnings

with warnings.catch_warnings():
    # ignore warning in GPy
    # bug report https://github.com/SheffieldML/GPy/issues/950
    warnings.simplefilter("ignore", ResourceWarning)
    from GPy.kern import Matern32, Bias
    from GPy.models import GPRegression
    from GPy.core.parameterization.priors import Gamma

from scipy.stats import rv_discrete

import numpy as np

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtWidgets import (
    QApplication,
    QGroupBox,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QRadioButton,
    QFileDialog,
    QSizePolicy,
)

from .hc_widgets import load_pixmap

logger = logging.getLogger(__name__)


class regressor:
    """Object that contains the Gaussian process capability of the scan widget."""

    def __init__(self, x_prescans, y_prescans, stepsize):
        # Intialize GP regressor object with the prescan measurements
        self.x_measured = x_prescans
        self.y_measured = np.array(y_prescans)
        num_points = int((np.max(self.x_measured) - np.min(self.x_measured)) / stepsize)
        num_points += 1
        self.x_potential = np.linspace(
            np.min(self.x_measured), np.max(self.x_measured), num_points
        )
        # Compute a window (called "delta") for neighbor probabilities calculation
        self.delta = (np.max(self.x_measured) - np.min(self.x_measured)) / len(
            self.x_measured
        )

        # Average of lower 10% of data is baseline of Bias kernel
        if len(set(self.y_measured)) != 1:
            self.mean_training_baseline = np.mean(
                self.y_measured[self.y_measured < np.percentile(self.y_measured, 10)]
            )
        # If all measured y values are the same value, use that value for the baseline
        else:
            self.mean_training_baseline = self.y_measured[0]

        # The kernel
        kernel = Matern32(1) + Bias(1, variance=self.mean_training_baseline)
        kernel.Mat32.variance.set_prior(
            Gamma.from_EV(np.max(self.y_measured), 1000.0), warning=False
        )
        kernel.Mat32.lengthscale.set_prior(Gamma.from_EV(100.0, 100.0), warning=False)

        # The model
        model = GPRegression(
            np.asarray(self.x_measured).reshape(-1, 1),
            np.asarray(self.y_measured).reshape(-1, 1),
            kernel,
        )

        # Force model prediction must go through all points
        model.Gaussian_noise.fix(0.0)
        model.optimize()
        self.model = model
        self.ypred = None
        self.std = None

    def neighbor_probability(self, potential_vals, found_vals, delta):
        """For each element in potential_vals, return a value proportional to the number of nearby points in found_vals.

        Delta is the window that determines what is considered "nearby"."""
        found_vals = found_vals.flatten()  # points already measured
        potential_vals = potential_vals.flatten()  # points that could be measured

        # Create an array of "neighborhoods" around each point that could be measured
        neighbor_lo = potential_vals - delta
        neighbor_hi = potential_vals + delta
        neighborhoods = np.array((neighbor_lo, neighbor_hi)).T
        prob = np.zeros(neighborhoods.shape[0])

        # Sum up the number of points already measured in each neighborhood
        for idx, neighborhood in enumerate(neighborhoods):
            new_prob = (
                (found_vals > neighborhood[0]) & (found_vals < neighborhood[1])
            ).sum()
            prob[idx] = new_prob

        # Sometimes all the points have no "neighbors". In this case, return a probability array of zeros.
        # Otherwise normalize the probability distribution
        if np.count_nonzero(prob) != 0:
            prob /= prob.sum()

            return prob

    def next_query_val(self):
        """Select the best point to measure next in a parameter scan."""
        # Get the predicted y values and standard deviations according to the current model
        ypred, std = self.model.predict((self.x_potential).reshape(-1, 1))
        # Form a normalized probability distribution out of the standard deviations
        pk = std
        pk = np.where(pk < 0, 0, pk)
        pk /= pk.sum()

        # Artificially deflate probability of choosing a point to measure that has many trained points next to it
        neigh_prob = self.neighbor_probability(
            self.x_potential,
            self.x_measured,
            self.delta,
        ).reshape(-1, 1)
        neigh_prob *= 0.3
        pk -= neigh_prob

        # (By a factor of 2) artificially inflate probability of choosing the higher points in the spectrum
        pk += ypred / ypred.sum()

        # In case 1) all probabilities are zero or 2) a NaN appears in pk, set all the probabilities to the same value
        if np.count_nonzero(pk) == 0 or np.isnan(pk).any():
            pk = np.ones(pk.shape)
            pk /= pk.sum()

        # Set probability of picking a point that is already in the training set to zero
        idx_to_zero = np.isin(self.x_potential, self.x_measured)
        pk[idx_to_zero] = 0

        # Normalize probability distribution...again
        pk = np.where(pk < 0, 0, pk)
        pk /= pk.sum()

        # Select x value for next query using the probability distribution
        # (rv_discrete only takes integers, so we scale all values up by 100
        # before using rv_discrete and then scale back down afterwards; for this
        # reason, the stepsize of x_potential cannot be less than 0.01, for under
        # those conditions there would still be some values that would not be
        # whole numbers)
        S = rv_discrete(
            values=[(1e2 * self.x_potential).astype(int).reshape(-1, 1), pk]
        )
        x_query = float(S.rvs()) / 1e2
        self.x_measured = np.append(self.x_measured, x_query).reshape(-1, 1)

    def update_model(self, new_y_val):
        """Update the Gaussian process kernel with newly measured data."""
        self.y_measured = np.append(self.y_measured, new_y_val).reshape(-1, 1)

        # Update training sets
        self.model.set_XY(X=self.x_measured, Y=self.y_measured)
        self.model.optimize()

        # When measuring a new maximum, clear the kernel parameters and restart optimization.
        # Hopefully, this prevents the kernel from freaking out over the fact that the most recent point
        # is so different from the others
        if (self.y_measured[-1] == np.max(self.y_measured)) & (
            len(self.y_measured) >= 5
        ):  # For some reason, GPy doesn't like to do restarts if there are very few points
            self.model.optimize_restarts(num_restarts=20, verbose=False)

        # Most recent Y-prediction and standard deviations
        ypred, std = self.model.predict(self.x_potential.reshape(-1, 1))
        self.ypred = ypred
        self.std = std

        # Update kernel
        # Matern kernel variance prior is centered around the max y value
        self.model.kern.Mat32.variance.set_prior(
            Gamma.from_EV(np.max(self.y_measured), 1000.0), warning=False
        )
        # Average of lower 10% of data is baseline of Bias kernel
        if len(set(self.y_measured.flatten())) != 1:
            self.mean_training_baseline = np.mean(
                self.y_measured[self.y_measured < np.percentile(self.y_measured, 10)]
            )
        # If all measured y values are the same value, use that value for the baseline
        else:
            self.mean_training_baseline = self.y_measured[0]
        self.model.kern.bias.variance = self.mean_training_baseline


class ScanWidget(QGroupBox):
    """
    Widget that scans a number of instrument parameter values and makes a measurement at each one.

    Parameters
    ----------
    app
        The main app
    name
        The scan widget name that appears in the user interface
    actions
        A dictionary in which the values are functions to be called at each measured value
    scan_parameters
        The parameters that one can scan; if no parameters are specified, then all parameters
        in the instrument will be considered scan parameters
    GP_option
        Option to use a Gaussian process scan or not
    get_measured_values_fxn
        Function that makes and returns a measurement at each parameter value
    scan_cycle_fxn
        Optional function that will be executed after each measurement
        (i.e. once per measurement cycle)
    finish_scan_fxn
        Optional function that will be executed at the conclusion of the scan


    :Scan Range GUI Parameters: * **Start** - Value at which the scan starts
                                * **Stop** - Value at which the scan ends
                                * **Step** - The step size between the values measured in the scan


    :Gaussian Process GUI Parameters: * **Start** - Value at which the Gaussian process pre-scan starts; this is also the minimum value that the Gaussian process will ever measure
                                      * **Stop** - Value at which the Gaussian process pre-scan ends; this is also the maximum value that the Gaussian process will ever measure
                                      * **Step** - The minimum spacing between adjacent measured values; this value cannot be less than 0.01
                                      * **# of Pre-Scans** - Number of values to pre-scan; Gaussian processes always begin with a prescan over an evenly-spaced array starting and ending with the start and stop values, respectively
                                      * **# of Queries** – Number of values to query during the Gaussian process (after the pre-scan) is finished
    """

    def __init__(
        self,
        app,
        name: str,
        actions: Dict,
        scan_parameters: Optional[Dict] = None,
        GP_option: bool = False,
        get_measured_values_fxn: Callable = None,
        scan_cycle_fxn: Optional[Callable] = None,
        finish_scan_fxn: Optional[Callable] = None,
    ):
        super().__init__(name)

        self.app = app

        self.actions = actions
        self.scan_parameters = scan_parameters
        self.get_measured_values = get_measured_values_fxn
        self.scan_cycle_fxn = scan_cycle_fxn
        self.finish_scan = finish_scan_fxn

        self.scan_instrument = None
        self.scan_parameter = None
        self.scan_action = None
        self.scan_progress = 0
        self.scan_finished = False

        self.values = ""
        self.val_list = []
        self.count = 0
        self.number_of_values = 0
        self.GP_option = GP_option
        self.GP_offset = 0.0

        # Create scan widget UI elements
        # UI 1: Indicates instrument and parameter
        self.instrument_label = QLabel("Instrument:")
        self.instrument_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.instrument_drop = QComboBox()
        self.instrument_drop.addItems(["----------"])
        self.instrument_drop.currentIndexChanged.connect(self.set_instrument)

        self.arrow_symbol = QLabel()
        self.arrow_symbol.setPixmap(load_pixmap("arrow.png"))
        self.arrow_symbol.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        self.parameter_label = QLabel("Parameter:")
        self.parameter_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.parameter_drop = QComboBox()
        self.parameter_drop.addItems(["----------"])
        self.parameter_drop.currentIndexChanged.connect(self.set_parameter)

        # UI 2: Indicates scan type – Gaussian process (GP), list of values, a range of values, or values list from a file
        self.use_GP = QRadioButton("GP")
        self.use_list = QRadioButton("List")
        self.use_range = QRadioButton("Range")
        self.use_file = QRadioButton("File")
        # Default scan type is a range of values scan
        self.use_range.setChecked(True)

        # Option 1: GP scan starting info
        self.GP_start_label = QLabel("Start:")
        self.GP_start_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.GP_start_edit = QLineEdit()

        self.GP_end_label = QLabel("End:")
        self.GP_end_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.GP_end_edit = QLineEdit()

        self.GP_step_label = QLabel("Step:")
        self.GP_step_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.GP_step_edit = QLineEdit()

        self.GP_n_queries_label = QLabel("# of Queries:")
        self.GP_n_queries_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.GP_n_queries_edit = QLineEdit()

        self.GP_n_prescans_label = QLabel("# of Pre-Scans:")
        self.GP_n_prescans_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.GP_n_prescans_edit = QLineEdit()

        # Option 2: Values to start scanning inputted manually into a list
        self.list_label = QLabel("Values:")
        self.list_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.list_edit = QLineEdit()
        self.list_edit.textChanged.connect(self.set_list_values)
        self.list_edit.setText(self.values)

        # Option 3: Range to scan
        self.range_start_label = QLabel("Start:")
        self.range_start_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )

        self.range_start_edit = QLineEdit()

        self.range_end_label = QLabel("End:")
        self.range_end_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.range_end_edit = QLineEdit()

        self.range_step_label = QLabel("Step:")
        self.range_step_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.range_step_edit = QLineEdit()

        # Option 4: Values to scan from file
        self.values_file_label = QLabel("File:")
        self.values_file_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )

        self.values_file_edit = QLineEdit()

        self.values_file_select_button = QPushButton("Browse")
        self.values_file_select_button.clicked.connect(self.browse_values_files)

        self.values_select_box = QGroupBox()
        self.values_select_box.setStyleSheet("QGroupBox{padding-top:3px}")

        # Create a QT grid for the scan types
        self.values_select_frame = QGridLayout()
        self.values_select_frame.addWidget(self.use_range, 0, 0, 1, 1)
        self.values_select_frame.addWidget(self.range_start_label, 0, 1, 1, 1)
        self.values_select_frame.addWidget(self.range_start_edit, 0, 2, 1, 1)
        self.values_select_frame.addWidget(self.range_end_label, 0, 3, 1, 1)
        self.values_select_frame.addWidget(self.range_end_edit, 0, 4, 1, 1)
        self.values_select_frame.addWidget(self.range_step_label, 0, 5, 1, 1)
        self.values_select_frame.addWidget(self.range_step_edit, 0, 6, 1, 1)

        if self.GP_option:
            self.values_select_frame.addWidget(self.use_GP, 1, 0, 1, 1)
            self.values_select_frame.addWidget(self.GP_start_label, 1, 1, 1, 1)
            self.values_select_frame.addWidget(self.GP_start_edit, 1, 2, 1, 1)

            self.values_select_frame.addWidget(self.GP_end_label, 1, 3, 1, 1)
            self.values_select_frame.addWidget(self.GP_end_edit, 1, 4, 1, 1)

            self.values_select_frame.addWidget(self.GP_step_label, 1, 5, 1, 1)
            self.values_select_frame.addWidget(self.GP_step_edit, 1, 6, 1, 1)

            self.values_select_frame.addWidget(self.GP_n_prescans_label, 2, 1, 1, 2)
            self.values_select_frame.addWidget(self.GP_n_prescans_edit, 2, 3, 1, 1)

            self.values_select_frame.addWidget(self.GP_n_queries_label, 2, 4, 1, 2)
            self.values_select_frame.addWidget(self.GP_n_queries_edit, 2, 6, 1, 1)

        self.values_select_frame.addWidget(self.use_list, 3, 0, 1, 1)
        self.values_select_frame.addWidget(self.list_label, 3, 1, 1, 1)
        self.values_select_frame.addWidget(self.list_edit, 3, 2, 1, 5)

        self.values_select_frame.addWidget(self.use_file, 4, 0, 1, 1)
        self.values_select_frame.addWidget(self.values_file_label, 4, 1, 1, 1)
        self.values_select_frame.addWidget(self.values_file_edit, 4, 2, 1, 2)
        self.values_select_frame.addWidget(self.values_file_select_button, 4, 5, 1, 2)

        self.values_select_box.setLayout(self.values_select_frame)

        # UI 3: A QT grid with assorted scanning parameters
        self.macro_label = QLabel("Scan Action:")
        self.macro_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.action_drop = QComboBox()
        self.action_drop.addItems(self.actions.keys())
        self.action_drop.currentIndexChanged.connect(self.action_changed)

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

        self.scan_opt_frame = QGridLayout()
        self.scan_opt_frame.addWidget(self.macro_label, 0, 0)
        self.scan_opt_frame.addWidget(self.action_drop, 0, 1)
        self.scan_opt_frame.addWidget(self.pause_label_before, 1, 0)
        self.scan_opt_frame.addWidget(self.pause_label_after, 2, 0)
        self.scan_opt_frame.addWidget(self.pause_edit_before, 1, 1)
        self.scan_opt_frame.addWidget(self.pause_edit_after, 2, 1)
        self.scan_opt_frame.addWidget(self.pause_timer_label_before, 1, 3)
        self.scan_opt_frame.addWidget(self.pause_timer_label_after, 2, 3)

        self.scan_opt_box = QGroupBox()
        self.scan_opt_box.setStyleSheet("QGroupBox{padding-top:3px}")
        self.scan_opt_box.setLayout(self.scan_opt_frame)

        # Create main QT grid for the three UIs in the scan_widget
        self.main_grid = QGridLayout()
        self.main_grid.addWidget(self.instrument_label, 0, 0, 1, 2)
        self.main_grid.addWidget(self.instrument_drop, 1, 0, 1, 2)
        self.main_grid.addWidget(self.arrow_symbol, 1, 2)
        self.main_grid.addWidget(self.parameter_label, 0, 3)
        self.main_grid.addWidget(self.parameter_drop, 1, 3)
        self.main_grid.addWidget(self.values_select_box, 2, 0, 1, 4)
        self.main_grid.addWidget(self.scan_opt_box, 3, 0, 1, 4)

        # Add scanning buttons and a scan progress bar
        self.scan_button = QPushButton()
        self.scan_button.setText("New Scan")
        self.scan_button.setIcon(QIcon(load_pixmap("scan.png")))
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
        self.stop_button.setIcon(QIcon(load_pixmap("stop.svg")))
        self.stop_button.setCheckable(False)
        self.stop_button.setSizePolicy(
            QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        )
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.button_stop_scan)

        self.scan_button_grid = QGridLayout()
        self.scan_button_grid.addWidget(self.scan_button, 0, 0)
        self.scan_button_grid.addWidget(self.continue_scan_button, 0, 1)
        self.scan_button_grid.addWidget(
            self.stop_button, 0, 2, alignment=QtCore.Qt.AlignRight
        )

        self.progress_grid = QGridLayout()
        self.progress_label = QLabel("Scan Progress")
        self.progress_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.progress_bar = QProgressBar()
        self.progress_grid.addWidget(self.progress_label, 0, 0)
        self.progress_grid.addWidget(self.progress_bar, 0, 1)
        self.progress_bar.setValue(float(self.scan_progress))

        # Define overall layout of the scan_widget
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.main_grid, 0, 0, 1, 2)
        self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 2)
        self.master_layout.addLayout(self.scan_button_grid, 3, 0, 1, 2)
        self.setLayout(self.master_layout)

        # Might need to call this again in the main app if instruments get defined after the scan widget
        self.update_scan_parameters()

        # Create timer to do scan
        self.scan_timer = QTimer(self)

    def browse_values_files(self) -> None:
        """Browse files to use for scanning range."""
        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getOpenFileName()
        filename = name_tuple[0]
        # If cancel button  was hit, name will be null
        if not filename:
            return

        self.values_file_edit.setText(filename)

    def set_instrument(self) -> None:
        """When an instrumnet is selected, update the list of parameterts that can be scanned."""
        if self.instrument_drop.currentText() == "":
            logger.warning("Scan Instrument dropdown is empty.")
            return
        else:
            self.scan_instrument = self.instrument_drop.currentText()

        self.parameter_drop.clear()
        # If a list of scan_parameters is provided for each instrument,
        # add those parameters to the parameter dropdown
        if self.scan_parameters is not None:
            self.parameter_drop.addItems(self.scan_parameters[self.scan_instrument])
        # If list of scan parameters is not provided, add all the
        # scan instrument's parameters to the parameter dropdown
        else:
            parameters = self.app.list_instrument_parameters(
                self.instrument_drop.currentText()
            )
            self.parameter_drop.addItems(parameters)

        # Set the scan bar progress to 0%
        self.scan_progress = 0
        self.progress_bar.setValue(self.scan_progress)

    def set_parameter(self) -> None:
        """When a parameter is selected, designate it as the scan parameter."""
        self.scan_parameter = self.parameter_drop.currentText()

    def set_list_values(self) -> None:
        """Set scan values to the values in the list field."""
        self.values = self.list_edit.text()

    def action_changed(self) -> None:
        """Change the action done at each scanned value."""
        self.scan_action = self.actions[self.action_drop.currentText()]

    def new_scan(self):
        "Set all parameters to initital scanning state and call start_scan."
        self.count = 0
        self.new_scan_time = ""
        self.continue_scan = False
        self.start_scan()

    def start_scan(self):
        "Enable stop scan button and call scanning function."
        if self.scan_instrument is None:
            logger.error(
                f"Failed to find instrument {self.instrument_drop.currentText()}"
            )
            return
        if not self.compute_values():
            return
        instrument = self.instrument_drop.currentText()
        parameter = self.parameter_drop.currentText()
        logger.info(
            f"Starting scan\n\tInstrument: {instrument}\n\tParameter: {parameter}\n\tValues:{self.val_list}"
        )
        self.scan_button.setEnabled(False)
        self.continue_scan_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.pause_before = True
        self.pause_before_after()

    def compute_values(self):
        """Compute the values for the scan to iterate over."""
        if self.use_list.isChecked():
            new_val_list = [float(x) for x in self.list_edit.text().split(",")]
            if self.continue_scan:
                self.val_list += new_val_list
            else:
                self.val_list = new_val_list
        elif self.use_range.isChecked():
            try:
                start = float(self.range_start_edit.text())
                end = float(self.range_end_edit.text())
                step_size = float(self.range_step_edit.text())
            except:
                logger.error(
                    "Scan Widget: Invalid values for Range Scan start, end, or step."
                )
                return False
            if self.continue_scan:
                self.val_list += [
                    float(v) for v in np.arange(start, end + step_size, step_size)
                ]
            else:
                self.val_list = [
                    float(v) for v in np.arange(start, end + step_size, step_size)
                ]
        elif self.use_file.isChecked():
            filename = self.values_file_edit.text()
            if filename == "":
                logger.error("Scan Widget: No filename provided for values file")
                return False
            # Read files
            with open(filename) as file:
                file_str = file.read().replace("\n", "")
            new_val_list = [float(x) for x in file_str.split(",")]
            if self.continue_scan:
                self.val_list += new_val_list
            else:
                self.val_list = new_val_list

        elif self.use_GP.isChecked():
            # If GP values are not inputted, get them from scan values
            if self.GP_start_edit.text() == "":
                self.GP_start_edit.setText(self.range_start_edit.text())
            if self.GP_end_edit.text() == "":
                self.GP_end_edit.setText(self.range_end_edit.text())
            if self.GP_step_edit.text() == "":
                self.GP_step_edit.setText(self.range_step_edit.text())

            if float(self.GP_step_edit.text()) < 0.01:
                logger.error(
                    "ValueError: Gaussian process stepsize must be greater than 0.01."
                )
                return False
            try:
                start = float(self.GP_step_edit.text())
                end = float(self.GP_step_edit.text())
                step_size = float(self.GP_step_edit.text())
            except:
                logger.error(
                    "Scan Widget: Invalid values for GP Scan start, end, or step."
                )
                return False

            self.GP_n_queries = int(self.GP_n_queries_edit.text())
            self.GP_n_prescans = int(self.GP_n_prescans_edit.text())

            if self.GP_n_prescans < 2:
                logger.error(
                    "ValueError: Gaussian process requires at least 2 prescans."
                )
                return False

            self.prescan_vals = np.linspace(
                int(self.GP_start_edit.text()),
                int(self.GP_end_edit.text()),
                self.GP_n_prescans,
            )

            if np.max(np.diff(self.prescan_vals)) <= float(self.GP_step_edit.text()):
                logger.error(
                    "ValueError: The GP minimum stepsize is larger than the prescan values stepsize."
                )
                return False

            if self.continue_scan:
                self.number_of_values += self.GP_n_queries
                self.val_list = np.append(
                    self.val_list, np.zeros(int(self.GP_n_queries))
                )
            else:
                self.number_of_values = self.GP_n_queries + len(self.prescan_vals)
                self.val_list = np.append(
                    self.prescan_vals, np.zeros(int(self.GP_n_queries))
                )

            return True
        else:
            logger.error("Please select a scanning method: Range, GP, List, or File.")
            return False

        self.number_of_values = len(self.val_list)
        return True

    def pause_before_after(self):
        """Determine whether an upcoming pause is before or after a measurement and call the pause function."""
        self.start_time = time.time()
        if self.pause_before:
            dt = float(self.pause_edit_before.text())
        else:
            dt = float(self.pause_edit_after.text())
        self.end_time = self.start_time + dt

        try:
            self.scan_timer.timeout.disconnect()
        except TypeError:
            pass
        self.scan_timer.timeout.connect(self.pause)
        self.scan_timer.start(100)

    def pause(self):
        """Give instruments time to update by pausing before and after measurement.

        After pausing before, this function calls operate_cycle to start a new cycle."""
        time_left = self.end_time - time.time()
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
                scan_action = self.action_drop.currentText()
                func = self.actions.get(scan_action, None)
                if func is not None:
                    logger.info(f"Running scan function '{scan_action}'")
                    func()
                self.first_run = False
                self.pause_before = False
                self.pause_before_after()
            else:
                self.operate_cycle()

    def operate_cycle(self):
        """Perform all actions that take place at one scan value measurement (i.e. in one cycle).

        These actions include making the desired measurement, updating the Gaussian
        process kernel (if applicable), executing the given scan_cycle_fxn (if given),
        updating the progress bar, moving to the next scan value to measure, and
        pausing when all these actions are completed.
        """
        if self.use_GP.isChecked() is False:
            self.GP_n_prescans = np.inf
        self.measured_yvals = self.get_measured_values()

        if self.count >= self.GP_n_prescans or self.continue_scan:
            self.GP_regressor.update_model(
                self.measured_yvals[self.count],
            )
        self.scan_cycle_fxn()

        # Update progress bar
        self.scan_progress = str((self.count + 1) / self.number_of_values * 100)
        self.progress_bar.setValue(float(self.scan_progress))
        QApplication.processEvents()

        # Move to next scan value
        self.count += 1
        if self.count == self.number_of_values:
            logger.info(
                f"Finished scan\n\tInstrument: {self.scan_instrument}\n\tParameter: {self.scan_parameter}\n\tValues:{self.val_list}."
            )
            self.end_scan()
            return
        if self.count >= self.GP_n_prescans or self.continue_scan:
            # For first GP query, initialize the GP regressor
            if self.count == self.GP_n_prescans and not self.continue_scan:
                logger.info("Finsihed GP Pre-Scan. Starting GP querying.")
                self.GP_regressor = regressor(
                    self.val_list[: self.count],
                    self.measured_yvals[: self.count],
                    float(self.GP_step_edit.text()),
                )

            self.GP_regressor.next_query_val()
            self.val_list[self.count] = self.GP_regressor.x_measured[-1]

        # Update scan instrument with new value
        v = self.val_list[self.count]
        if type(v) == str:
            v = v.strip()
        self.app.set_instrument_parameter(
            self.scan_instrument, self.scan_parameter, str(v)
        )
        # Start the scan
        self.pause_before = True
        self.pause_before_after()

    def continue_scan(self):
        "Continue the previous scan."
        self.continue_scan = True
        self.start_scan()

    def update_scan_parameters(self):
        """Determine which parameter can be scanned over."""
        self.instrument_drop.clear()

        # If a list of scan parameters is provided, add the scanned
        # instruments to the scan instrument dropdown
        if self.scan_parameters is not None:
            self.instrument_drop.addItems(self.scan_parameters.keys())
            return

        # If no scan parameters are provided, add all known instruments
        # to the scan instrument dropdown
        scan_instruments = []
        for instrument in self.app.list_instruments():
            if self.app.get_instrument_parameter(instrument, "IGNORE"):
                continue
            scan_instruments.append(instrument)
        self.instrument_drop.addItems(scan_instruments)

    def end_scan(self):
        """Reset buttons to non-scanning state."""
        self.scan_finished = True
        self.stop_button.click()

    def button_stop_scan(self):
        """Reset the user interface to the state when the app is not scanning."""
        self.scan_timer.stop()
        self.pause_timer_label_before.setText("0.0")
        self.pause_timer_label_after.setText("0.0")
        self.scan_button.setEnabled(True)
        self.continue_scan_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if self.scan_finished is False:
            logger.info("Scan Widget stopped manually by the user.")
        self.progress_bar.setValue(float(self.scan_progress))
        if self.progress_bar.value() > 0.0:
            self.finish_scan()
