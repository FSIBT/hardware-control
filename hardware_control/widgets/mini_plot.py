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

mtpl_logger = logging.getLogger("matplotlib")
mtpl_logger.setLevel("ERROR")


class HC_MiniPlotTool(QWidget):
    """A single matplotlib figure"""

    def __init__(
        self,
        window,
        name="Mini Plot",
        fixed_width=100,
        fixed_height=100,
        active=True,
        tz="America/Los_Angeles",
    ):
        super().__init__()

        self.app = window.app

        self.tz = tz

        self.normalize = False
        self.autoscale = True

        self.dpi = 300

        self.fig = plt.figure(
            figsize=(fixed_width / self.dpi, fixed_height / self.dpi), dpi=self.dpi
        )
        self.axes = self.fig.add_axes([0, 0, 1, 1])
        self.axes.axis("off")
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
        self.axes.axis("off")
        self.axes.grid(True)
        for key in self.app.data_sets[self.plot_set].data:
            if key == "time:time":
                continue
            try:
                arrs = self.app.data_sets[self.plot_set].get_corresponding_arrays(
                    ["time:time", key], True
                )
                # print(f"{key} -> mini")
                # y_arr = np.array(
                #     [float(yval) for yval in self.app.data_sets[self.plot_set].data[key]]
                # )
                self.axes.plot_date(
                    epoch2num(np.array(arrs["time:time"])),
                    np.array(arrs[key]),
                    "-",
                    label=key,
                    tz="America/Los_Angeles",
                    linewidth=0.25,
                )
            except:
                logger.debug(f"Failed to plot Y-data", exc_info=True)

        self.plot.draw()
