#
#

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QLineEdit, QLabel, QFormLayout, QGridLayout, QComboBox

from hardware_control.base import HC_Instrument, HC_Comm
import logging

logger = logging.getLogger(__name__)

#
#
class HC_FlowController(HC_Instrument):
    def __init__(
        self, backend, window, name: str = "Flow Controller", lock_until_sync=False,
    ):

        super().__init__(window, name, backend, lock_until_sync)

        self.settings = {}
        self.name = name
        self.address = backend.connection_addr

        backend.dummy = self.window.app.dummy

        if backend in self.window.app.comms:
            self.comm = self.window.app.comms[backend]
            self.comm.addWidget(self)
        else:
            self.window.app.comms[backend] = HC_Comm(backend, self, 2000)
            self.comm = self.window.app.comms[backend]

        self.filename = ""

        # # Initialize state to correct values
        # if initialize_with == "DEFAULT":
        #     self.save_on_close = False
        #     # Can't save without filename
        self.settings = self.default_state()
        # else:
        #     self.load_state(initialize_with)
        #     self.filename = initialize_with

        # *************************Create GUI************************

        # ****** DEFINE TEXT BOXES
        #
        self.rate_edit = QLineEdit()
        self.rate_edit.setValidator(QDoubleValidator())
        self.rate_edit.editingFinished.connect(
            lambda: self.comm.update_setting("rate", self.rate_edit.text())
        )
        self.rate_edit.setText(str(self.settings["rate"]))
        #
        self.form = QFormLayout()
        self.form.addRow("Flow rate (CFM?):", self.rate_edit)

        self.lower_grid = QGridLayout()
        #
        # ******* DEFINE DROPDOWNS + READOUT
        #
        self.gas_label = QLabel("Gas:")
        self.gas_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.gas_drop = QComboBox()
        self.gas_drop.addItems(["Argon", "Helium", "Hydrogen", "Air"])
        self.gas_drop.currentIndexChanged.connect(
            lambda: self.comm.update_setting("gas", self.gas_drop.currentText())
        )
        self.gas_drop.setCurrentText(self.settings["gas"])
        #
        self.pressure_label_fix0 = QLabel("Pressure: ")
        self.pressure_label_fix0.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.pressure_label_readout = QLabel("--")
        self.pressure_label_readout.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.pressure_label_fix1 = QLabel(" Torr?")
        self.pressure_label_fix1.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        #
        #
        self.flow_label_fix0 = QLabel("Flow: ")
        self.flow_label_fix0.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.flow_label_readout = QLabel("--")
        self.flow_label_readout.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.flow_label_fix1 = QLabel(" CFM?")
        self.flow_label_fix1.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
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
        #
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

        self.values["rate"] = "-"
        self.values["pressure"] = "-"

    def close(self):  # Note: this is a complete duplicate of the 'close()' function
        # in HC_Instrument, except it adds readout_timer.stop()

        if self.comm is not None:
            self.comm.close()
        self.readout_timer.stop

    def update_readout(self):
        """Queries the instrument for current readout data, then reads the most
        recent readout data from the inbox and pushes it to the GUI"""

        # Request updated readout data
        self.comm.command(f"rate?")
        self.comm.command(f"pressure?")

        # Get latest inbox entries for readout data...
        flow_meas = self.read_values(f"rate=")
        press_meas = self.read_values(f"pressure=")

        # Update self.values
        self.values["rate"] = flow_meas
        self.values["pressure"] = press_meas

        # Update labels
        self.pressure_label_readout.setText(press_meas)
        self.flow_label_readout.setText(flow_meas)

    # def get_header(self):
    #     # Todo: what are the units?
    #     return "Rate[?] Pressure[?]"
    #
    # def get_value_keys(self):
    #     return [self.values["rate"], self.values["pressure"]]

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        dflt["gas"] = "Argon"
        dflt["rate"] = 0.0

        return dflt

    def settings_to_UI(self):

        self.rate_edit.setText(str(self.settings["rate"]))
        self.gas_drop.setCurrentText(self.settings["gas"])
