from PyQt5 import QtCore
from PyQt5.QtWidgets import QLineEdit, QLabel, QGridLayout, QComboBox

from hardware_control.base import HC_Instrument
import logging

logger = logging.getLogger(__name__)


class HC_VariableEditTool(HC_Instrument):
    """A tool which allows the user to edit app variables from the main UI."""

    def __init__(
        self,
        window,
        name: str = "Application Variable Editor",
        vars={"Dynamic": "Value:"},
    ):

        super().__init__(window, name)

        self.vars = vars

        self.settings = {}
        self.name = name
        self.app = window.app
        self.ignore = True

        # *************************Create GUI************************

        self.button_panel = QGridLayout()
        allow_dynamic = True
        row = 0
        for idx, v in enumerate(self.vars):  # Requests dynamic...

            if v == "Dynamic":

                # Prevent duplicate dynamic boxes
                allow_dynamic = False

                # Create macro selection dropdown label
                variable_drop_label = QLabel("Variable:")
                # variable_drop_label.setPixmap(QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/icons/arrow.png")))
                variable_drop_label.setAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

                # Create macro selection dropdown
                self.variable_drop = QComboBox()
                self.variable_drop.addItems(["----------"])
                # variable_drop.setCurrentText(self.settings["parameter"])
                self.variable_drop.currentIndexChanged.connect(
                    lambda: self.select_variable(self.variable_drop.currentText())
                )

                # Create edit box label
                value_edit_label = QLabel(vars[v])
                # variable_drop_label.setPixmap(QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/icons/arrow.png")))
                value_edit_label.setAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

                # Create edit box
                value_edit = QLineEdit()
                value_edit.editingFinished.connect(
                    lambda: self.edit_variable(
                        self.variable_drop.currentText(), value_edit.text()
                    )
                )
                value_edit.setText("")
                value_edit.setMinimumWidth(80)

                self.button_panel.addWidget(variable_drop_label, row, 0)
                self.button_panel.addWidget(self.variable_drop, row, 1)
                self.button_panel.addWidget(value_edit_label, row + 1, 0)
                self.button_panel.addWidget(value_edit, row + 1, 1)
                row += 1

            elif v in [
                x for x in self.window.app.variables
            ]:  # But is a valid macro name....

                # Create edit box label
                value_edit_label = QLabel(vars[v])
                # variable_drop_label.setPixmap(QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/icons/arrow.png")))
                value_edit_label.setAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

                # Create edit box
                value_edit = QLineEdit()
                value_edit.editingFinished.connect(
                    lambda: self.edit_variable(v, value_edit.text())
                )
                value_edit.setText("")
                value_edit.setMinimumWidth(80)

                self.button_panel.addWidget(value_edit_label, row, 0)
                self.button_panel.addWidget(value_edit, row, 1)

            else:

                logger.warning(f"Variable '{v}' does not exist. Ignoring edit line.")
            row += 1

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.button_panel, 0, 0)
        # self.master_layout.addLayout(self.middle_grid, 1, 0, 1, 2)
        # self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 3)
        # self.master_layout.addWidget(self.scan_button, 3, 0)
        self.setLayout(self.master_layout)

    def edit_variable(self, var: str, value: str):
        try:
            self.window.app.variables[var] = value
            logger.debug(f"Setting {var} = '{value}'")
        except Exception:
            logger.debug(f"An exception occurred setting variable {var}")

    def select_variable(self, m: str):
        logger.debug(f"Setting macro to {m}")
        self.settings["variable"] = m

    def update_variables(self):
        self.variable_drop.clear()
        names = []
        for m in self.app.variables:
            names.append(m)
            logger.debug(f"Adding variable: {m}")
        self.variable_drop.addItems(names)

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        dflt["variable"] = "----------"

        return dflt
