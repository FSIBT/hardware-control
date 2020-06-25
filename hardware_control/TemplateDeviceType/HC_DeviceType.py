from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLineEdit, QLabel, QGridLayout, QDoubleSpinBox

from hardware_control.base import HC_Instrument, HC_Comm
import logging

logger = logging.getLogger(__name__)


class HC_DeviceType(HC_Instrument):
    # Convention: __init__(self, backend, window . . . )
    def __init__(
        self,
        backend,
        window,
        channels: list,
        name: str = "TemplateDevice",
        initialize_with: str = "INSTRUMENT",
        save_on_close: str = False,
        lock_until_sync=False,
    ):
        # initalizing
        super().__init__(window, name, backend, lock_until_sync)
        self.settings = {}  # A dict to store all possible settings
        self.save_on_close = save_on_close
        self.backend = backend

        if scpi_instr in self.window.app.comms:
            self.comm = self.window.app.comms[scpi_instr]
            self.comm.addWidget(self)
        else:
            self.window.app.comms[scpi_instr] = HC_Comm(scpi_instr, self)
            self.comm = self.window.app.comms[scpi_instr]

        # self.filename = ""  # currently not in use

        ### Create UI - example
        self.lineEdit = QLineEdit()
        self.lineEdit.setText("10")
        self.lineEdit.editingFinished.connect(
            lambda: self.command(self.lineEdit.text())
        )

        self.text = QLabel()
        self.text.setText("123")

        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(0, 10)
        self.spinbox.setSingleStep(0.15)
        self.spinbox.editingFinished.connect(
            lambda: self.update_setting("Volt_Channel1", str(self.spinbox.value()))
        )

        self.layout = QGridLayout()
        self.layout.addWidget(self.lineEdit, 0, 0)
        self.layout.addWidget(self.text, 0, 1)
        self.layout.addWidget(self.spinbox, 1, 0)
        self.setLayout(self.layout)
        ###

        ### add your specific settings
        self.settings["Volt_Channel1"] = 123
        self.settings["Volt_Channel2"] = 456

        # Create timer to query
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

        # Write state to Backend
        # this sends all settings, which are stored in the settings dictionary to the backend
        self.send_state()

    # Updates the readout
    def update_readout(self):
        self.command("RND")  # Sends readout command (for example)
        mess = self.read_values(
            "RND"
        )  # recived messige will be stored, once available this will read it out, that way the UI wont freeze
        if mess:
            self.text.setText(mess)

    def settings_to_UI(self):
        """ Add code to this function to make the widgets in the GUI update
        to reflect the state of the 'self.settings' dictionary. """

        pass
