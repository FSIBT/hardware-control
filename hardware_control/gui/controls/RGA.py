"""
    .. image:: /images/controls/RGA.png

"""
import logging

from PyQt5.QtGui import QIcon, QIntValidator

from PyQt5.QtWidgets import (
    QGroupBox,
    QGridLayout,
    QPushButton,
)

from ..widgets import (
    load_icon,
    HCLineEdit,
    HCComboBox,
    HCSpinBox,
    ScanWidget,
)

logger = logging.getLogger(__name__)


class RGA(QGroupBox):
    """A control program for residual gas analyzers (RGAs).

    This implements all front panel functions of a SRS CIS200 and
    also has some elements that are probably unique to this
    instrument.

    See Also
    --------
    hardware_control.instruments.srs.CIS200
    """

    def __init__(
        self,
        app,
        instrument_name: str,
    ):

        super().__init__(instrument_name)

        self.app = app
        self.instrument = instrument_name

        # Create GUI
        ## Ionizer Settings

        self.filament_emission = HCComboBox(
            self.app,
            self.instrument,
            parameter="FILAMENT_EMISSION",
            label="Filament Current",
            label_align="right",
            items=["0.5", "0.1", "0.05"],
        )

        self.extraction_voltage = HCComboBox(
            self.app,
            self.instrument,
            parameter="EXTRACT_VOLTAGE",
            label="Extraction Voltage",
            label_align="right",
            items=["40", "50"],
        )

        self.electron_energy = HCComboBox(
            self.app,
            self.instrument,
            parameter="ELECTRON_ENERGY",
            label="Electron Energy",
            label_align="right",
            items=["70", "105"],
        )

        self.ion_energy = HCComboBox(
            self.app,
            self.instrument,
            parameter="ION_ENERGY",
            label="Ion Energy",
            label_align="right",
            items=["8eV", "4eV"],
        )

        # Scan Settings
        ## set the bias for CEM
        self.bias = HCSpinBox(
            self.app,
            self.instrument,
            "EM_VOLTAGE",
            label="CEM Bias",
            label_align="right",
        )
        self.bias.setSingleStep(10)
        self.bias.setMinimum(0)
        self.bias.setMaximum(2490)

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.filament_emission.label, 0, 0)
        self.master_layout.addWidget(self.filament_emission, 0, 1)
        self.master_layout.addWidget(self.extraction_voltage.label, 0, 2)
        self.master_layout.addWidget(self.extraction_voltage, 0, 3)

        self.master_layout.addWidget(self.ion_energy.label, 1, 0)
        self.master_layout.addWidget(self.ion_energy, 1, 1)
        self.master_layout.addWidget(self.electron_energy.label, 1, 2)
        self.master_layout.addWidget(self.electron_energy, 1, 3)

        self.master_layout.addWidget(self.bias.label, 3, 0)
        self.master_layout.addWidget(self.bias, 3, 1)

        self.setLayout(self.master_layout)

        self.config_update_readout()

    def config_update_readout(self):
        """Query the instrument for current readout data."""

        for parameter in [
            "FILAMENT_EMISSION",
            "EXTRACT_VOLTAGE",
            "ELECTRON_ENERGY",
            "ION_ENERGY",
            "INITIAL_MASS",
            "FINAL_MASS",
            "EM_VOLTAGE",
            "",
        ]:
            self.app.add_auto_update_instrument_parameter(self.instrument, parameter)


