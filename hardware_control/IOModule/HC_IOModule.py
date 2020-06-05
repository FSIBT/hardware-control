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
)
from hardware_control.utility import remove_end_carriage_return

logger = logging.getLogger(__name__)


class HC_IOModule(HC_Instrument):
    # Convention: __init__(self, backend, window . . . )
    def __init__(
        self, backend, window, channels: list, name: str = "IO Module",
    ):
        # initalizing
        super().__init__(window, name)

        self.settings = {}
        self.backend = backend

        backend.dummy = self.window.app.dummy
        self.address = backend.connection_addr

        if backend in self.window.app.comms:
            self.comm = self.window.app.comms[backend]
            self.comm.addWidget(self)
        else:
            self.window.app.comms[backend] = HC_Comm(backend, self)
            self.comm = self.window.app.comms[backend]

        self.filename = ""

        self.voltage_meas_label = QLabel("Voltage: ----")
        self.press_meas_label = QLabel("Current: ----")
        self.curr_meas_label = QLabel("Pressure: ----")
        #
        self.V_edit = QLineEdit()
        self.V_edit.setValidator(QDoubleValidator())
        self.V_edit.editingFinished.connect(
            lambda: update_setting(f"CH{self.channel}_V_set", (self.V_edit.text()))
        )
        self.V_edit.setText("0")

        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.voltage_meas_label, 0, 0)
        self.main_layout.addWidget(self.curr_meas_label, 1, 0)
        self.main_layout.addWidget(self.press_meas_label, 2, 0)
        self.main_layout.addWidget(self.V_edit, 0, 1)
        self.setLayout(self.main_layout)

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

    def update_readout(self):

        self.comm.command("CH1_V_meas?")
        self.comm.command("CH2_V_meas?")
        self.comm.command("CH3_V_meas?")

        try:
            V_meas = remove_end_carriage_return(self.read_values(f"CH1_V_meas"))
            I_meas = remove_end_carriage_return(self.read_values(f"CH2_V_meas"))
            P_meas = remove_end_carriage_return(self.read_values(f"CH3_V_meas"))

            self.voltage_meas_label.setText(f"Voltage: {round(float(V_meas), 3)}")
            self.voltage_meas_label.setText(f"Voltage: {round(float(I_meas), 3)}")
            self.voltage_meas_label.setText(f"Voltage: {round(float(P_meas), 3)}")
        except:
            logger.error("update readout failed")
