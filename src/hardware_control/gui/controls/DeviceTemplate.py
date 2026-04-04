import logging

from PyQt6.QtWidgets import QLabel, QGridLayout, QGroupBox

from ...base.gui_control import ValidatedControl
from ..widgets import HCLineEdit, HCDoubleSpinBox

logger = logging.getLogger(__name__)


class DeviceType(ValidatedControl, QGroupBox):
    """An example for new GUI element that controls an instrument.

    This code can be used as a template to write a new GUI element.

    This template demonstrates the ValidatedControl pattern:
    1. Inherit from ValidatedControl first, then QGroupBox
    2. Pass app and instrument_name to super().__init__()
    3. Create HC widgets (they auto-register their parameters)
    4. Manually add any parameters used directly (not through widgets)
    5. Call _validate_parameters() before setLayout()
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        channels: list,
        name: str = "TemplateDevice",
        initialize_with: str = "INSTRUMENT",
    ):
        # STEP 1: Pass app, instrument_name, and widget_name to super().__init__()
        # This auto-starts parameter collection via ValidatedControl
        super().__init__(app, instrument_name, name)

        self.app = app
        self.instrument = instrument_name

        # STEP 2: Create HC widgets
        # These widgets automatically register their parameters with ValidatedControl
        self.lineEdit = HCLineEdit(
            self.app, self.instrument, parameter="CH1_VOLT", label="voltage"
        )

        # Regular Qt widgets (not HC widgets) don't auto-register
        self.text = QLabel()
        self.text.setText("123")

        self.spinbox = HCDoubleSpinBox(
            self.app, self.instrument, parameter="CH2_VOLT", label="Voltage"
        )
        self.spinbox.setRange(0, 10)
        self.spinbox.setSingleStep(0.15)

        # STEP 3: Manually add parameters used directly (not through widgets)
        # Example: if you called app.set_instrument_parameter() or app.call_instrument_command()
        # self._add_required_parameter("RESET", param_type='command')
        # self._add_required_parameter("STATUS", param_type='parameter', access='read')

        # STEP 4: IMPORTANT - Validate parameters before using them!
        # This ensures the instrument provides all required parameters/commands
        self._validate_parameters()

        # STEP 5: Build the layout
        # After validation passes, you can safely use the instrument
        self.layout = QGridLayout()

        self.layout.addWidget(self.lineEdit.label, 0, 0)
        self.layout.addWidget(self.lineEdit, 0, 1)

        self.layout.addWidget(self.text, 1, 0)

        self.layout.addWidget(self.spinbox.label, 2, 0)
        self.layout.addWidget(self.spinbox, 2, 1)

        self.setLayout(self.layout)
