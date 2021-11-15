import sys
import json
import logging
import os
from sys import platform
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow,
    QAction,
    QFileDialog,
)

from .App import App

logger = logging.getLogger(__name__)


class HCMainWindow(QMainWindow):
    """Create a QMainWindow with some additional menus unique to hardware control (HC).

    Typically, a new program will inherit from this class.

    Parameters
    ----------
    app :
       The main app that will store all instruments, parameters, commands, etc. This parameter is optional.
    dummy :
       If True, then the app runs in dummy mode. Only used if app is None.

    """

    def __init__(self, app: Optional[App] = None, dummy: bool = False):

        if app is None:
            app = App(dummy=dummy)
        self.app = app

        super().__init__()

        # Make the main window object into an app class variable
        # This allows access to the main window through the app object
        self.app.main_window = self

        self.add_menu()

        self.app.aboutToQuit.connect(self.close)

    def close(self):
        """Close the app."""

        self.app.close()

    def add_menu(self):
        """Add a File menu with an option to exit and save all datasets."""

        # self.menuBar() is a function in QMainWindow
        self.bar = self.menuBar()

        # File menu
        self.file_menu = self.bar.addMenu("File")
        self.file_menu.triggered[QAction].connect(self._process_file_menu)

        self.save_state_act = QAction("Save Instrument States", self)
        self.save_state_act.setShortcut("Ctrl+Shift+S")
        self.file_menu.addAction(self.save_state_act)

        self.save_data_act = QAction("Save Data", self)
        self.save_data_act.setShortcut("Ctrl+S")
        self.file_menu.addAction(self.save_data_act)

        self.file_menu.addSeparator()

        if platform in ["linux", "linux2", "darwin"]:
            self.close_act = QAction("Close Window", self)
            self.close_act.setShortcut("Ctrl+W")
        elif platform == "win32":
            self.close_act = QAction("Exit", self)
            self.close_act.setShortcut("Ctrl+Q")
        self.file_menu.addAction(self.close_act)

    def _process_file_menu(self, q):

        if q.text() == "Save Instrument States":

            filename = ""

            # Use file dialog to get save location
            dlg = QFileDialog()
            name_tuple = dlg.getSaveFileName()
            filename = name_tuple[0]
            if not filename:  # If cancel bttonw as hit, name will be null
                return

            self.app.save_settings(filename)

        elif q.text() == "Save Data":

            self.save_all()

        elif q.text() == "Exit" or q.text() == "Close Window":
            self.close()
            sys.exit(0)
        else:
            logger.error("function not supported")

    def save_all(self):
        """Save all datasets to a file, specified by a file dialog"""

        filename = ""

        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getSaveFileName()
        filename = name_tuple[0]
        if not filename:  # If cancel bttonw as hit, name will be null
            return

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
