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


class HC_IOModule(HC_Instrument):
    # Convention: __init__(self, backend, window . . . )
    def __init__(
        self,
        backend,
        window,
        in_channels: list,
        out_channels: list,
        name: str = "IO Module",
    ):

        super().__init__(window, name)

        self.settings = {}
        self.backend = backend

        self.in_channels = in_channels
        self.out_channels = out_channels

        backend.dummy = self.window.app.dummy
        self.address = backend.connection_addr

        if backend in self.window.app.comms:
            self.comm = self.window.app.comms[backend]
            self.comm.addWidget(self)
        else:
            self.window.app.comms[backend] = HC_Comm(backend, self)
            self.comm = self.window.app.comms[backend]

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

        # self.v_edit_label = QLabel(" kV")
        # #
        # self.v_edit_spacer = QSpacerItem(
        #     10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        # )
        # #
        # self.V_edit = QLineEdit()
        # self.V_edit.setValidator(QDoubleValidator())
        # self.V_edit.setFixedWidth(100)
        # self.V_edit.editingFinished.connect(
        #     lambda: self.comm.update_setting(f"CH1_V_set", (self.V_edit.text()))
        # )
        # self.V_edit.setText("0")
        #
        # self.v_to_zero = QPushButton("Set to 0 V")
        # self.v_to_zero.setCheckable(False)
        # self.v_to_zero.clicked.connect(lambda: self.set_to_zero())
        # #

        self.main_layout = QGridLayout()
        self.main_layout.addLayout(self.channel_panel, 0, 0)
        # self.main_layout.addWidget(self.voltage_meas_label, 0, 0)
        # self.main_layout.addWidget(self.curr_meas_label, 1, 0)
        # self.main_layout.addWidget(self.press_meas_label, 2, 0)
        # self.main_layout.addWidget(self.V_edit, 0, 1)
        # self.main_layout.addWidget(self.v_edit_label, 0, 2)
        # self.main_layout.addItem(self.v_edit_spacer, 0, 3, 3, 3)
        # self.main_layout.addItem(self.bottom_spacer, 3, 0)
        # self.main_layout.addWidget(self.v_to_zero, 1, 1)

        self.setLayout(self.main_layout)

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

    def update_readout(self):

        for ic in self.in_channel_widgets:
            ic.update_readout()

        # self.comm.command("CH1_V_meas?")
        # self.comm.command("CH2_V_meas?")
        # self.comm.command("CH3_V_meas?")
        #
        # try:
        #     V_meas = remove_end_carriage_return(self.read_values(f"CH3_V_meas"))
        #     I_meas = remove_end_carriage_return(self.read_values(f"CH2_V_meas"))
        #     P_meas = remove_end_carriage_return(self.read_values(f"CH1_V_meas"))
        #
        #     if V_meas is not None:
        #         V_meas = float(V_meas) / 10 * 100e3 + 420  # 10V = 100 kV
        #
        #         if V_meas > 1e3:
        #             self.voltage_meas_label.setText(
        #                 f"Voltage: {round(float(V_meas)*1e-3, 3)} kV"
        #             )
        #         else:
        #             self.voltage_meas_label.setText(
        #                 f"Voltage: {round(float(V_meas), 3)} V"
        #             )
        #     else:
        #         self.voltage_meas_label.setText(f"Voltage: ---- V")
        #
        #     if I_meas is not None:
        #         I_meas = float(I_meas) / 10 * 3e-3 + 8.1e-6  # 10V = 100% = 3mA
        #
        #         if I_meas < 1e-3:
        #             self.press_meas_label.setText(
        #                 f"Current: {round(float(I_meas)*1e6, 3)} µA"
        #             )
        #         elif I_meas < 1:
        #             self.press_meas_label.setText(
        #                 f"Current: {round(float(I_meas)*1e3, 3)} mA"
        #             )
        #         else:
        #             self.press_meas_label.setText(
        #                 f"Current: {round(float(I_meas), 3)} A"
        #             )
        #     else:
        #         self.press_meas_label.setText(f"Current: ---- µA")
        #
        #     if P_meas is not None:
        #         P_meas = float(P_meas) * 100
        #
        #         self.curr_meas_label.setText(
        #             f"Pressure: {round(float(P_meas), 3)} mTorr"
        #         )
        #     else:
        #         self.curr_meas_label.setText(f"Pressure: ---- mTorr")
        #
        # except:
        #     logger.error("update readout failed", exc_info=True)


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
            apply_to_label(self.measurement_label, V_meas, self.units)

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
        # #
        self.edit_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        # #
        self.editbox = QLineEdit()
        self.editbox.setValidator(QDoubleValidator())
        self.editbox.setFixedWidth(100)
        self.editbox.editingFinished.connect(
            lambda: self.control.comm.update_setting(
                f"CH{self.channel}_V_set", (self.editbox.text())
            )
        )
        self.editbox.setText("0")

        self.unit_label = QLabel(f" {self.units}")

        if self.set_to_zero_button:
            self.to_zero_but = QPushButton("Set to 0 V")
            self.to_zero_but.setCheckable(False)
            self.to_zero_but.clicked.connect(lambda: self.set_to_zero())
        # #

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.edit_label, 0, 0)
        self.main_layout.addWidget(self.editbox, 0, 1)
        self.main_layout.addWidget(self.unit_label, 0, 2)
        if self.set_to_zero_button:
            self.main_layout.addWidget(self.to_zero_but, 1, 1, 1, 2)

        self.setLayout(self.main_layout)

    def update_readout(self):

        # Query value
        self.control.comm.command("CH{self.channel}_V_meas?")

        try:

            # Read return value
            V_meas = remove_end_carriage_return(
                self.read_values(f"CH{self.channel}_V_meas")
            )

            # Convert to float. Run through conversion function if provided
            if callable(self.conversion_function):
                V_meas = self.conversion_function(float(V_meas))
            else:
                V_meas = float(V_meas)

            # Update label
            apply_to_label(self.measurement_label, V_meas)

        except:
            self.measurement_label.setText(f"---- V")

    def set_to_zero(self):
        self.editbox.setText("0")
        self.control.update_setting(f"CH{self.channel}_V_set", "0")
