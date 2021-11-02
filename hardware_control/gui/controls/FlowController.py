import logging

from PyQt5.QtWidgets import QGroupBox

from ..widgets import HCLabel, HCLineEdit, HCGridLayout

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

        self.layout = HCGridLayout([self.rate, self.pressure, self.flow])
        self.setLayout(self.layout)

        self.config_auto_update()

        logger.debug(f"Initalized {self.name}")

    def config_auto_update(self):
        """Queries the instrument for current readout data."""

        for parameter in ["RATE", "PRESSURE"]:
            self.app.add_auto_update_instrument_parameter(self.instrument, parameter)
