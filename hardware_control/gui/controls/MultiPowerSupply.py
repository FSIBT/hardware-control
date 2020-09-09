import logging

from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QDoubleValidator, QFont
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

from ..base import Instrument
from ...utility import (
    remove_end_carriage_return,
    apply_to_label,
)
from ..widgets import setButtonState, load_icon


logger = logging.getLogger(__name__)

LABEL_MIN_WIDTH = 15
DISP_DECIMAL_PLACES = 1


class MultiPowerSupply(Instrument):
    """A GUI for a multi channel power supply.

    Example of a 3 channel power supply:

    .. image:: /images/controls/MultiPowerSupply-3ch.png
      :height: 200

    See Also
    --------
    hardware_control.backends.caen.Caen_14xxET.Caen_14xxET
    hardware_control.backends.keysight.Keysight_36300.Keysight_36300
    hardware_control.backends.rigol.Rigol_DP832.RigolDP832

    """

    ADD = "Add"
    ONLY = "Only"
    HIDE = "Hide"

    def __init__(
        self,
        app,
        backend,
        channels: list,
        name: str = "Multi-Channel PSU",
        show_VI_limits=False,
        show_custom_labels=False,
        show_status_panel=False,
        all_enable_button=None,
        lock_until_sync=False,
    ):
        if all_enable_button is None:
            all_enable_button = MultiPowerSupply.HIDE

        super().__init__(app, name, backend, lock_until_sync)

        self.all_enable_button = all_enable_button

        # Check that the user provided valid channel request...
        if (len(channels) > backend.num_channels) or (
            max(channels) > self.backend.num_channels
        ):
            logger.warning(
                "WARNING: Requested channel not available on instrument."
                " Ignoring extra channels."
            )

        # Add channels that are within range and not repeats
        self.channels = []
        for c in channels:
            if (c <= self.backend.num_channels) and (not c in self.channels):
                self.channels.append(c)
                self.values[f"CH{c}_V_OUT"] = "-"
                self.values[f"CH{c}_I_OUT"] = "-"
                self.values[f"CH{c}_V_SET"] = "-"
                self.values[f"CH{c}_I_SET"] = "-"

        self.init_values()
        self.settings = self.default_state()

        # Create GUI
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
                    (all_enable_button == MultiPowerSupply.ONLY),
                )
            )
            self.channel_panel.addWidget(self.channel_widgets[-1], 0, idx)
        #

        self.all_enable_but = QPushButton("All On/Off")
        if self.all_enable_button == MultiPowerSupply.ONLY:
            self.all_enable_but.setCheckable(True)
        else:
            self.all_enable_but.setCheckable(False)
        self.all_enable_but.clicked.connect(self.all_on_off)
        setButtonState(self.all_enable_but, False)

        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.channel_panel, 0, 0, 1, 3)
        if all_enable_button in [MultiPowerSupply.ADD, MultiPowerSupply.ONLY]:
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

    def all_on_off(self):

        # IF channel buttons are displayed, check their status to determine if
        # all need to be turned on vs off.
        if self.all_enable_button != MultiPowerSupply.ONLY:

            logger.debug(
                "All channels on/off button pressed."
                " Will check other channels' button states"
            )

            any_on = False
            for c in self.channel_widgets:
                if c.enabled_but.isChecked():
                    any_on = True
                    break

            for c in self.channel_widgets:
                if any_on:
                    self.update_setting(f"CH{c.channel}_ENABLE", str(False))
                    setButtonState(c.enabled_but, False)
                else:
                    self.update_setting(f"CH{c.channel}_ENABLE", str(True))
                    setButtonState(c.enabled_but, True)

        else:
            logger.debug(
                "All channels on/off button pressed. Will set based on button.isChecked()"
            )

            for c in self.channel_widgets:
                self.update_setting(
                    f"CH{c.channel}_ENABLE", str(self.all_enable_but.isChecked())
                )

    def close(self):
        super().close()
        self.readout_timer.stop()

    def update_readout(self):
        """Queries the instrument for current readout data, then reads the most
        recent readout data from the inbox and pushes it to the GUI"""

        # Request updated readout data
        for idx, c in enumerate(self.channels):  # For each channel...
            self.command(f"CH{c}_V_OUT?")
            self.command(f"CH{c}_I_OUT?")
            self.command(f"CH{c}_V_SET?")
            self.command(f"CH{c}_I_SET?")
            if self.channel_widgets[idx].show_VI_limits:
                self.command(f"CH{c}_V_MAX?")
                self.command(f"CH{c}_I_MAX?")
            if self.channel_widgets[idx].show_status_panel:
                self.command(f"CH{c}_ENABLE?")
            # if self.channel_widgets[idx].show_status_panel:
            #     self.command(f"CH{c}_current_limited?")
            #     self.command(f"CH{c}_output_enabled?")
            #     self.command(f"CH{c}_ramp_direction?")

            # Get latest inbox entries for readout data...
            Vout = remove_end_carriage_return(self.read_values(f"CH{c}_V_OUT"))
            Iout = remove_end_carriage_return(self.read_values(f"CH{c}_I_OUT"))
            Vset = remove_end_carriage_return(self.read_values(f"CH{c}_V_SET"))
            Iset = remove_end_carriage_return(self.read_values(f"CH{c}_I_SET"))
            if self.channel_widgets[idx].show_VI_limits:
                Vmax = remove_end_carriage_return(self.read_values(f"CH{c}_V_MAX"))
                Imax = remove_end_carriage_return(self.read_values(f"CH{c}_I_MAX"))
            if self.channel_widgets[idx].show_status_panel:
                enabled = remove_end_carriage_return(self.read_values(f"CH{c}_ENABLE"))
            else:
                enabled = None
            # if self.channel_widgets[idx].show_status_panel:
            #     self.command(f"CH{c}_current_limited?")
            #     self.command(f"CH{c}_output_enabled?")
            #     self.command(f"CH{c}_ramp_direction?")

            # self.values[f"CH{c}_V_OUT"] = Vout
            # self.values[f"CH{c}_I_OUT"] = Iout
            # self.values[f"CH{c}_V_SET"] = Vset
            # self.values[f"CH{c}_I_SET"] = Iset
            # if self.channel_widgets[idx].show_VI_limits:
            #     self.values[f"CH{c}_V_MAX"] = Vmax
            #     self.values[f"CH{c}_I_MAX"] = Imax
            # if self.channel_widgets[idx].show_status_panel:
            #     self.values[f"CH{c}_ENABELD"] = enabled

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

        self.update_setting(f"CH{channel}_I_MAX", str(maxI))

    def set_maxV(self, channel: int, maxV: float):
        """ Sets an internal limit for the voltage from channel 'n'. """

        try:
            channel = int(channel)
        except:
            return

        self.update_setting(f"CH{channel}_V_MAX", str(maxV))

    def set_channel_label(self, channel: int, label: str):
        """ Sets a channel label to a new custom value """

        try:
            for cw in self.channel_widgets:
                if cw.channel == channel:
                    cw.set_label(label)
            # self.channel_widgets[channel].set_label(label)
        except:
            logger.error(f"Failed to set channel {channel} label to {label}")

    def init_values(self):
        self.values = {}
        for c in self.channels:
            self.values[f"CH{c}_V_OUT"] = ""
            self.values[f"CH{c}_I_OUT"] = ""
            self.values[f"CH{c}_V_MAX"] = ""
            self.values[f"CH{c}_I_MAX"] = ""
            self.values[f"CH{c}_V_SET"] = ""
            self.values[f"CH{c}_I_SET"] = ""
            self.values[f"CH{c}_ENABLE"] = ""

    def default_state(self):
        """Create a default state object if can't get state from a file."""

        default = {}
        for c in self.channels:
            default[f"CH{c}_ENABLE"] = "False"
            default[f"CH{c}_V_SET"] = "0"
            default[f"CH{c}_I_SET"] = "0.5"

        return default

    def settings_to_UI(self):
        for c in self.channel_widgets:
            c.settings_to_UI()


