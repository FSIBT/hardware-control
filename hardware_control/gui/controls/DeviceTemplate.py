import logging

from PyQt5.QtWidgets import QLabel, QGridLayout, QGroupBox

from ..widgets import HCLineEdit, HCDoubleSpinBox

logger = logging.getLogger(__name__)


class DeviceType(QGroupBox):
    """An example for new GUI element that controls an instrument.

    This code can be used as a template to write a new GUI element.
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        channels: list,
        name: str = "TemplateDevice",
        initialize_with: str = "INSTRUMENT",
    ):
        super().__init__()

        self.app = app
        self.instrument = instrument_name

        # Create UI - example
        self.lineEdit = HCLineEdit(
            self.app, self.instrument, parameter="CH1_VOLT", label="voltage"
        )

        self.text = QLabel()
        self.text.setText("123")

        self.spinbox = HCDoubleSpinBox(
            self.app, self.instrument, parameter="CH2_VOLT", label="Voltage"
        )
        self.spinbox.setRange(0, 10)
        self.spinbox.setSingleStep(0.15)

        self.layout = QGridLayout()

        self.layout.addWidget(self.lineEdit.label, 0, 0)
        self.layout.addWidget(self.lineEdit, 0, 1)

        self.layout.addWidget(self.text, 1, 0)

        self.layout.addWidget(self.spinbox.label, 2, 0)
        self.layout.addWidget(self.spinbox, 2, 1)

        self.setLayout(self.layout)

        self.config_auto_update()

    def config_auto_update(self):
        """Code that reads certain settings on a regular basis"""

        for parameter in ["CH1_VOLT", "CH2_Volt"]:
            self.app.add_auto_update_instrument_parameter(self.instrument, parameter)
