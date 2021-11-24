"""
    .. image:: /images/widgets/data_widget.png
      :height: 490
      :width: 700
"""
import logging
from os import getcwd
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QAbstractScrollArea,
    QFileDialog,
)

logger = logging.getLogger(__name__)


class DataWidget(QWidget):
    """Display all datasets in the app.

    Shows one dataset and has a drop down menu to switch to other
    datasets defined in the app.

    Also includes a button to clear all data from the selected dataset
    and option to save the dataset.
    """

    def __init__(
        self,
        app,
        name: str = "Data Logger",
    ):

        super().__init__()
        self.app = app
        self.name = name

        self.current_dataset = ""

        # Left dataset selector sidebar
        self.dataset_chooser_label = QLabel("Dataset:")

        self.dataset_chooser_drop = QComboBox()
        self.dataset_chooser_drop.addItems(["----------"])

        self.data_select_layout = QVBoxLayout()
        self.data_select_layout.addWidget(self.dataset_chooser_label)
        self.data_select_layout.addWidget(self.dataset_chooser_drop)
        self.data_select_layout.addStretch()

        # Data Table
        self.table = QTableWidget()
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.table.setRowCount(15)
        self.table.setColumnCount(4)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.save_button = QPushButton()
        self.save_button.setText("Save")
        self.save_button.clicked.connect(self.save_data)

        self.clear_button = QPushButton()
        self.clear_button.setText("Erase Dataset data")
        self.clear_button.clicked.connect(self.erase_dataset_data)

        self.data_disp_box = QGridLayout()
        self.data_disp_box.addWidget(self.table, 0, 0, 1, 4)
        self.data_disp_box.addWidget(self.save_button, 1, 0)
        self.data_disp_box.addWidget(self.clear_button, 1, 3)

        # Host all UIs in a groupbox
        self.data_disp_frame = QGroupBox("Data")
        self.data_disp_frame.setLayout(self.data_disp_box)

        self.update_dataset_chooser()
        self.dataset_chooser_drop.currentIndexChanged.connect(
            lambda: self.set_current_dataset(self.dataset_chooser_drop.currentText())
        )

        self.grid = QHBoxLayout()
        self.grid.addLayout(self.data_select_layout)
        self.grid.addWidget(self.data_disp_frame)
        self.setLayout(self.grid)

        # Add a timer to update the display of the current table
        self.update_table_timer = QTimer(self)
        self.update_table_timer.timeout.connect(self.update_table)
        self.update_table_timer.start(1000)

    def save_data(self):
        """Save the current dataset to a .json, .pickle, .npy, or .txt file."""
        # File options
        file_filter = "JSON File (*.json);; Pickle File (*.pickle);; NPY File (*.npy);; Text File (*.txt)"

        # Open QT file dialog widget with save directory as the current working directory (cwd)
        savefile, __ = QFileDialog.getSaveFileName(
            parent=self,
            directory=getcwd(),
            filter=file_filter,
            initialFilter="Text File (*.txt)",
        )
        file_extension = savefile.split("/")[-1].split(".")[-1]

        # Save file with the Dataset class' "save" method
        self.app.data_sets[self.current_dataset].save(Path(savefile), file_extension)

    def erase_dataset_data(self):
        """Clear all data in the dataset that is currently being viewed."""
        ds_name = self.current_dataset

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Are you sure you want to delete the dataset?")
        msg.setInformativeText(
            f"Continuing will permanently erase all data in Dataset '{ds_name}'."
        )
        msg.setStandardButtons(QMessageBox.No | QMessageBox.Yes)
        buttonReply = msg.exec()

        if buttonReply == QMessageBox.No:
            return

        try:
            self.app.data_sets[self.current_dataset].clear()
        except:
            logger.error("Failed to delete dataset data", exc_info=True)

        self.update_table()

    def set_current_dataset(self, dataset):
        """Change which dataset is currently being viewed."""
        if dataset == "":
            return

        self.table.setRowCount(0)

        logger.debug(f"LoggerTool display dataset set to '{dataset}'")
        self.current_dataset = dataset
        self.dataset_chooser_drop.setCurrentText(self.current_dataset)
        self.update_table()

        # Resize data to fit column contents
        self.table.resizeColumnsToContents()

    def update_table(self):
        """Set up or update the current dataset data table."""
        dataset = self.app.data_sets[self.current_dataset]

        # Set correct number of columns
        self.table.setColumnCount(len(dataset.data))

        # Set correct number of rows
        num_rows = len(dataset)
        self.table.setRowCount(num_rows)

        # Title columns
        header_names = []
        for field in dataset.data:
            # Use custom name if available, otherwise use field name
            if field in dataset.channel_names:
                header_names.append(dataset.channel_names[field])
            else:
                # Apply readable name for time column if not specified
                if field == "time:time":
                    header_names.append("Time")
                    continue

                header_names.append(field)

        self.table.setHorizontalHeaderLabels(header_names)

        # Write indices along vertical
        indeces_str = [str(x) for x in list(range(num_rows))]

        self.table.setVerticalHeaderLabels(indeces_str)

        # Update data in table
        col = 0
        for field in dataset.data:
            for ridx, val in enumerate(dataset.data[field]):
                temp_item = QTableWidgetItem()

                # If value can be converted to a string, do so
                if isinstance(val, (int, float)):
                    temp_item.setText(f"{val:g}")
                elif isinstance(val, bool):
                    temp_item.setText(str(val))
                elif isinstance(val, str):
                    if val in ["None", ""]:
                        temp_item.setText("<offline>")
                    else:
                        temp_item.setText(val)
                elif isinstance(val, list):
                    if len(val) > 0:
                        temp_item.setText(f"[{type(val[0])}*{len(val)}]")
                    else:
                        temp_item.setText("List")
                elif isinstance(val, dict):
                    temp_item.setText(f"Dict * {len(val)}")
                elif val is None:
                    temp_item.setText("<offline>")
                else:
                    temp_item.setText(f"Type={type(val)}")
                self.table.setItem(ridx, col, temp_item)

            col += 1

        # Resize data to fit column contents
        self.table.resizeColumnsToContents()

    def update_dataset_chooser(self):
        """Updated the drop down menu with the list of all datasets."""
        self.dataset_chooser_drop.clear()

        names = list(self.app.data_sets.keys())
        self.dataset_chooser_drop.addItems(names)

        # Select one dataset and display it if none currently displayed
        if len(names) > 0 and self.current_dataset == "":
            self.set_current_dataset(names[-1])
