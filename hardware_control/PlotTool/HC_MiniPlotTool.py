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

plt.ioff()

import logging

logger = logging.getLogger(__name__)


class HC_MiniPlotTool(QWidget):
    """A single matplotlib figure"""

    def __init__(
        self, window, name="Mini Plot", fixed_width=100, fixed_height=100, active=True
    ):
        super().__init__()

        self.app = window.app

        self.normalize = False
        self.autoscale = True

        self.fig, self.axes = plt.subplots()
        self.plot = FigureCanvas(self.fig)
        self.plot.setMaximumWidth(fixed_width)
        self.plot.setMaximumHeight(fixed_height)
        # setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.plot)

        self.setLayout(self.vbox)

        self.plot_set = None

        self.interval = 1000
        self.active = active

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        if self.active:
            self.update_timer.start(self.interval)

    def set_dataset(self, set_name: str):

        self.plot_set = set_name

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

        # for k, v in self.data.items():
        #     myX = np.array([x[0] for x in v])
        #     myY = np.array([x[1] for x in v])
        #     if self.normalize and len(myY) and myY.max() > 0:
        #         myY = myY / myY.max()
        #     self.axes.plot_date(
        #         epoch2num(myX), myY, "o-", label=k, tz="America/Los_Angeles"
        #     )
        self.axes.set_ylim([0, 10])
        self.plot.draw()
