import sys
import json
import logging
import os
from sys import platform

from PyQt5.QtWidgets import (
    QMainWindow,
    QAction,
    QInputDialog,
    QFileDialog,
)

from .Dataset import Dataset

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, app):

        super().__init__()

        self.app = app
        self.app.main_window = self

        self.add_menu()

    def add_menu(self):

        # self.menuBar() is a function in QMainWindow
        self.bar = self.menuBar()

        # File menu
        self.file_menu = self.bar.addMenu("File")
        self.file_menu.triggered[QAction].connect(self.process_file_menu)

        self.save_state_act = QAction("Save Instrument States", self)
        self.save_state_act.setShortcut("Ctrl+Shift+S")
        self.file_menu.addAction(self.save_state_act)

        self.save_data_act = QAction("Save Data", self)
        self.save_data_act.setShortcut("Ctrl+S")
        self.file_menu.addAction(self.save_data_act)

        self.clear_data_act = QAction("Clear Data", self)
        self.clear_data_act.setShortcut("Ctrl+Shift+K")
        self.file_menu.addAction(self.clear_data_act)

        self.new_group_act = QAction("New Dataset", self)
        self.new_group_act.setShortcut("Ctrl+Shift+N")
        self.file_menu.addAction(self.new_group_act)

        self.file_menu.addSeparator()

        if platform in ["linux", "linux2", "darwin"]:
            self.close_act = QAction("Close Window", self)
            self.close_act.setShortcut("Ctrl+W")
        elif platform == "win32":
            self.close_act = QAction("Exit", self)
            self.close_act.setShortcut("Ctrl+Q")
        self.file_menu.addAction(self.close_act)

        # Instrument Menu
        self.instr_menu = self.bar.addMenu("Instrument")
        self.instr_menu.triggered[QAction].connect(self.process_instr_menu)

        self.sync_from_ui_act = QAction("Sync from UI", self)
        self.instr_menu.addAction(self.sync_from_ui_act)

        self.sync_from_instr_act = QAction("Sync from Instrument", self)
        self.instr_menu.addAction(self.sync_from_instr_act)

        self.sync_from_file_act = QAction("Sync from File", self)
        self.instr_menu.addAction(self.sync_from_file_act)

        self.sync_from_file_act = QAction("Refresh UI", self)
        self.instr_menu.addAction(self.sync_from_file_act)

        self.instr_menu.addSeparator()

        self.print_addresses_act = QAction("Print Addresses", self)
        self.instr_menu.addAction(self.print_addresses_act)

        # Scripting Menu
        self.scripting_menu = self.bar.addMenu("Scripting")
        self.scripting_menu.triggered[QAction].connect(self.process_scripting_menu)

        self.run_command_act = QAction("Run Command", self)
        self.run_command_act.setShortcut("Ctrl+R")
        self.scripting_menu.addAction(self.run_command_act)

    def process_file_menu(self, q):

        if q.text() == "Save Instrument States":

            filename = ""

            # Use file dialog to get save location
            dlg = QFileDialog()
            name_tuple = dlg.getSaveFileName()
            filename = name_tuple[0]
            if not filename:  # If cancel bttonw as hit, name will be null
                return

            self.app.save_all_states(filename)

        elif q.text() == "Save Data":

            self.save_all()

        elif q.text() == "Clear Data":

            for ds_name in self.app.data_sets:
                self.app.data_sets[ds_name].clear()

        elif q.text() == "New Dataset":

            self.create_new_group()

            for inst in self.app.instruments:
                if (
                    inst.name == "Data Logger"
                ):  # TODO: Find resilient way to automatically identify LoggerTool objects to update their group lists
                    inst.update_groups()

        elif q.text() == "Exit" or q.text() == "Close Window":
            self.close()
            sys.exit(0)
        else:
            logger.error("function not supported")

    def process_instr_menu(self, q):

        if q.text() == "Sync from Instrument":

            self.app.backends_to_settings()
            self.app.settings_to_UI()

        elif q.text() == "Sync from UI":

            self.app.settings_to_backends()

        elif q.text() == "Sync from File":

            filename = ""

            # Use file dialog to get save location
            dlg = QFileDialog()
            name_tuple = dlg.getOpenFileName()
            filename = name_tuple[0]
            if not filename:  # If cancel bttonw as hit, name will be null
                return

            self.app.load_state_from_file(filename)

        elif q.text() == "Refresh UI":

            for instr in self.app.instruments:
                instr.settings_to_UI()

        elif q.text() == "Print Addresses":

            print("Instrument Addresses")
            for inst in self.app.instruments:

                try:
                    addr = inst.address
                except Exception:
                    addr = "---"

                if addr == "" or addr is None:
                    addr = "---"

                print(f"\t{inst.name}:\t {addr}")

        else:
            logger.error("function not supported")

    def process_scripting_menu(self, q):
        if q.text() == "Run Command":

            dlg = QInputDialog(self)
            dlg.setInputMode(QInputDialog.TextInput)
            dlg.setLabelText("Command:")
            dlg.resize(500, 100)
            okPressed = dlg.exec_()
            text = dlg.textValue()

            # text, okPressed = QInputDialog.getText(self, "Where am I??", "Command", QLineEdit.Normal)
            if okPressed and text != "":
                self.app.process_external_command(text)
        else:
            logger.error("function not supported")

    def save_all(self):
        """ Save all datasets to a file, specified by a file dialog """

        filename = ""

        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getSaveFileName()
        filename = name_tuple[0]
        if not filename:  # If cancel bttonw as hit, name will be null
            return

        # print(filename)

        all_data = {}

        # Collect all datasets data in one dictionary
        for ds_name in self.app.data_sets:
            set_name = self.app.data_sets[ds_name].name
            all_data[f"{set_name}"] = self.app.data_sets[ds_name].data

        # Add extension if not specified
        ext = os.path.splitext(filename)[-1].lower()
        if ext == "":
            filename = filename + ".json"

        # Write file
        with open(filename, "w", encoding="utf-8") as outfile:
            json.dump(all_data, outfile, ensure_ascii=False, indent=4)

    def save_data(self, dataset_name: str):
        """Saves the data stored in the app's data_sets object. Saves the dataset
        with name specified by 'dataset_name'. If 'sets' is empty string, will save
        all datasets."""

        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getSaveFileName()
        name = name_tuple[0]
        if not name:  # If cancel bttonw as hit, name will be null
            return

        # Use input dialog to get save file type
        save_types = ["JSON", "Pickle", "NPY", "TXT"]
        if self.app is not None:
            for data_format in self.app.additional_save_formats:
                save_types.append(data_format)
        file_type, okay = QInputDialog.getItem(
            self, "Select File Type", "File Type:", save_types, 0, False
        )

        print(f"Save set '{dataset_name}' to file '{name}' with type '{file_type}'")

        if okay and file_type:
            logger.info(f"Saving as {file_type} with name {name}")
            try:
                self.app.data_sets[dataset_name].save(name, file_type)
            except:
                logger.error(
                    f"Failed to find and save dataset with name '{dataset_name}'",
                    exc_info=True,
                )
        else:
            logger.info("Save canceled")

    def create_new_group(self):

        dlg = QInputDialog(self)
        dlg.setInputMode(QInputDialog.TextInput)
        dlg.setLabelText("New dataset name:")
        dlg.resize(500, 100)
        okPressed = dlg.exec_()
        text = dlg.textValue()

        if okPressed and text != "":
            temp_ds = Dataset(text)
            self.app.data_sets[text] = temp_ds