class ScanProcessControlWidget(ScanWidget):
    def __init__(self, app, actions):

        super().__init__(app, "RGA scan", actions)
        self.app = app
        self.actions = actions

        self.RGA_scan_box = QGroupBox()
        self.RGA_scan_layout = QGridLayout()

        ## set the intial scan mass
        self.MI = HCLineEdit(
            self.app,
            self.instrument,
            "INITIAL_MASS",
            label="Intial Mass",
            label_align="right",
        )

        ## set the intial scan mass
        self.MF = HCLineEdit(
            self.app,
            self.instrument,
            "FINAL_MASS",
            label="Final Mass",
            label_align="right",
        )

        ## set the scan steps
        self.SA = HCLineEdit(
            self.app,
            self.instrument,
            "SCAN_STEPS",
            label="steps/amu",
            label_align="right",
        )

        ## set the single scan mass
        self.SM = HCLineEdit(
            self.app,
            self.instrument,
            label="Single Mass:",
            label_align="right",
        )

        ## repeat how many times for one triggers
        self.SM_times = HCLineEdit(
            self.app,
            self.instrument,
            label="Single scan points",
            label_align="right",
        )

        ## set the scan rate
        self.Scan_rate = HCLineEdit(
            self.app,
            self.instrument,
            "SCAN_RATE",
            label="Scan Rate",
            label_align="right",
        )

        ## repeat how many times for one triggers
        self.Scan_times = HCLineEdit(
            self.app,
            self.instrument,
            label="Num. of Scans",
            label_align="right",
        )

        ## add the widgets into the scan_layout
        self.RGA_scan_layout.addWidget(self.MI.label, 0, 0)
        self.RGA_scan_layout.addWidget(self.MI, 0, 1)
        self.RGA_scan_layout.addWidget(self.MF.label, 0, 2)
        self.RGA_scan_layout.addWidget(self.MF, 0, 3)
        self.RGA_scan_layout.addWidget(self.SA.label, 0, 4)
        self.RGA_scan_layout.addWidget(self.SA, 0, 5)
        self.RGA_scan_layout.addWidget(self.SM.label, 1, 0)
        self.RGA_scan_layout.addWidget(self.SM, 1, 1)
        self.RGA_scan_layout.addWidget(self.SM_times.label, 2, 2)
        self.RGA_scan_layout.addWidget(self.SM_times, 2, 3)
        self.RGA_scan_layout.addWidget(self.Scan_rate.label, 2, 0)
        self.RGA_scan_layout.addWidget(self.Scan_rate, 2, 1)
        self.RGA_scan_layout.addWidget(self.Scan_times.label, 2, 0)
        self.RGA_scan_layout.addWidget(self.Scan_times, 2, 1)

        self.scan_opt_frame = QGridLayout()
        self.scan_opt_box = QGroupBox()
        self.pause_before = HCLineEdit(
            label="Pause Before",
            label_align="right",
        )
        self.pause_before.setText("10")
        self.pause_before.setValidator(QIntValidator())

        self.pause_after = HCLineEdit(
            label="Pause After",
            label_align="right",
        )
        self.pause_after.setText("10")
        self.pause_after.setValidator(QIntValidator())

        self.scans_drop = HCComboBox(
            self.app,
            self.instrument,
            label="Scans",
            label_align="right",
            items=["Analog", "Single Mass"],
        )

        self.scan_button = QPushButton()
        self.scan_button.setIcon(QIcon(load_icon("scan.png")))
        self.scan_button.setCheckable(False)
        self.scan_button.clicked.connect(self.scan)
        # self.scan_button.setSizePolicy(
        #     QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        # )

        self.scan_opt_frame.addWidget(self.pause_before.label, 0, 0)
        self.scan_opt_frame.addWidget(self.pause_after.label, 1, 0)
        self.scan_opt_frame.addWidget(self.pause_before, 0, 1)
        self.scan_opt_frame.addWidget(self.pause_after, 1, 1)
        self.scan_opt_frame.addWidget(self.scans_drop.label, 2, 0)
        self.scan_opt_frame.addWidget(self.scans_drop, 2, 1)
        self.scan_opt_frame.addWidget(self.scan_button, 2, 2)

        ## add two parts of scan into the main_layout
        self.main_layout = QGridLayout()
        self.RGA_scan_box.setLayout(self.RGA_scan_layout)
        self.main_layout.addWidget(self.RGA_scan_box, 0, 0)
        self.scan_opt_box.setLayout(self.scan_opt_frame)
        self.main_layout.addWidget(self.scan_opt_frame, 1, 0)

    def scan(self):
        scan_action = self.scans_drop.currentText()
        func = self.actions.get(scan_action, None)
        if func is not None:
            logger.info(f"\t\tRunning scan function {scan_action}")
            func()
        self.first_run = False
        self.pause_before = False
        self.pause_before_after()
