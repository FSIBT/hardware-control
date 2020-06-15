import json
import json

import numpy as np
import pkg_resources
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QWidget,
    QGroupBox,
    QLabel,
    QGridLayout,
    QSizePolicy,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)
from collections import defaultdict, deque
import time

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.dates import epoch2num

import logging

logger = logging.getLogger(__name__)


class HC_PlotTool(QWidget):
    """A single matplotlib figure"""

    def __init__(self, window, name="Plot Window", active=True):
        super().__init__()

        self.app = window.app

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

        self.plot_set = None

        # self.elements_and_name = []
        # self.data = defaultdict(deque)

        self.interval = 1000
        self.active = active

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        if self.active:
            self.update_timer.start(self.interval)

    #     self.timer = QtCore.QTimer(self)
    #     self.timer.timeout.connect(self.add_data)
    #
    #     # always get data
    #     if self.active:
    #         self.timer.start(self.interval)
    #
    # def add_element(self, element, name):
    #     self.elements_and_name.append((element, name))
    #
    # def add_data(self):
    #     t = time.time()
    #     for e, n in self.elements_and_name:
    #         self.data[n].append([t, getattr(e, n)])
    #
    #     # only save the last 10000 data points
    #     for k, v in self.data.items():
    #         while len(v) > 10000:
    #             v.popleft()

    def set_dataset(self, set_name: str):

        self.plot_set = set_name

    def toggle_autoscale(self):
        self.autoscale = not self.autoscale

    def toggle_normalize(self):
        self.normalize = not self.normalize

    def update(self):
        xleft, xright = self.axes.get_xlim()
        ybottom, ytop = self.axes.get_ylim()
        self.axes.clear()
        self.axes.set_xlabel("Time")

    def update(self):

        # Return if nothing set
        if self.plot_set is None:
            return

        # Check that set exists
        if self.plot_set not in self.app.data_sets:
            return

        # Check that is a function of time
        if "time:time" not in self.app.data_sets[self.plot_set].data:
            return

        x_arr = np.array(
            [
                float(tval)
                for tval in self.app.data_sets[self.plot_set].data["time:time"]
            ]
        )

        xleft, xright = self.axes.get_xlim()
        ybottom, ytop = self.axes.get_ylim()

        self.axes.clear()
        self.axes.set_xlabel("Time (s)")
        for key in self.app.data_sets[self.plot_set].data:
            if key == "time:time":
                continue
            y_arr = np.array(
                [float(yval) for yval in self.app.data_sets[self.plot_set].data[key]]
            )
            self.axes.plot_date(
                epoch2num(x_arr), y_arr, "o-", label=key, tz="America/Los_Angeles"
            )
            print(f"{min(y_arr)}, {max(y_arr)}")

        # for k, v in self.data.items():
        #     myX = np.array([x[0] for x in v])
        #     myY = np.array([x[1] for x in v])
        #     if self.normalize and len(myY) and myY.max() > 0:
        #         myY = myY / myY.max()
        #     self.axes.plot_date(
        #         epoch2num(myX), myY, "o-", label=k, tz="America/Los_Angeles"
        #     )
        self.axes.legend(loc="best")
        plt.locator_params(axis="y", nbins=6)
        self.axes.set_ylim([0, 10])
        if not self.autoscale:
            self.axes.set_xlim([xleft, xright])
            self.axes.set_ylim([ybottom, ytop])
        self.plot.draw()
