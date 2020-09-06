#!/usr/bin/env python3
"""hardware_control-control to control the hardware_control test stand

Usage:
  hardware_control-control [--dummy] [--no-HV-limit] [--set-voltage <kV>]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand

  --no-HV-limit        don't restrict HV power supply to 40 kV min
  --set-voltage <kV>   initial setpoint for the HV [default: 0]
"""

import faulthandler
import sys
from pathlib import Path

import appdirs
from docopt import docopt
import pyvisa

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
    QWidget,
    QAction,
)

import hardware_control.backends as hc_back
import hardware_control.gui as hc

faulthandler.enable()

commands = docopt(__doc__)
dummy = commands["--dummy"]
HVLIMIT = commands["--no-HV-limit"]
HVSETPOINT = float(commands["--set-voltage"])

dirs = appdirs.AppDirs("hardware_control")
appname = "HC_control"
appauthor = "hardware_control"
CACHEDIR = Path(appdirs.user_cache_dir(appname, appauthor)) / "tabs"
if not CACHEDIR.is_dir():
    CACHEDIR.mkdir(parents=True)


class App(QMainWindow):
    """The main window"""

    prepare_shutdown = pyqtSignal()

    def __init__(self, dummy=False, app=None):
        super().__init__()
        self.app = app
        self.scan_time = 2  # seconds

        # set up the window
        self.dummy = dummy

        self.setWindowTitle("hardware_control Controls")
        if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
            font = self.font()
            font.setPointSize(2 * font.pointSize())
            self.setFont(font)

        # file menue
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        self.tab_menu = self.menu.addMenu("Tabs")
        self.help_menu = self.menu.addMenu("Help")

        if sys.platform == "win32":
            QIcon.setThemeSearchPaths([r"c:\Program Files\Git\usr\share\icons"])
        QIcon.setThemeName("Adwaita")

        # QGroupBox;
        scope_com = hc_back.Keysight_4000X("192.168.0.14")
        self.scope = hc.Oscilloscope(app, scope_com, self.dummy)

        quitButton = QAction(QIcon.fromTheme("application-exit"), "Exit", self)
        quitButton.setShortcut("Ctrl+Q")
        quitButton.setStatusTip("Quit")
        quitButton.triggered.connect(self.close)
        self.file_menu.addAction(quitButton)

        aboutButton = QAction(QIcon.fromTheme("help-about"), "About", self)
        aboutButton.setStatusTip("About")
        aboutButton.triggered.connect(self.about)
        self.help_menu.addAction(aboutButton)

        self.main_widget = QWidget(self)
        self.main_window = QVBoxLayout()

        self.statusbar = QHBoxLayout()
        self.main_window.addLayout(self.statusbar)

        self.tabs = QtWidgets.QTabWidget()

        self.main_window.addWidget(self.tabs)

        self.rm = pyvisa.ResourceManager()

        self.plot = hc.FigureTab()

        self.plotHV = hc.FigureTab()

        self.controller = QWidget()

        self.logfiler = hc.LogPlot()

        self.tabs.addTab(self.logfiler, "Logfile")

        self.tabs.currentChanged.connect(self.tabchanged)

        self.main_widget.setLayout(self.main_window)
        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)

        self.timer = QtCore.QTimer(self)

        self.show()

    def tabchanged(self, i):
        self.timer.stop()
        try:
            self.timer.timeout.disconnect()
        except TypeError:
            pass

        if self.tabs.tabText(i) == "Getter Plot":
            self.timer.timeout.connect(self.plot.update)
            self.plot.update()
            self.timer.start(1000)
        elif self.tabs.tabText(i) == "HV Plot":
            self.timer.timeout.connect(self.plotHV.update)
            self.plotHV.update()
            self.timer.start(1000)

    def close_connections(self):
        # send signal to threads
        self.prepare_shutdown.emit()

        self.rm.close()

    def about(self):
        pyversion = ".".join([str(i) for i in sys.version_info])
        QMessageBox.about(
            self,
            "About",
            "hardware control\n\n"
            + f"python-version: {pyversion}\n"
            + f"hardware_control-version: {hardware_control.__version__}",
        )


if __name__ == "__main__":
    app = QApplication([])
    ex = hc.App(dummy, app)
    app.aboutToQuit.connect(ex.close_connections)
    sys.exit(app.exec_())

# Local Variables:
# mode: python
# coding: utf-8
# End:
