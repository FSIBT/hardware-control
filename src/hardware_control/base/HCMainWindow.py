import sys
import json
import logging
import os
import signal
from sys import platform
from typing import Any

from PyQt6.QtWidgets import (
    QMainWindow,
    QFileDialog,
)
from PyQt6.QtGui import QAction, QCursor

from .App import App
from .remote_access_gui import RemoteAccessIndicator, RemoteAccessPopup

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

    def __init__(self, app: App | None = None, dummy: bool = False):
        if app is None:
            app = App(dummy=dummy)
        self.app = app

        super().__init__()

        self.remote_access_indicator = None
        self.remote_access_popup = RemoteAccessPopup(self.app, self)

        # Make the main window object into an app class variable
        # This allows access to the main window through the app object
        self.app.main_window = self

        self.add_menu()

        self.app.aboutToQuit.connect(self.close)
        signal.signal(signal.SIGINT, self.ctrl_c)

    def ctrl_c(self, signum: int, frame: Any) -> None:
        "Close the app via Ctrl-C."
        self.close()
        sys.exit(0)

    def close(self) -> None:
        """Close the app."""
        self.app.close()

    def setStatusBar(self, statusbar) -> None:
        """Set the status bar and show the remote access mode in it."""
        super().setStatusBar(statusbar)
        if statusbar is not None:
            self._add_remote_access_indicator(statusbar)

    def statusBar(self):
        """Return the status bar, which shows the remote access mode."""
        statusbar = super().statusBar()
        self._add_remote_access_indicator(statusbar)
        return statusbar

    def _add_remote_access_indicator(self, statusbar) -> None:
        """Add the indicator, which only exists if the program uses a status bar."""
        indicator = self.remote_access_indicator
        if indicator is not None and indicator.parent() is statusbar:
            return
        self.remote_access_indicator = RemoteAccessIndicator(self.app, statusbar)
        statusbar.addPermanentWidget(self.remote_access_indicator)

    def show_remote_access(self) -> None:
        """Open the popup to change the remote access settings."""
        self.remote_access_popup.show_at(QCursor.pos())

    def add_menu(self) -> None:
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

        # Remote access menu
        self.remote_menu = self.bar.addMenu("Remote Access")
        self.remote_access_act = QAction("Settings...", self)
        self.remote_access_act.triggered.connect(self.show_remote_access)
        self.remote_menu.addAction(self.remote_access_act)

    def _process_file_menu(self, q: QAction) -> None:
        if q.text() == "Save Instrument States":
            filename = ""

            # Use file dialog to get save location
            dlg = QFileDialog()
            name_tuple = dlg.getSaveFileName()
            filename = name_tuple[0]
            if not filename:  # If cancel button was hit, name will be null
                return

            self.app.save_settings(filename)

        elif q.text() == "Save Data":
            self.save_all()

        elif q.text() == "Exit" or q.text() == "Close Window":
            self.close()
            sys.exit(0)
        else:
            logger.error("function not supported")

    def save_all(self) -> None:
        """Save all datasets to a file, specified by a file dialog"""

        filename = ""

        # Use file dialog to get save location
        dlg = QFileDialog()
        name_tuple = dlg.getSaveFileName()
        filename = name_tuple[0]
        if not filename:  # If cancel button was hit, name will be null
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
