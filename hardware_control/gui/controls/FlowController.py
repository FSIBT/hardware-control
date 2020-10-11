import logging

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QLineEdit, QLabel, QFormLayout, QGridLayout, QComboBox

from ..base import Instrument
from ..widgets import QControlCombo, QIndicator, QControl

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
        self.rate = QControl(self, "RATE", "Flow rate (sccm)")

        # ******* DEFINE DROPDOWNS + READOUT
        self.gas = QControlCombo(
            self,
            "GAS",
            "Gas",
            ["Argon", "Helium", "Hydrogen", "Air"],
            label_align="right",
        )

        self.pressure = QIndicator(
            self, "Pressure", unit="Torr", use_prefix=False, label_align="right",
        )
        self.flow = QIndicator(
            self, "Flow", unit="sccm", use_prefix=False, label_align="right",
        )

        self.autolayout_grid()

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
        self.pressure.setText(self.read_values("PRESSURE"))
        self.flow.setText(self.read_values("RATE"))

    def default_state(self):
        return {
            "GAS": "ARGON",
            "RATE": "0.0",
        }

    def settings_to_UI(self):
        self.rate.settings_to_UI()
        self.gas.settings_to_UI()