class PowerSupplyChannel(QWidget):
    """A Qt-widget that implements controls for a single channel of a power supply.

    Used together with :py:class:`MulitPowerSupply`.
    """

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

        align_left_center = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        align_right_center = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter

        # ************** DEFINE UI *********************#
        self.channel_label = QLabel()
        if self.channel <= 20 and not self.show_custom_labels:
            self.channel_label.setPixmap(load_icon(f"channel_{self.channel}.png"))
        else:
            if self.custom_labels_colorcoded:
                colors = ["yellow", "green", "blue", "red", "violet", "orange"]
                self.channel_label.setText(
                    f'<font color="{colors[(channel-1)%6]}">Channel {channel}</font>'
                )
            else:
                self.channel_label.setText(f"Channel {channel}")
            self.channel_label.setFont(QFont("Arial", 20))
            self.channel_label.setAlignment(align_left_center)

        # ****** DEFINE READOUTS
        self.V_set_label = QLabel("Vset:")
        self.V_set_label.setAlignment(align_right_center)

        self.V_set_label_val = QLabel("-------")
        self.V_set_label_val.setAlignment(align_left_center)

        self.I_set_label = QLabel("Iset:")
        self.I_set_label.setAlignment(align_right_center)

        self.I_set_label_val = QLabel("-------")
        self.I_set_label_val.setAlignment(align_left_center)

        self.V_out_label = QLabel("Vout:")
        self.V_out_label.setAlignment(align_right_center)

        self.V_out_label_val = QLabel("-------")
        self.V_out_label_val.setAlignment(align_left_center)

        self.I_out_label = QLabel("Iout:")
        self.I_out_label.setAlignment(align_right_center)

        self.I_out_label_val = QLabel("-------")
        self.I_out_label_val.setAlignment(align_left_center)

        self.P_out_label = QLabel("Pout:")
        self.P_out_label.setAlignment(align_right_center)

        self.P_out_label_val = QLabel("-------")
        self.P_out_label_val.setAlignment(align_left_center)

        if self.show_VI_limits:
            self.V_max_label = QLabel("Vmax:")
            self.V_max_label.setAlignment(align_right_center)

            self.V_max_label_val = QLabel("-------")
            self.V_max_label_val.setAlignment(align_left_center)

            self.I_max_label = QLabel("Imax:")
            self.I_max_label.setAlignment(align_right_center)

            self.I_max_label_val = QLabel("-------")
            self.I_max_label_val.setAlignment(align_left_center)

        # Layout readout
        self.readout_grid = QGridLayout()
        self.readout_grid.addWidget(self.V_set_label, 0, 0)
        self.readout_grid.addWidget(self.V_set_label_val, 0, 1)
        self.readout_grid.addWidget(self.I_set_label, 1, 0)
        self.readout_grid.addWidget(self.I_set_label_val, 1, 1)

        self.readout_grid.addWidget(self.V_out_label, 0, 2)
        self.readout_grid.addWidget(self.V_out_label_val, 0, 3)
        self.readout_grid.addWidget(self.I_out_label, 1, 2)
        self.readout_grid.addWidget(self.I_out_label_val, 1, 3)

        self.readout_grid.addWidget(self.P_out_label, 2, 2)
        self.readout_grid.addWidget(self.P_out_label_val, 2, 3)

        if self.show_VI_limits:
            self.readout_grid.addWidget(self.V_max_label, 3, 0)
            self.readout_grid.addWidget(self.V_max_label_val, 3, 1)
            self.readout_grid.addWidget(self.I_max_label, 3, 2)
            self.readout_grid.addWidget(self.I_max_label_val, 3, 3)

        # ****** DEFINE CONTROLS
        #
        self.V_ctrl_label = QLabel("Voltage (V):")
        self.V_ctrl_label.setAlignment(align_right_center)

        self.I_ctrl_label = QLabel("Current (A): ")
        self.I_ctrl_label.setAlignment(align_left_center)

        self.V_edit = QLineEdit()
        self.V_edit.setValidator(QDoubleValidator())
        self.V_edit.editingFinished.connect(
            lambda: main_widget.update_setting(
                f"CH{self.channel}_V_SET", (self.V_edit.text())
            )
        )
        self.V_edit.setText(str(main_widget.settings[f"CH{channel}_V_SET"]))

        self.I_edit = QLineEdit()
        self.I_edit.setValidator(QDoubleValidator())
        self.I_edit.editingFinished.connect(
            lambda: main_widget.update_setting(
                f"CH{self.channel}_I_SET", (self.I_edit.text())
            )
        )
        self.I_edit.setText(str(main_widget.settings[f"CH{channel}_I_SET"]))

        self.enabled_but = QPushButton()
        self.enabled_but.setText("On/Off")
        self.enabled_but.setCheckable(True)
        self.enabled_but.clicked.connect(
            lambda: main_widget.update_setting(
                f"CH{channel}_ENABLE", str(self.enabled_but.isChecked())
            )
        )
        setButtonState(self.enabled_but, main_widget.settings[f"CH{channel}_ENABLE"])

        self.controls_grid = QGridLayout()
        self.controls_grid.addWidget(self.V_ctrl_label, 0, 0)
        self.controls_grid.addWidget(self.V_edit, 0, 1)
        self.controls_grid.addWidget(self.I_ctrl_label, 1, 0)
        self.controls_grid.addWidget(self.I_edit, 1, 1)
        if not hide_power_button:
            self.controls_grid.addWidget(self.enabled_but, 2, 1)

        # Load pix maps
        self.steady_ind = load_icon("steady_label.svg")
        self.rampdn_ind = load_icon("rampdn_label.svg")
        self.rampup_ind = load_icon("rampup_label.svg")
        self.disabled_ind = load_icon("disabled_label.svg")
        self.enabled_ind = load_icon("enabled_label.svg")
        self.ccurr_ind = load_icon("ccurrent_label.svg")
        self.cvolt_ind = load_icon("cvoltage_label.svg")
        self.na_ind = load_icon("na_label.svg")

        self.CC_ind_label = QLabel("CC:")
        self.CC_ind_label.setAlignment(align_left_center)
        self.CC_indic = QLabel()
        self.CC_indic.setPixmap(self.na_ind)

        self.enabled_ind_label = QLabel("Output:")
        self.enabled_ind_label.setAlignment(align_left_center)
        self.enabled_indic = QLabel()
        self.enabled_indic.setPixmap(self.na_ind)

        self.ramp_ind_label = QLabel("Ramp:")
        self.ramp_ind_label.setAlignment(align_left_center)
        self.ramp_indic = QLabel()
        self.ramp_indic.setPixmap(self.na_ind)

        self.status_panel = QGroupBox()
        self.status_grid = QGridLayout()
        self.status_grid.addWidget(self.CC_ind_label, 0, 1)
        self.status_grid.addWidget(self.enabled_ind_label, 0, 2)
        self.status_grid.addWidget(self.ramp_ind_label, 0, 3)
        self.status_grid.addWidget(self.CC_indic, 1, 1)
        self.status_grid.addWidget(self.enabled_indic, 1, 2)
        self.status_grid.addWidget(self.ramp_indic, 1, 3)
        self.status_panel.setLayout(self.status_grid)

        # ******* DEFINE OVERALL LAYOUT
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
                        self.CC_indic.setPixmap(self.ccurr_ind)
                    else:
                        self.CC_indic.setPixmap(self.cvolt_ind)
                except:
                    pass

            if enabled is not None:
                if enabled == "True":
                    self.enabled_indic.setPixmap(self.enabled_ind)
                    self.enabled_but.setChecked(True)
                else:
                    self.enabled_indic.setPixmap(self.disabled_ind)
                    self.enabled_but.setChecked(False)

            if (
                self.main_widget.ramp_timer.isActive()
                and f"CH{self.channel}_V_SET" in self.main_widget.active_ramps
            ):

                key = f"CH{self.channel}_V_SET"

                if self.main_widget.active_ramps[key] < self.main_widget.settings[key]:
                    self.ramp_indic.setPixmap(self.rampup_ind)
                else:
                    self.ramp_indic.setPixmap(self.rampdn_ind)
            else:
                self.ramp_indic.setPixmap(self.steady_ind)

    def set_label(self, label: str):
        align_left_center = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        if self.custom_labels_colorcoded:
            colors = ["yellow", "green", "blue", "red", "violet", "orange"]
            self.channel_label.setText(
                f'<font color="{colors[(self.channel-1)%6]}">{label}</font>'
            )
        else:
            self.channel_label.setText(f"{label}")
        self.channel_label.setFont(QFont("Arial", 20))
        self.channel_label.setAlignment(align_left_center)

    def settings_to_UI(self):
        self.V_edit.setText(str(self.main_widget.settings[f"CH{self.channel}_V_SET"]))
        self.I_edit.setText(str(self.main_widget.settings[f"CH{self.channel}_I_SET"]))
        setButtonState(
            self.enabled_but, self.main_widget.settings[f"CH{self.channel}_ENABLE"]
        )
