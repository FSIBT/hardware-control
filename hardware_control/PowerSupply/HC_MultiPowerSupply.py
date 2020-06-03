#
# This defines the OscilloscopeControl and OscilloscopeComm classes. By passing
# an instance of a SCPI command wrapper class to an OscilloscpeControl objcet,
# you can easily create GUIs for oscilloscopes.
#

import pkg_resources
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QDoubleValidator, QPixmap, QFont
from PyQt5.QtWidgets import (
    QLineEdit,
    QPushButton,
    QLabel,
    QWidget,
    QGridLayout,
    QGroupBox,
)

from hardware_control.base import HC_Instrument, HC_Comm, setButtonState
import logging

logger = logging.getLogger(__name__)


class HC_MultiPowerSupply(HC_Instrument):
    def __init__(
        self, backend, window, channels: list, name: str = "Multi-Channel PSU",
    ):

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

        # Check that the user provided valid channel request...
        if (len(channels) > backend.num_channels) or (
            max(channels) > self.backend.num_channels
        ):
            logger.warning(
                "WARNING: Requested channel not available on instrument. Ignoring extra channels."
            )

        # Add channels that are within range and not repeats
        self.channels = []
        for c in channels:
            if (c <= self.backend.num_channels) and (not c in self.channels):
                self.channels.append(c)
                self.values[f"CH{c}_V_out"] = "-"
                self.values[f"CH{c}_I_out"] = "-"
                self.values[f"CH{c}_V_set"] = "-"
                self.values[f"CH{c}_I_set"] = "-"

        # Initialize settings to correct values
        # if initialize_with == "INSTRUMENT":
        #     self.save_on_close = False
        #     # Can't save without filename
        #     self.settings = self.initialize_gui_instrument()
        # elif initialize_with == "DEFAULT":
        #     self.save_on_close = False
        #     # Can't save without filename
        self.settings = self.default_state()
        # else:
        #     self.load_state(initialize_with)
        #     self.filename = initialize_with

        # Create GUI
        #
        #
        # Automatically create channel widgets and push them into a row
        self.channel_widgets = []
        self.channel_panel = QGridLayout()
        for idx, c in enumerate(self.channels):
            self.channel_widgets.append(PowerSupplyChannel(c, self))
            self.channel_panel.addWidget(self.channel_widgets[-1], 0, idx)
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.channel_panel, 0, 0)
        #
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

    def close(self):  # Note: this is a complete duplicate of the 'close()' function
        # in HC_Instrument, except it adds readout_timer.stop()

        if self.comm is not None:
            self.comm.close()
        self.readout_timer.stop()

    def update_readout(self):
        """Queries the instrument for current readout data, then reads the most
        recent readout data from the inbox and pushes it to the GUI"""

        # Request updated readout data
        for idx, c in enumerate(self.channels):  # For each channel...
            self.comm.command(f"CH{c}_V_out?")
            self.comm.command(f"CH{c}_I_out?")
            self.comm.command(f"CH{c}_V_set?")
            self.comm.command(f"CH{c}_I_set?")
            if self.channel_widgets[idx].show_VI_limits:
                self.comm.command(f"CH{c}_V_max?")
                self.comm.command(f"CH{c}_I_max?")
            # if self.channel_widgets[idx].show_status_panel:
            #     self.comm.command(f"CH{c}_current_limited?")
            #     self.comm.command(f"CH{c}_output_enabled?")
            #     self.comm.command(f"CH{c}_ramp_direction?")

            # Get latest inbox entries for readout data...
            Vout = self.read_values(f"CH{c}_V_out")
            Iout = self.read_values(f"CH{c}_I_out")
            Vset = self.read_values(f"CH{c}_V_set")
            Iset = self.read_values(f"CH{c}_I_set")
            if self.channel_widgets[idx].show_VI_limits:
                Vmax = self.read_values(f"CH{c}_V_max")
                Imax = self.read_values(f"CH{c}_I_max")
            # if self.channel_widgets[idx].show_status_panel:
            #     self.comm.command(f"CH{c}_current_limited?")
            #     self.comm.command(f"CH{c}_output_enabled?")
            #     self.comm.command(f"CH{c}_ramp_direction?")

            self.values[f"CH{c}_V_out"] = Vout
            self.values[f"CH{c}_I_out"] = Iout
            self.values[f"CH{c}_V_set"] = Vset
            self.values[f"CH{c}_I_set"] = Iset
            # if self.channel_widgets[idx].show_VI_limits:
            #     self.values[f"CH{c}_V_max"] = Vmax
            #     self.values[f"CH{c}_I_max"] = Imax

            logger.debug(
                f"'{self.name}'[{c}] received values: {Vout}, {Iout}, {Vset}, {Iset}, {Vmax}, {Imax}"
            )

            # Send newest data to GUI
            self.channel_widgets[idx].update_readout(Vout, Iout, Vset, Iset, Vmax, Imax)

    def set_maxI(self, channel: int, maxI: float):
        """ Sets an internal limit for the current from channel 'n'. """

        try:
            channel = int(channel)
        except:
            return

        self.comm.update_setting("CH{channel}_I_max", str(maxI))

    def set_maxV(self, channel: int, maxV: float):
        """ Sets an internal limit for the voltage from channel 'n'. """

        try:
            channel = int(channel)
        except:
            return

        self.comm.update_setting("CH{channel}_V_max", str(maxV))

    def get_header(self):

        retval = ""
        for c in self.channels:
            retval = (
                retval + f"CH{c}_V_out[V] CH{c}_I_out[A] CH{c}_V_set[V] CH{c}_I_set[A] "
            )

        return retval

    def get_value_keys(self):

        retval = []
        for c in self.channels:
            retval.append(f"CH{c}_V_out")
            retval.append(f"CH{c}_I_out")
            retval.append(f"CH{c}_V_set")
            retval.append(f"CH{c}_I_set")

        return retval

    def set_channel_label(self, channel: int, label: str):
        """ Sets a channel label to a new custom value """

        try:
            for cw in self.channel_widgets:
                if cw.channel == channel:
                    cw.set_label(label)
            # self.channel_widgets[channel].set_label(label)
        except:
            logger.error(f"Failed to set channel {channel} label to {label}")

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        for c in self.channels:
            dflt[f"CH{c}_enabled"] = False
            dflt[f"CH{c}_V_set"] = 0
            dflt[f"CH{c}_I_set"] = 0.5

        return dflt

    def settings_to_UI(self):

        for c in self.channel_widgets:
            c.settings_to_UI()


