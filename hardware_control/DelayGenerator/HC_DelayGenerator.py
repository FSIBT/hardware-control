import pkg_resources
from PyQt5 import QtCore
from PyQt5.QtGui import QIntValidator, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QGroupBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
)

from hardware_control.base import HC_Instrument, HC_Comm


class HC_DelayGenerator(HC_Instrument):
    def __init__(
        self,
        scpi_instr,
        window,
        name: str = "Pulse Generator Control",
        initialize_with: str = "INSTRUMENT",
    ):

        super().__init__(window, name)

        self.settings = {}
        self.name = name

        self.settings = self.default_state()

        scpi_instr.dummy = self.window.app.dummy
        self.comm = HC_Comm(scpi_instr, self)
        self.filename = ""

        # Create GUI

        self.trig_mode_label = QLabel("Trigger Mode:")
        self.trig_mode_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_mode_drop = QComboBox()
        self.trig_mode_drop.addItems(["Internal", "External", "Single", "Burst"])
        self.trig_mode_drop.currentIndexChanged.connect(
            lambda: self.update_setting(
                f"trigger_mode", self.trig_mode_drop.currentText()
            )
        )
        self.trig_mode_drop.setCurrentText(str(self.settings[f"trigger_mode"]))
        #
        self.trig_edge_label = QLabel("Trigger Edge:")
        self.trig_edge_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_edge_drop = QComboBox()
        self.trig_edge_drop.addItems(["Positive", "Negative"])
        self.trig_edge_drop.currentIndexChanged.connect(
            lambda: self.update_setting(
                f"trigger_edge", self.trig_edge_drop.currentText()
            )
        )
        self.trig_edge_drop.setCurrentText(str(self.settings[f"trigger_edge"]))
        #
        self.trig_z_label = QLabel("Ext. Trigger Zin:")
        self.trig_z_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_z_drop = QComboBox()
        self.trig_z_drop.addItems(["50 Ohms", "Hi-Z"])
        self.trig_z_drop.currentIndexChanged.connect(
            lambda: self.update_setting(f"ext_trig_Zin", self.trig_z_drop.currentText())
        )
        self.trig_z_drop.setCurrentText(str(self.settings[f"ext_trig_Zin"]))
        #
        self.trig_lev_label = QLabel("Ext Trig Level (V):")
        self.trig_lev_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.trig_lev_edit = QDoubleSpinBox()
        self.trig_lev_edit.editingFinished.connect(
            lambda: self.update_setting("trigger_level", self.trig_lev_edit.text())
        )
        self.trig_lev_edit.setDecimals(3)
        self.trig_lev_edit.setSingleStep(0.05)
        if hasattr(scpi_instr, "ExternalTriggerThreshold"):
            self.trig_lev_edit.setRange(
                -scpi_instr.ExternalTriggerThreshold,
                scpi_instr.ExternalTriggerThreshold,
            )
        self.trig_lev_edit.setValue(float(self.settings["trigger_level"]))
        #
        self.single_trig_but = QPushButton()
        self.single_trig_but.setText("Single Trigger")
        self.single_trig_but.setIcon(
            QIcon(
                (
                    QPixmap(
                        pkg_resources.resource_filename(
                            "hardware_control", "DelayGenerator/graphics/pulse.png"
                        )
                    )
                )
            )
        )
        self.single_trig_but.setCheckable(False)
        self.single_trig_but.clicked.connect(lambda: self.command("single_trigger"))
        self.single_trig_but.setEnabled(self.trig_mode_drop.currentText() == "Single")
        #
        self.pulse_label = QLabel("Pulses per Burst:")
        self.pulse_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.pulse_edit = QSpinBox()
        self.pulse_edit.editingFinished.connect(
            lambda: self.update_setting("pulses_per_burst", self.pulse_edit.text())
        )
        if hasattr(scpi_instr, "PulsesPerBurst"):
            self.pulse_edit.setRange(2, scpi_instr.PulsesPerBurst)
        self.pulse_edit.setValue(int(self.settings["pulses_per_burst"]))
        #
        self.period_label = QLabel("Triggers per Burst:")
        self.period_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.period_edit = QSpinBox()
        self.period_edit.setMinimum(1)
        self.period_edit.editingFinished.connect(
            lambda: self.update_setting("trigger_period", self.period_edit.text())
        )
        self.period_edit.setSingleStep(1)
        self.period_edit.setValue(int(self.settings["trigger_period"]))
        #
        self.write_label = QLabel("Command: ")
        self.write_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        self.write_edit = QLineEdit()
        self.write_edit.editingFinished.connect(
            lambda: self.update_setting("direct_command", self.write_edit.text())
        )
        self.write_edit.setText(self.settings["direct_command"])
        #
        self.write_but = QPushButton()
        self.write_but.setText("Write")
        self.write_but.setCheckable(False)
        self.write_but.clicked.connect(
            lambda: self.command(self.settings["direct_command"])
        )
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.trig_mode_label, 0, 0)
        self.master_layout.addWidget(self.trig_mode_drop, 0, 1)
        self.master_layout.addWidget(self.trig_z_label, 0, 2)
        self.master_layout.addWidget(self.trig_z_drop, 0, 3)

        self.master_layout.addWidget(self.trig_edge_label, 1, 0)
        self.master_layout.addWidget(self.trig_edge_drop, 1, 1)
        self.master_layout.addWidget(self.trig_lev_label, 1, 2)
        self.master_layout.addWidget(self.trig_lev_edit, 1, 3)

        self.master_layout.addWidget(self.single_trig_but, 2, 3)

        self.master_layout.addWidget(self.pulse_label, 3, 0)
        self.master_layout.addWidget(self.pulse_edit, 3, 1)

        self.master_layout.addWidget(self.period_label, 3, 2)
        self.master_layout.addWidget(self.period_edit, 3, 3)

        self.master_layout.addWidget(self.write_label, 4, 0)
        self.master_layout.addWidget(self.write_edit, 4, 1)

        self.master_layout.addWidget(self.write_but, 4, 3)
        #
        self.setLayout(self.master_layout)

        # Write state to scope - synch scope with GUI
        self.send_state()

    def enableDisableWidgets(self, setting: str, value: str):

        if setting == "trigger_mode":
            if value == "Single":
                self.single_trig_but.setEnabled(True)
            else:
                self.single_trig_but.setEnabled(False)

    def default_state(self):
        """Create the defualt state variable"""

        dflt = {}

        dflt["trigger_mode"] = "INT"
        dflt["trigger_edge"] = "POS"
        dflt["ext_trig_Zin"] = "HiZ"
        dflt["burst_count"] = "2"
        dflt["burst_period"] = "4"
        dflt["direct_command"] = ""
        dflt["pulses_per_burst"] = "2"
        dflt["trigger_period"] = "4"
        dflt["trigger_level"] = "0"
        return dflt
