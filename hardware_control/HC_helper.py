from collections import defaultdict, deque
import datetime
import pkg_resources
import hashlib
import sys
import time

from PyQt5 import QtCore
from PyQt5.QtCore import QThread, QSize
from PyQt5.QtGui import QIcon, QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QSizePolicy,
    QPushButton,
    QLabel,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtSvg import QSvgWidget

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.dates import epoch2num
import numpy as np


class HC_OnOff(QPushButton):
    """An On/Off button with a nice icon for on/off

    Takes two functions that will be called when turning on/off
    starts in an unkown state if not defined otherwise

    if f_off is None: assume that f_on is a signal that can emit a boolian.
    """

    def __init__(self, f_on, f_off=None):
        super().__init__()
        self.setCheckable(True)

        self.onText = "On"
        self.offText = "Off"
        self.unkownText = "status unkown"

        self.onIcon = QIcon(
            pkg_resources.resource_filename(
                "hardware_control", "icons/button-power-on.svg"
            )
        )
        self.offIcon = QIcon(
            pkg_resources.resource_filename(
                "hardware_control", "icons/button-power-off.svg"
            )
        )
        self.unkownIcon = QIcon(
            pkg_resources.resource_filename(
                "hardware_control", "icons/button-power-unkown.svg"
            )
        )

        self.f_on = f_on
        self.f_off = f_off
        self.clicked.connect(self.click)

        self.setText(self.unkownText)
        self.setIcon(self.unkownIcon)
        self.setIconSize(QtCore.QSize(30, 30))

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def click(self):
        # we need a 'not' here since the button internally already
        # changed state at this point
        if not self.isChecked():
            if self.f_off:
                self.f_off()
            else:
                self.f_on.emit(False)
            self.set_icon_off()
        else:
            if self.f_off:
                self.f_on()
            else:
                self.f_on.emit(True)
            self.set_icon_on()

    def on(self):
        if self.f_off:
            self.f_on()
        else:
            self.f_on.emit(True)
        self.set_icon_on()

    def set_icon_on(self):
        """Just set the icon to on. Useful during startup"""
        self.setChecked(True)
        self.setIcon(self.onIcon)
        self.setText(self.onText)

    def off(self):
        if self.f_off:
            self.f_off()
        else:
            self.f_on.emit(False)
        self.set_icon_off()

    def set_icon_off(self):
        """Just set the icon to off. Useful during startup"""
        self.setChecked(False)
        self.setIcon(self.offIcon)
        self.setText(self.offText)

    def isOn(self):
        return self.isChecked()


class HC_OnOffIndicator(QSvgWidget):
    """An On/Off indicator

    Listens to signals for on/off and shows a green or red light with a tooltip for mouse-over events.

    starts in an unkown state (both lights off)"""

    def __init__(self, name):
        self.name = name
        self.onIcon = pkg_resources.resource_filename(
            "hardware_control", "icons/on-off-indicator-on.svg"
        )
        self.offIcon = pkg_resources.resource_filename(
            "hardware_control", "icons/on-off-indicator-off.svg"
        )
        self.unkownIcon = pkg_resources.resource_filename(
            "hardware_control", "icons/on-off-indicator-unkown.svg"
        )

        super().__init__(self.unkownIcon)

        self.setMouseTracking(True)
        self.setToolTip(name)

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def sizeHint(self):
        return QSize(10, 20)

    def on(self):
        self.renderer().load(self.onIcon)

    def off(self):
        self.renderer().load(self.offIcon)

    def set(self, status):
        if status:
            self.on()
        else:
            self.off()


class HC_FixedLabel(QLabel):
    """A QLabel that fixes its width to the initial string"""

    def __init__(self, label, color=None):
        super().__init__(label)

        font = QFont()
        font.setPointSize(18)
        font.setBold(False)
        self.setFont(font)

        fm = QFontMetrics(self.font())
        self.setFixedWidth(fm.width(self.text()))

        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if color is not None:
            self.setStyleSheet(
                f"color: white;background-color:{color}; padding: 5px;border: 1px solid black;"
            )


class HC_FigureTab(QWidget):
    """A single matplotlib figure"""

    def __init__(self, parent=None, active=True):
        super().__init__()

        self.normalize = False
        self.autoscale = True

        self.fig, self.axes = plt.subplots()
        self.plot = FigureCanvas(self.fig)
        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav = NavigationToolbar(self.plot, self)
        self.nav.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # custom toolbar
        self.controls = QHBoxLayout()
        self.normalizebutton = QPushButton("normalize")
        self.normalizebutton.clicked.connect(self.toggle_normalize)
        self.normalizebutton.setCheckable(True)
        self.autoscalebutton = QPushButton("autoscale")
        self.autoscalebutton.clicked.connect(self.toggle_autoscale)
        self.autoscalebutton.setCheckable(True)
        self.autoscalebutton.setChecked(True)
        self.controls.addWidget(self.normalizebutton)
        self.controls.addWidget(self.autoscalebutton)
        self.controls.addStretch(1)

        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.controls)
        self.vbox.addWidget(self.nav)
        self.vbox.addWidget(self.plot)
        self.vbox.addSpacing(50)

        self.setLayout(self.vbox)

        self.elements_and_name = []
        self.data = defaultdict(deque)

        self.interval = 1000
        self.active = active

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.add_data)

        # always get data
        if self.active:
            self.timer.start(self.interval)

    def add_element(self, element, name):
        self.elements_and_name.append((element, name))

    def add_data(self):
        t = time.time()
        for e, n in self.elements_and_name:
            self.data[n].append([t, getattr(e, n)])

        # only save the last 10000 data points
        for k, v in self.data.items():
            while len(v) > 10000:
                v.popleft()

    def toggle_autoscale(self):
        self.autoscale = not self.autoscale

    def toggle_normalize(self):
        self.normalize = not self.normalize

    def update(self):
        xleft, xright = self.axes.get_xlim()
        ybottom, ytop = self.axes.get_ylim()
        self.axes.clear()
        self.axes.set_xlabel("Time")
        for k, v in self.data.items():
            myX = np.array([x[0] for x in v])
            myY = np.array([x[1] for x in v])
            if self.normalize and len(myY) and myY.max() > 0:
                myY = myY / myY.max()
            self.axes.plot_date(
                epoch2num(myX), myY, "o-", label=k, tz="America/Los_Angeles"
            )
        self.axes.legend(loc="best")
        if not self.autoscale:
            self.axes.set_xlim([xleft, xright])
            self.axes.set_ylim([ybottom, ytop])
        self.plot.draw()
