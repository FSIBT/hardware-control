"""
This is the Base class for reading modules
it provides a simple UI.
"""
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel, QWidget, QGridLayout, QLCDNumber, QSpacerItem

from hardware_control.base import HC_Instrument, HC_Comm
import logging
from PyQt5.QtGui import QDoubleValidator, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QGroupBox,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QWidget,
    QFormLayout,
    QGridLayout,
    QComboBox,
    QDoubleSpinBox,
    QSizePolicy,
)
from hardware_control.utility import remove_end_carriage_return, apply_to_label

logger = logging.getLogger(__name__)

LABEL_MIN_WIDTH = -15
DISP_DECIMAL_PLACES = 1


class HC_IOModule(HC_Instrument):
    def __init__(
        self,
        backend,
        window,
        in_channels: list,
        out_channels: list,
        name: str = "IO Module",
        lock_until_sync=False,
    ):

        super().__init__(window, name, backend, lock_until_sync)

        self.settings = {}
        self.backend = backend

        self.in_channels = in_channels
        self.out_channels = out_channels

        backend.dummy = self.window.app.dummy
        self.address = backend.connection_addr

        self.filename = ""

        self.channel_panel = QGridLayout()
        self.in_channel_widgets = []
        self.out_channel_widgets = []
        lowest_row = 0
        for idx, ic in enumerate(self.in_channels):
            if len(ic) != 4:
                continue

            self.in_channel_widgets.append(
                InputChannel(self, ic[0], ic[1], ic[2], ic[3])
            )
            self.channel_panel.addWidget(self.in_channel_widgets[-1], idx, 0)
            lowest_row = max(lowest_row, idx)

        for idx, oc in enumerate(self.out_channels):
            if len(oc) != 4:
                continue

            self.out_channel_widgets.append(
                OutputChannel(self, oc[0], oc[1], oc[2], oc[3], set_to_zero_button=True)
            )
            self.channel_panel.addWidget(self.out_channel_widgets[-1], idx, 1)
            lowest_row = max(lowest_row, idx)

        self.bottom_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.channel_panel.addItem(self.bottom_spacer, lowest_row + 1, 0, 1, 2)
        self.main_layout = QGridLayout()
        self.main_layout.addLayout(self.channel_panel, 0, 0)

        self.setLayout(self.main_layout)

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

    def update_readout(self):
        for ic in self.in_channel_widgets:
            ic.update_readout()


class InputChannel(QWidget):
    def __init__(self, control, channel, function=None, units="V", label="Voltage: "):

        super().__init__()

        self.control = control
        self.channel = channel

        self.conversion_function = function
        self.units = units

        self.label_str = label
        self.param_label = QLabel(self.label_str)
        if not self.label_str.endswith(": "):
            self.label_str = self.label_str + ": "
            self.param_label.setText(self.label_str)

        self.measurement_label = QLabel(f"---- {self.units}")
        self.measurement_label.setFixedWidth(120)

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.param_label, 0, 0)
        self.main_layout.addWidget(self.measurement_label, 0, 1)

        self.setLayout(self.main_layout)

    def update_readout(self):
        # Query value
        self.control.comm.command(f"CH{self.channel}_V_meas?")

        try:

            # Read return value
            V_meas = remove_end_carriage_return(
                self.control.read_values(f"CH{self.channel}_V_meas")
            )

            # Convert to float. Run through conversion function if provided
            if callable(self.conversion_function):
                V_meas = self.conversion_function(float(V_meas))

            # Update label
            apply_to_label(
                self.measurement_label,
                V_meas,
                self.units,
                DISP_DECIMAL_PLACES,
                LABEL_MIN_WIDTH,
            )

        except Exception as e:
            self.measurement_label.setText(f"---- V")


class OutputChannel(QWidget):
    def __init__(
        self,
        control,
        channel,
        function=None,
        units="V",
        label="Set voltage: ",
        set_to_zero_button=False,
    ):

        super().__init__()

        self.control = control
        self.channel = channel

        self.conversion_function = function
        self.units = units

        self.set_to_zero_button = set_to_zero_button

        self.edit_label = QLabel(label)

        self.edit_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )

        self.editbox = QLineEdit()
        self.editbox.setValidator(QDoubleValidator())
        self.editbox.setFixedWidth(100)
        self.editbox.editingFinished.connect(self.set_voltage)
        self.editbox.setText("0")

        self.unit_label = QLabel(f" {self.units}")

        if self.set_to_zero_button:
            self.to_zero_but = QPushButton("Set to 0 V")
            self.to_zero_but.setCheckable(False)
            self.to_zero_but.clicked.connect(lambda: self.set_to_zero())

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.edit_label, 0, 0)
        self.main_layout.addWidget(self.editbox, 0, 1)
        self.main_layout.addWidget(self.unit_label, 0, 2)
        if self.set_to_zero_button:
            self.main_layout.addWidget(self.to_zero_but, 1, 1, 1, 2)

        self.setLayout(self.main_layout)

    def set_voltage(self):
        voltage = float(self.editbox.text())

        if callable(self.conversion_function):
            voltage = self.conversion_function(voltage)

            self.control.update_setting(f"CH{self.channel}_V_set", str(voltage))

    def set_to_zero(self):
        self.editbox.setText("0")
        self.control.update_setting(f"CH{self.channel}_V_set", "0")
