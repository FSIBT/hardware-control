import logging

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QLineEdit, QLabel, QFormLayout, QGridLayout, QComboBox

from ..base import Instrument

logger = logging.getLogger(__name__)


class FlowController(Instrument):
    """A GUI for a gas flow controller.

    Implements setting the gas flow and the type of gas used. As well
    as reading out the current flow and pressure at the flow meter.

    .. image:: /images/controls/FlowController.png
      :height: 200

    See Also
    --------
    hardware_control.backends.alicat.Alicat_M_Series.Alicat_M_Series

    """

    def __init__(
        self, app, backend, name: str = "Flow Controller", lock_until_sync=False,
    ):
        super().__init__(app, name, backend, lock_until_sync)

        self.settings = self.default_state()

        # *************************Create GUI************************

        # ****** DEFINE TEXT BOXES
        self.rate_edit = QLineEdit()
        self.rate_edit.setValidator(QDoubleValidator())
        self.rate_edit.editingFinished.connect(
            lambda: self.update_setting("RATE", self.rate_edit.text())
        )
        self.rate_edit.setText(str(self.settings["RATE"]))

        self.form = QFormLayout()
        self.form.addRow("Flow rate (sccm):", self.rate_edit)

        self.lower_grid = QGridLayout()

        # ******* DEFINE DROPDOWNS + READOUT
        self.gas_label = QLabel("Gas:")
        self.gas_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.gas_drop = QComboBox()
        self.gas_drop.addItems(["Argon", "Helium", "Hydrogen", "Air"])
        self.gas_drop.currentIndexChanged.connect(
            lambda: self.update_setting("GAS", self.gas_drop.currentText().upper())
        )
        self.gas_drop.setCurrentText(self.settings["GAS"])

        self.pressure_label_fix0 = QLabel("Pressure: ")
        self.pressure_label_fix0.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.pressure_label_readout = QLabel("--")
        self.pressure_label_readout.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.pressure_label_fix1 = QLabel(" Torr")
        self.pressure_label_fix1.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )

        self.flow_label_fix0 = QLabel("Flow: ")
        self.flow_label_fix0.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.flow_label_readout = QLabel("--")
        self.flow_label_readout.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        self.flow_label_fix1 = QLabel(" sccm")
        self.flow_label_fix1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Add widgets to grid layout
        self.lower_grid.addWidget(self.gas_label, 0, 0, 1, 1)
        self.lower_grid.addWidget(self.gas_drop, 0, 1, 1, 2)
        self.lower_grid.addWidget(self.pressure_label_fix0, 1, 0, 1, 1)
        self.lower_grid.addWidget(self.pressure_label_readout, 1, 1, 1, 1)
        self.lower_grid.addWidget(self.pressure_label_fix1, 1, 2, 1, 1)
        self.lower_grid.addWidget(self.flow_label_fix0, 2, 0, 1, 1)
        self.lower_grid.addWidget(self.flow_label_readout, 2, 1, 1, 1)
        self.lower_grid.addWidget(self.flow_label_fix1, 2, 2, 1, 1)

        # ******* DEFINE OVERALL LAYOUT
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.form, 0, 0)
        self.master_layout.addLayout(self.lower_grid, 1, 0)
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

        logger.debug("Initalized")

        self.values["RATE"] = "-"
        self.values["PRESSURE"] = "-"

    def close(self):
        self.readout_timer.stop()
        super().close()

    def update_readout(self):
        """Queries the instrument for current readout data, then reads the most
        recent readout data from the inbox and pushes it to the GUI"""

        # Request updated readout data
        self.command("RATE?")
        self.command("PRESSURE?")

        # Update labels
        self.pressure_label_readout.setText(self.read_values("PRESSURE"))
        self.flow_label_readout.setText(self.read_values("RATE"))

    def default_state(self):
        return {
            "GAS": "ARGON",
            "RATE": "0.0",
        }

    def settings_to_UI(self):
        self.rate_edit.setText(str(self.settings["RATE"]))
        self.gas_drop.setCurrentText(self.settings["GAS"])
