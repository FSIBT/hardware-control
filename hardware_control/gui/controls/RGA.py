import logging

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator
from PyQt5.QtWidgets import (
    QGroupBox,
    QComboBox,
    QLabel,
    QGridLayout,
    QWidget,
)

from ..widgets import (
    load_icon,
    HCLineEdit,
    HCComboBox,
    HCDoubleSpinBox,
    HCPushButton,
    HCSpinBox,
)

logger = logging.getLogger(__name__)


class RGA(QGroupBox):
    """A GUI for Residual Gas Analyzer.

    This implements all front panel functions of a SRS CIS200 and has
    also has some elements that are probably unique to this
    instrument.

    .. image:: /images/controls/DelayGenerator.png
      :height: 200

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

        ## set the intial scan mass
        self.MI = HCSpinBox(
            self.app,
            self.instrument,
            "INITIAL_MASS",
            label="Intial Mass",
            label_align="right",
        )
        self.MI.setSingleStep(1)
        self.MI.setMinimum(1)
        self.MI.setMaximum(199)

        ## set the intial scan mass
        self.MF = HCSpinBox(
            self.app,
            self.instrument,
            "FINAL_MASS",
            label="Final Mass",
            label_align="right",
        )
        self.MF.setSingleStep(1)
        self.MF.setMinimum(20)
        self.MF.setMaximum(200)

        ## set the scan rate
        self.scan_rate = HCSpinBox(
            self.app,
            self.instrument,
            "SCAN_RATE",
            label="Scan Rate",
            label_align="right",
        )
        self.scan_rate.setSingleStep(1)
        self.scan_rate.setMinimum(0)
        self.scan_rate.setMaximum(7)

        self.channel_box.setLayout(self.channel_box_layout)

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.filament_emission.label, 0, 0)
        self.master_layout.addWidget(self.filament_emission, 0, 1)
        self.master_layout.addWidget(self.extraction_voltage.label, 0, 2)
        self.master_layout.addWidget(self.extraction_voltage, 0, 3)

        self.master_layout.addWidget(self.ion_energy.label, 1, 0)
        self.master_layout.addWidget(self.ion_energy, 1, 1)
        self.master_layout.addWidget(self.electron_energy.label, 1, 2)
        self.master_layout.addWidget(self.electron_energy, 1, 3)

        self.master_layout.addWidget(self.MI.label, 2, 0)
        self.master_layout.addWidget(self.MI, 2, 1)
        self.master_layout.addWidget(self.MF.label, 2, 2)
        self.master_layout.addWidget(self.MI, 2, 3)

        self.master_layout.addWidget(self.scan_rate.label, 3, 0)
        self.master_layout.addWidget(self.scan_rate, 3, 1)

        self.master_layout.addWidget(self.bias.label, 3, 2)
        self.master_layout.addWidget(self.bias, 3, 2)

        self.setLayout(self.master_layout)

        # Create timer to query instrument
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.app.globalRefreshRate)

    def update_readout(self):
        """Queries the instrument for current readout data."""

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
            self.app.update_instrument_parameter(self.instrument, parameter)
