from collections import defaultdict, deque
import json
import logging
import pkg_resources
import time

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

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.dates import epoch2num
import numpy as np

# needed to get plots work
plt.ioff()

logger = logging.getLogger(__name__)

mtpl_logger = logging.getLogger("matplot")
mtpl_logger.setLevel("ERROR")


class HC_PlotBase(QWidget):
    """Base class for plotting widgets to display measured data."""

    def __init__(
        self,
        window,
        name="",
        width=500,
        height=500,
        active=True,
        tz="America/Los_Angeles",
        dpi=100,
    ):
        super().__init__()

        self.app = window.app
        self.normalize = False
        self.autoscale = True
        self.tz = tz
        self.dpi = dpi
        self.fmt = "o-"

        self.plot_set = None

        self.fig = plt.figure(
            figsize=(width / self.dpi, height / self.dpi), dpi=self.dpi
        )
        self.plot = FigureCanvas(self.fig)

        self.interval = 1000
        self.active = active

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        if self.active:
            self.update_timer.start(self.interval)

    def set_dataset(self, set_name: str):
        self.plot_set = set_name

    def toggle_autoscale(self):
        self.autoscale = not self.autoscale

    def toggle_normalize(self):
        self.normalize = not self.normalize

    def update(self):
        """Update the plot with new data.

        handels autoscale and normalize and plots the data.

        Should be called via super() from the class that inherits from
        HC_PlotBase. self.plot.draw() also needs to be called.
        """

        # Return if nothing set
        if self.plot_set is None:
            return

        # Check that set exists
        if self.plot_set not in self.app.data_sets:
            return

        # Check that is a function of time
        if "time:time" not in self.app.data_sets[self.plot_set].data:
            return

        xleft, xright = self.axes.get_xlim()
        ybottom, ytop = self.axes.get_ylim()

        self.axes.clear()
        for key in self.app.data_sets[self.plot_set].data:
            if key == "time:time":
                continue
            try:

                arrs = self.app.data_sets[self.plot_set].get_corresponding_arrays(
                    ["time:time", key], True
                )
                y_values = np.array(arrs[key])
                if self.normalize:
                    mymax = np.abs(y_values).max()
                    if mymax > 0:
                        y_values /= mymax

                # Get channel name
                if key in self.app.data_sets[self.plot_set].channel_names:
                    label_name = self.app.data_sets[self.plot_set].channel_names[key]
                else:
                    label_name = key

                self.axes.plot_date(
                    epoch2num(np.array(arrs["time:time"])),
                    y_values,
                    self.fmt,
                    label=label_name,
                    tz=self.tz,
                    linewidth=self.linewidth,
                )
            except:
                logger.debug(f"Failed to plot Y-data", exc_info=True)

        if not self.autoscale:
            self.axes.set_xlim([xleft, xright])
            self.axes.set_ylim([ybottom, ytop])


class HC_PlotTool(HC_PlotBase):
    """A single matplotlib figure.

    with a normalize and autoscale button.
    """

    def __init__(self, window, name="Plot Tool", **kwargs):
        super().__init__(window, name=name, **kwargs)

        self.axes = self.fig.add_subplot()

        self.linewidth = 1

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

    def update(self):
        super().update()

        self.axes.set_xlabel("Time (s)")
        self.axes.legend(loc="best")
        self.axes.grid(True)
        plt.locator_params(axis="y", nbins=6)
        self.plot.draw()


class HC_MiniPlotTool(HC_PlotBase):
    """A minimized matplotlib figure.

    No axes, no lables, just the data in a small window that can be included in a status bar for example.
    """

    def __init__(self, window, name="Mini Plot", width=100, height=100, **kwargs):
        super().__init__(window, name=name, **kwargs)

        self.axes = self.fig.add_axes([0, 0, 1, 1])
        self.axes.axis("off")
        self.plot.setMaximumWidth(width)
        self.plot.setMaximumHeight(height)

        self.fmt = "-"
        self.linewidth = 0.25

        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.plot)

        self.setLayout(self.vbox)

    def update(self):
        super().update()

        self.axes.axis("off")
        self.axes.grid(True)
        self.plot.draw()
