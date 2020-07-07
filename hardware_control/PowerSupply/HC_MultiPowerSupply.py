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
    QSpacerItem,
    QSizePolicy,
)

from hardware_control.base import HC_Instrument, HC_Comm, setButtonState
import logging
from hardware_control.utility import remove_end_carriage_return
from hardware_control.utility import change_units, apply_to_label

logger = logging.getLogger(__name__)

ADD = "Add"
ONLY = "Only"
HIDE = "Hide"

LABEL_MIN_WIDTH = 15
DISP_DECIMAL_PLACES = 1


class HC_MultiPowerSupply(HC_Instrument):
    def __init__(
        self,
        backend,
        window,
        channels: list,
        name: str = "Multi-Channel PSU",
        show_VI_limits=False,
        show_custom_labels=False,
        show_status_panel=False,
        all_enable_button=HIDE,
        lock_until_sync=False,
    ):

        super().__init__(window, name, backend, lock_until_sync)

        self.settings = {}
        self.backend = backend

        backend.dummy = self.window.app.dummy
        self.address = backend.connection_addr

        self.all_enable_button = all_enable_button

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

        self.init_values()

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
            self.channel_widgets.append(
                PowerSupplyChannel(
                    c,
                    self,
                    show_VI_limits,
                    show_custom_labels,
                    show_status_panel,
                    (all_enable_button == ONLY),
                )
            )
            self.channel_panel.addWidget(self.channel_widgets[-1], 0, idx)
        #

        self.all_enable_but = QPushButton("All On/Off")
        if self.all_enable_button == ONLY:
            self.all_enable_but.setCheckable(True)
        else:
            self.all_enable_but.setCheckable(False)
        self.all_enable_but.clicked.connect(self.all_on_off)
        setButtonState(self.all_enable_but, False)

        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.channel_panel, 0, 0, 1, 3)
        if all_enable_button == ADD or all_enable_button == ONLY:
            self.enable_all_spacer = QSpacerItem(
                10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
            )
            self.master_layout.addItem(self.enable_all_spacer, 1, 0, 1, 2)
            self.master_layout.addWidget(self.all_enable_but, 1, 2)
        #
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

        # Create timer to query voltages
        self.readout_timer = QTimer(self)
        self.readout_timer.timeout.connect(self.update_readout)
        self.readout_timer.start(self.globalRefreshRate)

        self.read_state_from_backend()

    def init_values(self):

        self.values = {}
        for c in self.channels:
            self.values[f"CH{c}_V_out"] = ""
            self.values[f"CH{c}_I_out"] = ""
            self.values[f"CH{c}_V_max"] = ""
            self.values[f"CH{c}_I_max"] = ""
            self.values[f"CH{c}_V_set"] = ""
            self.values[f"CH{c}_I_set"] = ""
            self.values[f"CH{c}_enable"] = ""

    def all_on_off(self):

        # IF channel buttons are displayed, check their status to determine if
        # all need to be turned on vs off.
        if self.all_enable_button != ONLY:

            logger.debug(
                "All channels on/off button pressed. Will check other channels' button states"
            )

            any_on = False
            for c in self.channel_widgets:
                if c.enabled_but.isChecked():
                    any_on = True
                    break

            for c in self.channel_widgets:
                if any_on:
                    self.update_setting(f"CH{c.channel}_enable", str(False))
                    setButtonState(c.enabled_but, False)
                else:
                    self.update_setting(f"CH{c.channel}_enable", str(True))
                    setButtonState(c.enabled_but, True)

        else:

            logger.debug(
                "All channels on/off button pressed. Will set based on button.isChecked()"
            )

            for c in self.channel_widgets:
                self.update_setting(
                    f"CH{c.channel}_enable", str(self.all_enable_but.isChecked())
                )

    def close(self):  # Note: this is a complete duplicate of the 'close()' function
        # in HC_Instrument, except it adds readout_timer.stop()

        if self.comm is not None:
            if self.comm.try_connect_timer.isActive():
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
            if self.channel_widgets[idx].show_status_panel:
                self.comm.command(f"CH{c}_enable?")
            # if self.channel_widgets[idx].show_status_panel:
            #     self.comm.command(f"CH{c}_current_limited?")
            #     self.comm.command(f"CH{c}_output_enabled?")
            #     self.comm.command(f"CH{c}_ramp_direction?")

            # Get latest inbox entries for readout data...
            Vout = remove_end_carriage_return(self.read_values(f"CH{c}_V_out"))
            Iout = remove_end_carriage_return(self.read_values(f"CH{c}_I_out"))
            Vset = remove_end_carriage_return(self.read_values(f"CH{c}_V_set"))
            Iset = remove_end_carriage_return(self.read_values(f"CH{c}_I_set"))
            if self.channel_widgets[idx].show_VI_limits:
                Vmax = remove_end_carriage_return(self.read_values(f"CH{c}_V_max"))
                Imax = remove_end_carriage_return(self.read_values(f"CH{c}_I_max"))
            if self.channel_widgets[idx].show_status_panel:
                enabled = remove_end_carriage_return(self.read_values(f"CH{c}_enable"))
            else:
                enabled = None
            # if self.channel_widgets[idx].show_status_panel:
            #     self.comm.command(f"CH{c}_current_limited?")
            #     self.comm.command(f"CH{c}_output_enabled?")
            #     self.comm.command(f"CH{c}_ramp_direction?")

            # self.values[f"CH{c}_V_out"] = Vout
            # self.values[f"CH{c}_I_out"] = Iout
            # self.values[f"CH{c}_V_set"] = Vset
            # self.values[f"CH{c}_I_set"] = Iset
            # if self.channel_widgets[idx].show_VI_limits:
            #     self.values[f"CH{c}_V_max"] = Vmax
            #     self.values[f"CH{c}_I_max"] = Imax
            # if self.channel_widgets[idx].show_status_panel:
            #     self.values[f"CH{c}_enabeld"] = enabled

            # print(f"Instr '{self.name}' sending values to widget # {idx} (CH: {c}). There are {len(self.channel_widgets)} total widgets.")
            if self.channel_widgets[idx].show_VI_limits:
                logger.debug(
                    f"'{self.name}'[{c}] received values: {Vout}, {Iout}, {Vset}, {Iset}, {Vmax}, {Imax}"
                )
            else:
                logger.debug(
                    f"'{self.name}'[{c}] received values: {Vout}, {Iout}, {Vset}, {Iset}"
                )

            # Send newest data to GUI
            if self.channel_widgets[idx].show_VI_limits:
                self.channel_widgets[idx].update_readout(
                    Vout, Iout, Vset, Iset, Vmax, Imax, enabled
                )
            else:
                self.channel_widgets[idx].update_readout(
                    Vout, Iout, Vset, Iset, enabled=enabled
                )

    def set_maxI(self, channel: int, maxI: float):
        """ Sets an internal limit for the current from channel 'n'. """

        try:
            channel = int(channel)
        except:
            return

        self.comm.update_setting(f"CH{channel}_I_max", str(maxI))

    def set_maxV(self, channel: int, maxV: float):
        """ Sets an internal limit for the voltage from channel 'n'. """

        try:
            channel = int(channel)
        except:
            return

        self.comm.update_setting(f"CH{channel}_V_max", str(maxV))

    # def get_header(self):
    #
    #     retval = ""
    #     for c in self.channels:
    #         retval = (
    #             retval + f"CH{c}_V_out[V] CH{c}_I_out[A] CH{c}_V_set[V] CH{c}_I_set[A] "
    #         )
    #
    #     return retval
    #
    # def get_value_keys(self):
    #
    #     retval = []
    #     for c in self.channels:
    #         retval.append(f"CH{c}_V_out")
    #         retval.append(f"CH{c}_I_out")
    #         retval.append(f"CH{c}_V_set")
    #         retval.append(f"CH{c}_I_set")
    #
    #     return retval

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
            dflt[f"CH{c}_enable"] = False
            dflt[f"CH{c}_V_set"] = 0
            dflt[f"CH{c}_I_set"] = 0.5

        return dflt

    def settings_to_UI(self):

        for c in self.channel_widgets:
            c.settings_to_UI()


