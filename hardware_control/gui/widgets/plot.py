import logging

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QSizePolicy,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QComboBox,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.dates import epoch2num
import numpy as np

# needed to get plots work
plt.ioff()

logger = logging.getLogger(__name__)


class PlotBase(QWidget):
    """Base class for plotting widgets to display measured data."""

    def __init__(
        self,
        app,
        name="",
        width=500,
        height=500,
        active=True,
        time_zone="America/Los_Angeles",
        dpi=100,
    ):
        super().__init__()

        self.app = app
        self.name = name
        self.normalize = False
        self.autoscale = True
        self.time_zone = time_zone
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
        """ Specifies which dataset the widget should display

        Parameters
        ----------
        set_name : str
            Name of dataset in hc.App to display
        """
        self.plot_set = set_name

        self.axes.clear()

    def toggle_autoscale(self):
        """ Toggles the autoscale function.

        The autoscale function will automatically adjust the axes to fit the
        data. This function toggles the autoscale function on and off.
        """
        self.autoscale = not self.autoscale

    def toggle_normalize(self):
        """ Toggles the normalize function.

        The normalize function will automatically normalize the displayed data to
        have a maximum value of 1. This allows parameters of greatly different
        magnitudes to be viewed easily on the same chart. This function toggles
        the normalize function on and off.
        """
        self.normalize = not self.normalize

    def update(self):
        """Update the plot with new data.

        handels autoscale and normalize and plots the data.

        Should be called via super() from the class that inherits from
        hc.PlotBase. self.plot.draw() also needs to be called.
        """

        # Return if nothing set
        if self.plot_set is None:
            logger.error(f"No data set given in {self.name}.")
            return

        # Check that set exists
        if self.plot_set not in self.app.data_sets:
            logger.error(f"Unkown data set {self.plot_set} in {self.name}.")
            return

        # Check that is a function of time
        if "time:time" not in self.app.data_sets[self.plot_set].data:
            logger.info(f"Data set {self.plot_set} in {self.name} has no time data.")
            return

        xleft, xright = self.axes.get_xlim()
        ybottom, ytop = self.axes.get_ylim()

        self.axes.clear()
        for key in self.app.data_sets[self.plot_set].data:

            # Skip non-lists
            if not self.app.data_sets[self.plot_set].values_are_list(key):
                continue

            # Skip non-numeric types
            if not self.app.data_sets[self.plot_set].values_are_numeric(key):
                continue

            if key[-4:] == "Misc":
                continue

            if key == "time:time":
                continue

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
                tz=self.time_zone,
                linewidth=self.linewidth,
            )

        if not self.autoscale:
            self.axes.set_xlim([xleft, xright])
            self.axes.set_ylim([ybottom, ytop])


class PlotTool(PlotBase):
    """A single matplotlib figure.

    with a normalize and autoscale button.
    """

    def __init__(self, app, name="Plot Tool", **kwargs):
        super().__init__(app, name=name, **kwargs)

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
        self.select_set_label = QLabel("Dataset:")
        self.select_set_drop = QComboBox()
        self.select_set_drop.addItems([x for x in app.data_sets])
        self.select_set_drop.currentIndexChanged.connect(self.selector_changed)

        self.controls.addWidget(self.normalizebutton)
        self.controls.addWidget(self.autoscalebutton)
        self.controls.addWidget(self.select_set_label)
        self.controls.addWidget(self.select_set_drop)
        self.controls.addStretch(1)

        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.controls)
        self.vbox.addWidget(self.nav)
        self.vbox.addWidget(self.plot)
        self.vbox.addSpacing(50)

        self.setLayout(self.vbox)

    def selector_changed(self):
        """ Is automatically called when the dataset dropdown is changed.

        This function updates the dataset to plot using the current value of the
        dropdown widget.
        """

        current_text = self.select_set_drop.currentText()

        if current_text is not None:
            super().set_dataset(current_text)

    def set_dataset(self, set_name: str):
        """ Sets the dataset in hc.App to plot.

        Parameters
        ----------
        set_name : str
            Name of set in hc.App to plot
        """

        super().set_dataset(set_name)

        self.select_set_drop.clear()
        self.select_set_drop.addItems([x for x in self.app.data_sets])
        self.select_set_drop.setCurrentText(set_name)

    def update(self):
        """ Updates the plot widget with the most recent data.
        """

        super().update()

        self.axes.set_xlabel("Time (s)")
        handles, labels = self.axes.get_legend_handles_labels()
        if len(handles) > 0:
            self.axes.legend(loc="best")
        self.axes.grid(True)
        plt.locator_params(axis="y", nbins=6)
        self.plot.draw()


class MiniPlotTool(PlotBase):
    """A minimized matplotlib figure.

    No axes, no lables, just the data in a small window that can be
    included in a status bar for example.

    """

    def __init__(self, app, name="Mini Plot", width=100, height=100, **kwargs):
        super().__init__(app, name=name, **kwargs)

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
        """ Updates the plot widget with the most recent data.
        """
        super().update()

        self.axes.axis("off")
        self.axes.grid(True)
        self.plot.draw()
