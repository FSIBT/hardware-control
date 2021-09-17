import logging

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QLineEdit,
    QLabel,
    QFormLayout,
    QGridLayout,
    QComboBox,
    QGroupBox,
)


from ..widgets import HCComboBox, HCLabel, HCLineEdit

logger = logging.getLogger(__name__)


class FlowController(QGroupBox):
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
        self,
        app,
        instrument_name: str,
        name: str = "Flow Controller",
    ):
        super().__init__(name)
        self.app = app
        self.instrument = instrument_name
        self.name = name

        self.rate = HCLineEdit(
            self.app, self.instrument, "RATE", label="Flow rate (sccm)"
        )

        # TODO: gas selection not implemented
        # self.gas = HCComboBox(
        #    self.app,
        #    self.instrument,
        #    parameter="GAS",
        #    label="Gas",
        #    items=["Argon", "Helium", "Hydrogen", "Air"],
        #    label_align="right",
        # )

        self.pressure = HCLabel(
            self.app,
            self.instrument,
            parameter="PRESSURE",
            label="Pressure",
            unit="Torr",
            use_prefix=False,
            label_align="right",
        )
        self.flow = HCLabel(
            self.app,
            self.instrument,
            parameter="RATE",
            label="Flow",
            unit="sccm",
            use_prefix=False,
            label_align="right",
        )

        self.layout = QGridLayout()
        self.layout.addWidget(self.rate.label, 0, 0)
        self.layout.addWidget(self.rate, 0, 1)

        # self.layout.addWidget(self.gas.label, 1, 0)
        # self.layout.addWidget(self.gas, 1, 1)

        self.layout.addWidget(self.pressure.label, 2, 0)
        self.layout.addWidget(self.pressure, 2, 1)

        self.layout.addWidget(self.flow.label, 3, 0)
        self.layout.addWidget(self.flow, 3, 1)

        self.setLayout(self.layout)

        # Create timer to query instrument
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.app.globalRefreshRate)

        logger.debug(f"Initalized {self.name}")

    def close(self):
        self.readout_timer.stop()
        super().close()

    def update_readout(self):
        """Queries the instrument for current readout data."""

        for parameter in ["RATE", "PRESSURE"]:
            self.app.update_instrument_parameter(self.instrument, parameter)