class PowerSupplyChannel(QWidget):
    def __init__(
        self,
        channel: int,
        main_widget,
        show_VI_limits=False,
        show_custom_labels=False,
        show_status_panel=False,
        hide_power_button=False,
    ):
        super().__init__()

        self.channel = channel
        self.main_widget = main_widget

        # Style options
        self.show_VI_limits = show_VI_limits
        self.show_custom_labels = show_custom_labels
        self.show_status_panel = show_status_panel
        self.custom_labels_colorcoded = False

        # ************** DEFINE UI *********************#
        #
        self.channel_label = QLabel()
        if self.channel <= 20 and not self.show_custom_labels:
            self.channel_label.setPixmap(
                QPixmap(
                    pkg_resources.resource_filename(
                        "hardware_control", f"icons/channel_{self.channel}.png",
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
                f"CH{channel}_enable", str(self.enabled_but.isChecked())
            )
        )
        setButtonState(self.enabled_but, main_widget.settings[f"CH{channel}_enable"])
        #
        self.controls_grid = QGridLayout()
        self.controls_grid.addWidget(self.V_ctrl_label, 0, 0)
        self.controls_grid.addWidget(self.V_edit, 0, 1)
        self.controls_grid.addWidget(self.I_ctrl_label, 1, 0)
        self.controls_grid.addWidget(self.I_edit, 1, 1)
        if not hide_power_button:
            self.controls_grid.addWidget(self.enabled_but, 2, 1)

        # Load pix maps
        self.steady_ind = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", f"icons/steady_label.svg"
            )
        )
        self.rampdn_ind = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", f"icons/rampdn_label.svg"
            )
        )
        self.rampup_ind = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", f"icons/rampup_label.svg"
            )
        )
        self.disabled_ind = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", f"icons/disabled_label.svg"
            )
        )
        self.enabled_ind = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", f"icons/enabled_label.svg"
            )
        )
        self.ccurr_ind = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", f"icons/ccurrent_label.svg"
            )
        )
        self.cvolt_ind = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", f"icons/cvoltage_label.svg"
            )
        )
        self.na_ind = QPixmap(
            pkg_resources.resource_filename("hardware_control", f"icons/na_label.svg")
        )

        self.CC_ind_label = QLabel("CC:")
        self.CC_ind_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.CC_ind = QLabel()
        self.CC_ind.setPixmap(self.na_ind)

        self.enabled_ind_label = QLabel("Output:")
        self.enabled_ind_label.setAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )
        self.enabled_ind = QLabel()
        self.enabled_ind.setPixmap(self.na_ind)

        self.ramp_ind_label = QLabel("Ramp:")
        self.ramp_ind_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.ramp_ind = QLabel()
        self.ramp_ind.setPixmap(self.na_ind)

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

    def update_readout(
        self, Vout, Iout, Vset, Iset, Vmax=None, Imax=None, enabled=None
    ):

        apply_to_label(
            self.V_out_label_val, Vout, "V", DISP_DECIMAL_PLACES, LABEL_MIN_WIDTH
        )
        apply_to_label(
            self.I_out_label_val, Iout, "A", DISP_DECIMAL_PLACES, LABEL_MIN_WIDTH
        )
        apply_to_label(
            self.V_set_label_val, Vset, "V", DISP_DECIMAL_PLACES, LABEL_MIN_WIDTH
        )
        apply_to_label(
            self.I_set_label_val, Iset, "A", DISP_DECIMAL_PLACES, LABEL_MIN_WIDTH
        )

        if Vout is not None and Iout is not None:
            try:
                pwr = float(Vout) * float(Iout)
                apply_to_label(
                    self.P_out_label_val, pwr, "W", DISP_DECIMAL_PLACES, LABEL_MIN_WIDTH
                )
            except:
                apply_to_label(
                    self.P_out_label_val,
                    "----",
                    "W",
                    DISP_DECIMAL_PLACES,
                    LABEL_MIN_WIDTH,
                )

        if self.show_VI_limits:
            apply_to_label(
                self.V_max_label_val, Vmax, "V", DISP_DECIMAL_PLACES, LABEL_MIN_WIDTH
            )
            apply_to_label(
                self.I_max_label_val, Imax, "A", DISP_DECIMAL_PLACES, LABEL_MIN_WIDTH
            )

        if self.show_status_panel:
            if Iout is not None and Iset is not None:
                try:
                    if float(Iout) >= float(Iset) * 0.95:
                        self.CC_ind.setPixmap(self.ccurr_ind)
                    else:
                        self.CC_ind.setPixmap(self.cvolt_ind)
                except:
                    pass

            if enabled is not None:
                if enabled == "True":
                    self.enabled_ind.setPixmap(self.enabled_ind)
                else:
                    self.enabled_ind.setPixmap(self.disabled_ind)

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
            self.enabled_but, self.main_widget.settings[f"CH{self.channel}_enable"]
        )