class PowerSupplyChannel(QWidget):
    def __init__(self, channel: int, main_widget):
        super().__init__()

        self.channel = channel
        self.main_widget = main_widget

        # Style options
        self.show_VI_limits = True
        self.show_custom_labels = True
        self.custom_labels_colorcoded = False
        self.show_status_panel = True

        # ************** DEFINE UI *********************#
        #
        self.channel_label = QLabel()
        if self.channel <= 20 and not self.show_custom_labels:
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", f"graphics/channel_{self.channel}.png",
                    )
                )
            )
        else:
            if self.custom_labels_colorcoded:
                colors = ["yellow", "green", "blue", "red", "violet", "orange"]
                self.channel_label.setText(
                    f'<font color="{colors[(channel-1)%6]}">Channel {channel}</font>'
                )
            else:
                self.channel_label.setText(f"Channel {channel}")
            self.channel_label.setFont(QFont("Arial", 20))
            self.channel_label.setAlignment(
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            )

        # ****** DEFINE READOUTS
        #
        self.V_set_label = QLabel("Vset:")
        self.V_set_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.V_set_label_val = QLabel("-------")
        self.V_set_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.I_set_label = QLabel("Iset:")
        self.I_set_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.I_set_label_val = QLabel("-------")
        self.I_set_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        #
        #
        self.V_out_label = QLabel("Vout:")
        self.V_out_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.V_out_label_val = QLabel("-------")
        self.V_out_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.I_out_label = QLabel("Iout:")
        self.I_out_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.I_out_label_val = QLabel("-------")
        self.I_out_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        #
        #
        self.P_out_label = QLabel("Pout:")
        self.P_out_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.P_out_label_val = QLabel("-------")
        self.P_out_label_val.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        if self.show_VI_limits:
            self.V_max_label = QLabel("Vmax:")
            self.V_max_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            #
            self.V_max_label_val = QLabel("-------")
            self.V_max_label_val.setAlignment(
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            )
            #
            self.I_max_label = QLabel("Imax:")
            self.I_max_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            #
            self.I_max_label_val = QLabel("-------")
            self.I_max_label_val.setAlignment(
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            )

        # Layout readout
        self.readout_grid = QGridLayout()
        self.readout_grid.addWidget(self.V_set_label, 0, 0)
        self.readout_grid.addWidget(self.V_set_label_val, 0, 1)
        self.readout_grid.addWidget(self.I_set_label, 1, 0)
        self.readout_grid.addWidget(self.I_set_label_val, 1, 1)
        #
        self.readout_grid.addWidget(self.V_out_label, 0, 2)
        self.readout_grid.addWidget(self.V_out_label_val, 0, 3)
        self.readout_grid.addWidget(self.I_out_label, 1, 2)
        self.readout_grid.addWidget(self.I_out_label_val, 1, 3)
        #
        self.readout_grid.addWidget(self.P_out_label, 2, 2)
        self.readout_grid.addWidget(self.P_out_label_val, 2, 3)
        #
        if self.show_VI_limits:
            self.readout_grid.addWidget(self.V_max_label, 3, 0)
            self.readout_grid.addWidget(self.V_max_label_val, 3, 1)
            self.readout_grid.addWidget(self.I_max_label, 3, 2)
            self.readout_grid.addWidget(self.I_max_label_val, 3, 3)

        # ****** DEFINE CONTROLS
        #
        self.V_ctrl_label = QLabel("Voltage (V):")
        self.V_ctrl_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.I_ctrl_label = QLabel("Current (A): ")
        self.I_ctrl_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.V_edit = QLineEdit()
        self.V_edit.setValidator(QDoubleValidator())
        self.V_edit.editingFinished.connect(
            lambda: main_widget.update_setting(
                f"CH{self.channel}_V_set", (self.V_edit.text())
            )
        )
        self.V_edit.setText(str(main_widget.settings[f"CH{channel}_V_set"]))
        #
        self.I_edit = QLineEdit()
        self.I_edit.setValidator(QDoubleValidator())
        self.I_edit.editingFinished.connect(
            lambda: main_widget.update_setting(
                f"CH{self.channel}_I_set", (self.I_edit.text())
            )
        )
        self.I_edit.setText(str(main_widget.settings[f"CH{channel}_I_set"]))
        #
        self.enabled_but = QPushButton()
        self.enabled_but.setText("On/Off")
        self.enabled_but.setCheckable(True)
        self.enabled_but.clicked.connect(
            lambda: main_widget.update_setting(
                f"CH{channel}_enabled", str(self.enabled_but.isChecked())
            )
        )
        setButtonState(self.enabled_but, main_widget.settings[f"CH{channel}_enabled"])
        #
        self.controls_grid = QGridLayout()
        self.controls_grid.addWidget(self.V_ctrl_label, 0, 0)
        self.controls_grid.addWidget(self.V_edit, 0, 1)
        self.controls_grid.addWidget(self.I_ctrl_label, 1, 0)
        self.controls_grid.addWidget(self.I_edit, 1, 1)
        self.controls_grid.addWidget(self.enabled_but, 2, 1)

        # Load pix maps
        self.steady_pix = QPixmap(
            pkg_resources.resource_filename("hardware_control", f"icons/steady_ind.svg")
        )
        self.falling_pix = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", f"icons/falling_ind.svg"
            )
        )
        self.rising_pix = QPixmap(
            pkg_resources.resource_filename("hardware_control", f"icons/rising_ind.svg")
        )
        self.grey_pix = QPixmap(
            pkg_resources.resource_filename("hardware_control", f"icons/grey_ind.svg")
        )
        self.red_pix = QPixmap(
            pkg_resources.resource_filename("hardware_control", f"icons/red_ind.svg")
        )
        self.green_pix = QPixmap(
            pkg_resources.resource_filename("hardware_control", f"icons/green_ind.svg")
        )
        self.blue_pix = QPixmap(
            pkg_resources.resource_filename("hardware_control", f"icons/blue_ind.svg")
        )

        self.CC_ind_label = QLabel("CC:")
        self.CC_ind_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.CC_ind = QLabel()
        self.CC_ind.setPixmap(self.grey_pix)

        self.enabled_ind_label = QLabel("Output:")
        self.enabled_ind_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.enabled_ind = QLabel()
        self.enabled_ind.setPixmap(self.grey_pix)

        self.ramp_ind_label = QLabel("Ramp:")
        self.ramp_ind_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.ramp_ind = QLabel()
        self.ramp_ind.setPixmap(self.steady_pix)

        self.status_panel = QGroupBox()
        self.status_grid = QGridLayout()
        self.status_grid.addWidget(self.CC_ind_label, 0, 1)
        self.status_grid.addWidget(self.enabled_ind_label, 0, 2)
        self.status_grid.addWidget(self.ramp_ind_label, 0, 3)
        self.status_grid.addWidget(self.CC_ind, 1, 1)
        self.status_grid.addWidget(self.enabled_ind, 1, 2)
        self.status_grid.addWidget(self.ramp_ind, 1, 3)
        self.status_panel.setLayout(self.status_grid)

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.channel_label, 0, 0)
        self.master_layout.addLayout(self.readout_grid, 1, 0)
        self.master_layout.addLayout(self.controls_grid, 2, 0)
        if self.show_status_panel:
            self.master_layout.addWidget(self.status_panel, 3, 0)
        self.setLayout(self.master_layout)

    def update_readout(self, Vout, Iout, Vset, Iset, Vmax=None, Imax=None):

        if Vout is not None:
            try:
                self.V_out_label_val.setText(f"{round(float(Vout), 3)} V")
            except:
                self.V_out_label_val.setText(f"----- V")
        else:
            self.V_out_label_val.setText(f"----- V")

        if Iout is not None:
            try:
                self.I_out_label_val.setText(f"{round(float(Iout), 3)} A")
            except:
                self.I_out_label_val.setText(f"----- A")
        else:
            self.I_out_label_val.setText(f"----- A")

        if Vset is not None:
            try:
                self.V_set_label_val.setText(f"{round(float(Vset), 3)} V")
            except:
                self.V_set_label_val.setText(f"----- V")
        else:
            self.V_set_label_val.setText(f"----- V")

        if Iset is not None:
            try:
                self.I_set_label_val.setText(f"{round(float(Iset), 3)} A")
            except:
                self.I_set_label_val.setText(f"----- A")
        else:
            self.I_set_label_val.setText(f"----- A")

        if Vout is not None and Iout is not None:
            try:
                pwr = float(Vout) * float(Iout)
                self.P_out_label_val.setText(f"{round(pwr, 3)} W")
            except Exception as e:
                self.P_out_label_val.setText("----- W")
        else:
            self.P_out_label_val.setText("----- W")

        if self.show_VI_limits:
            if Vmax is not None:
                try:
                    self.V_max_label_val.setText(f"{round(float(Vmax), 3)} V")
                except:
                    self.V_max_label_val.setText("---- V")
            else:
                self.V_max_label_val.setText("None")

            if Imax is not None:
                try:
                    self.I_max_label_val.setText(f"{round(float(Vmax), 3)} A")
                except:
                    self.I_max_label_val.setText("---- A")
            else:
                self.I_max_label_val.setText("None")

    def set_label(self, label: str):

        if self.custom_labels_colorcoded:
            colors = ["yellow", "green", "blue", "red", "violet", "orange"]
            self.channel_label.setText(
                f'<font color="{colors[(self.channel-1)%6]}">{label}</font>'
            )
        else:
            self.channel_label.setText(f"{label}")
        self.channel_label.setFont(QFont("Arial", 20))
        self.channel_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

    def settings_to_UI(self):

        self.V_edit.setText(str(self.main_widget.settings[f"CH{self.channel}_V_set"]))
        self.I_edit.setText(str(self.main_widget.settings[f"CH{self.channel}_I_set"]))
        setButtonState(
            self.enabled_but, self.main_widget.settings[f"CH{self.channel}_enabled"]
        )
