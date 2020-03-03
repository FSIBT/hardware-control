import json
import json

import pkg_resources
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import (
    QPixmap,
    QProgressBar,
    QIcon,
    QApplication,
    QSpacerItem,
    QSizePolicy,
)
from PyQt5.QtWidgets import (
    QGroupBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QGridLayout,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QCheckBox,
    QMessageBox,
)
from hardware_control.base import HC_Instrument


class HC_LoggerTool(HC_Instrument):
    def __init__(self, window, name: str = "Data Logger"):

        super().__init__(window, name)

        self.settings = {}
        self.name = name
        self.app = window.app
        self.ignore = True

        self.allow_edit_data = False

        self.settings = self.default_state()

        # *************************Create GUI************************

        # self.arrow_symbol = QLabel()
        # self.arrow_symbol.setPixmap(QPixmap(pkg_resources.resource_filename("hardware_control", "ScanTool/graphics/arrow.png")))
        # self.arrow_symbol.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        # # ****** DEFINE TEXT BOXES
        # #

        self.data_select_frame = QWidget()
        self.data_select_layout = QGridLayout()
        #
        self.dispgroup_label = QLabel("Logging Group:")
        self.dispgroup_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        #
        self.dispgroup_drop = QComboBox()
        self.dispgroup_drop.addItems(["----------"])
        self.dispgroup_drop.setCurrentText(self.settings["display_group"])
        self.dispgroup_drop.currentIndexChanged.connect(
            lambda: self.set_group(self.dispgroup_drop.currentText())
        )
        #
        self.new_group_button = QPushButton()
        self.new_group_button.setText("New Dataset")
        self.new_group_button.clicked.connect(self.create_new_group)
        #
        self.sidebar_v_spacer = QSpacerItem(
            20, 200, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        #
        self.save_all_button = QPushButton()
        self.save_all_button.setText("Save All Sets")
        self.save_all_button.clicked.connect(self.save_all_data)
        #
        self.data_select_layout.addWidget(self.dispgroup_label, 0, 0)
        self.data_select_layout.addWidget(self.dispgroup_drop, 1, 0)
        self.data_select_layout.addWidget(self.new_group_button, 2, 0)
        self.data_select_layout.addItem(self.sidebar_v_spacer, 3, 0)
        self.data_select_layout.addWidget(self.save_all_button, 4, 0)
        self.data_select_frame.setLayout(self.data_select_layout)

        self.data_disp_frame = QGroupBox("Data")
        #
        self.table = QTableWidget()
        self.table.setRowCount(4)
        self.table.setColumnCount(4)
        self.table.cellChanged.connect(self.data_changed_from_cell)
        #
        self.autosave_check = QCheckBox("Autosave")
        # self.autosave_check.setChecked()
        self.autosave_check.stateChanged.connect(
            lambda: self.autosave_on_off(self.autosave_check.isChecked())
        )
        #
        self.save_interval_label = QLabel("Interval Time (s):")
        self.save_interval_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        #
        self.save_interval_spacer = QSpacerItem(
            150, 40, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        #
        self.save_interval_edit = QLineEdit()
        self.save_interval_edit.editingFinished.connect(
            lambda: self.set_interval(self.save_interval_edit.text())
        )
        # self.save_interval_edit.setText()
        #
        self.save_button = QPushButton()
        self.save_button.setText("Save")
        self.save_button.clicked.connect(self.save_data)
        #
        self.clear_button = QPushButton()
        self.clear_button.setText("Erase Group Data")
        self.clear_button.clicked.connect(self.erase_group_data)
        #
        self.disp_frame_layout = QGridLayout()
        self.disp_frame_layout.addWidget(self.table, 0, 0, 1, 4)
        self.disp_frame_layout.addWidget(self.autosave_check, 1, 0)
        self.disp_frame_layout.addItem(self.save_interval_spacer, 1, 1)
        self.disp_frame_layout.addWidget(self.save_interval_label, 1, 2)
        self.disp_frame_layout.addWidget(self.save_interval_edit, 1, 3)
        self.disp_frame_layout.addWidget(self.save_button, 2, 0)
        self.disp_frame_layout.addWidget(self.clear_button, 2, 3)
        self.data_disp_frame.setLayout(self.disp_frame_layout)

        # ******* DEFINE OVERALL LAYOUT
        #
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.data_select_frame, 0, 0)
        # self.master_layout.addLayout(self.middle_grid, 1, 0, 1, 2)
        # self.master_layout.addLayout(self.progress_grid, 2, 0, 1, 3)
        self.master_layout.addWidget(self.data_disp_frame, 0, 1)
        self.setLayout(self.master_layout)

        # self.update_table_timer = QTimer(self)
        # self.update_table_timer.timeout.connect(self.update_table)
        # self.update_table_timer.start(1000)

        # self.autosave_timer = QTimer(self)
        # self.autosave_timer.timeout.connect(self.exec_autosave)
        # try:
        #     self.autosave_timer.start(1e3*float(self.settings["save_interval"]))
        # except:
        #     self.autosave_timer.start(120*1e3)

    def create_new_group(self):

        self.window.create_new_group()

        self.update_groups()

    def autosave_on_off(self, state: bool):

        try:
            self.window.app.data_sets[self.settings["display_group"]].autosave = state
        except:
            self.window.app.pDebug("ERROR: Failed to set autosave state", True)

    def set_interval(self, t: str):
        """Sets the autosave interval"""

        try:
            self.window.app.data_sets[
                self.settings["display_group"]
            ].autosave_interval = float(t)
            self.window.app.data_sets[
                self.settings["display_group"]
            ].autosave_timer.setInterval(float(t) * 1000)
        except:
            self.window.app.pDebug("ERROR: Failed to set interval time", True)

    def save_data(self):

        self.window.save_data([self.settings["display_group"]])

    def save_all_data(self):

        self.window.save_data([])

    def erase_group_data(self):

        ds_name = self.settings["display_group"]

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("You are about to delete data. Abort?")
        msg.setInformativeText(
            f"Continuing will permanently erase all data in Dataset '{ds_name}'"
        )
        msg.setWindowTitle("Data Erasure Warning")
        # msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ignore | QMessageBox.Abort)
        buttonReply = msg.exec()

        # buttonReply = QMessageBox.warning(self, 'Data Erasure Warning', "You are about to delete unsaved data. Continue?", QMessageBox.Ignore | QMessageBox.Abort, QMessageBox.Abort)
        if buttonReply == QMessageBox.Abort:
            return

        try:
            self.window.app.data_sets[self.settings["display_group"]].data = []
        except:
            self.window.app.pDebug("ERROR: Failed to delete group data", True)

        self.update_table()

    def data_changed_from_cell(self, row: int, col: int):

        # print(f"cell changed @ ({row}, {col}). Value is now {self.table.itemAt(row, col).text()}") #TODO: Finish fixing 'data changed from cell' code
        pass

    def set_group(self, group):

        self.settings["display_group"] = group
        self.dispgroup_drop.setCurrentText(self.settings["display_group"])
        self.update_table()

    def update_table(self):

        try:
            group = self.window.app.data_sets[self.settings["display_group"]]

            # Set correct number of columns
            self.table.setColumnCount(len(group.data))

            # Set correct number of rows
            num_rows = group.len()
            if num_rows != -1:
                self.table.setRowCount(num_rows + 1)
            else:
                return  # TODO: Change this so it shows the fragmented data

            # Title columns
            header_names = []
            for field in group.data:
                header_names.append(field)
            self.table.setHorizontalHeaderLabels(header_names)

            # Write indeces along vertical
            indeces = list(range(num_rows))
            indeces_str = []
            for i in indeces:
                indeces_str.append(str(i))

            self.table.setVerticalHeaderLabels(indeces_str)

            col = 0
            for field in group.data:

                for ridx, val in enumerate(group.data[field]):
                    temp_item = QTableWidgetItem()
                    temp_item.setText((str(val)))
                    self.table.setItem(ridx, col, temp_item)

                col += 1

            self.autosave_check.setChecked(
                self.window.app.data_sets[self.settings["display_group"]].autosave
            )

            self.save_interval_edit.setText(
                str(
                    self.window.app.data_sets[
                        self.settings["display_group"]
                    ].autosave_interval
                )
            )

        except Exception as e:
            self.window.app.pDebug(
                f"ERROR: Exception occured while updating table ({str(e)})", True
            )

    def update_groups(self):

        self.dispgroup_drop.clear()

        # Copy all goup names into dropdown
        names = []
        for key in self.window.app.data_sets:
            names.append(key)
        self.dispgroup_drop.addItems(names)

        # Select one group and display it if none currently displayed
        if len(names) > 0 and self.settings["display_group"] == "":
            self.set_group(names[0])

    #
    # Create a default state object if can't get state from a file
    #
    def default_state(self):

        dflt = {}

        dflt["display_group"] = ""
        # dflt["instrument"] = "----------"
        # dflt["parameter"] = "----------"
        # dflt["action_instrument"] = "----------"
        # dflt["action_parameter"] = "----------"
        # dflt["progress"] = "0"
        # dflt["macro"] = "None"

        return dflt
