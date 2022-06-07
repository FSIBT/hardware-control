"""
    .. image:: /images/widgets/plot.png
"""
import logging
from typing import Optional, List

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

import numpy as np
import pandas as pd

# needed to get plots work
plt.ioff()

logger = logging.getLogger(__name__)


class PlotBase(QWidget):
    """Base class for plotting widgets to display measured data."""

    def __init__(
        self,
        app,
        name: str = "",
        width: int = 500,
        height: int = 500,
        active_update: bool = True,
        time_zone: str = "America/Los_Angeles",
        dpi: int = 100,
    ):
        super().__init__()

        self.app = app
        self.name = name
        self.active_update = active_update
        self.time_zone = time_zone
        self.dpi = dpi

        # Plotting parameters
        self.normalize = False
        self.autoscale = True
        self.fmt = "o-"
        self.plot_set = None
        self.unused_colors = [
            "b",
            "g",
            "r",
            "c",
            "m",
            "y",
            "k",
            "purple",
            "orange",
            "springgreen",
            "slategray",
            "maroon",
        ]
        self.used_colors = []
        self.param_colors = {}

        # Set up plotting
        self.fig = plt.figure(
            figsize=(width / self.dpi, height / self.dpi), dpi=self.dpi
        )
        self.plot = FigureCanvas(self.fig)

        # Create timer to query instruments
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update)
        if self.active_update:
            self.update_timer.start(self.app.globalRefreshRate)

    def set_dataset(self, dataset_name: str):
        """Specify which dataset the widget should display.

        Parameters
        ----------
        dataset_name : str
            Name of dataset to display
        """
        self.plot_set = dataset_name

        for ax in self.ax_lst:
            ax.clear()

    def toggle_autoscale(self):
        """Toggle the autoscale function.

        The autoscale function will automatically adjust the axes to fit the
        data. This function toggles the autoscale function on and off.
        """
        self.autoscale = not self.autoscale

    def toggle_normalize(self):
        """Toggle the normalize function.

        The normalize function will automatically normalize the displayed data to
        have a maximum value of 1. This allows parameters of greatly different
        magnitudes to be viewed easily on the same chart. This function toggles
        the normalize function on and off.
        """
        self.normalize = not self.normalize

    def update(self):
        """Update the plot with new data.

        Handles autoscaling, normalizaiton, and data plotting.

        Should be called via super() from the class that inherits from
        PlotBase. self.plot.draw() also needs to be called.
        """

        # Return if nothing set
        if self.plot_set is None:
            logger.error(f"No dataset given in {self.name}.")
            return

        # Check that the dataset exists
        if self.plot_set not in self.app.data_sets:
            logger.error(f"Unkown data set {self.plot_set} in {self.name}.")
            return

        dataset = self.app.data_sets[self.plot_set]

        for ax in self.ax_lst:
            ax.clear()

        self.ax_1_labels = []
        self.ax_2_labels = []
        self.plot_obj_lst = []
        for idx, instrument_tup in enumerate(dataset.instruments):
            key = f"{instrument_tup[0]}:{instrument_tup[1]}"
            plot_ax = instrument_tup[2]

            df = dataset.to_pandas(columns=["time:time", key], cleanup=True)
            if df.empty:
                return

            y_values = df[key].to_numpy()
            x_values = pd.to_datetime(df["time:time"], unit="s").dt.tz_localize("UTC")
            x_values = x_values.dt.tz_convert("America/Los_Angeles")

            if self.normalize:
                mymax = np.abs(y_values).max()
                if mymax > 0:
                    y_values = y_values / mymax

            # Get channel name
            if key in dataset.channel_names:
                label_name = dataset.channel_names[key]
            else:
                label_name = key

            if plot_ax == 1:
                ax = self.axes
                self.ax_1_labels.append(label_name)
            elif plot_ax == 2:
                ax = self.axes_2
                self.ax_2_labels.append(label_name)
            else:
                logger.error(
                    f"Plot axis {plot_ax} is invalid. Plot axis must be either 1 or 2."
                )

            if label_name not in self.param_colors.keys():
                if len(self.unused_colors) == 0:
                    self.unused_colors = self.used_colors
                    self.used_colors = []
                self.param_colors[label_name] = self.unused_colors[0]
                self.used_colors.append(self.unused_colors[0])
                self.unused_colors.remove(self.unused_colors[0])

            plot_obj = ax.plot_date(
                x_values.to_numpy(),
                y_values,
                self.fmt,
                color=self.param_colors[label_name],
                label=label_name,
                tz=self.time_zone,
                linewidth=self.linewidth,
            )
            self.plot_obj_lst.append(plot_obj[0])

        if not self.autoscale:
            xleft, xright = ax.get_xlim()
            ybottom, ytop = ax.get_ylim()
            ax.set_xlim([xleft, xright])
            ax.set_ylim([ybottom, ytop])

        # Label axes if two axes are in use
        if len(self.ax_2_labels) != 0:
            self.ax_1_labels = ", ".join(self.ax_1_labels)
            self.ax_2_labels = ", ".join(self.ax_2_labels)
            self.axes.set_ylabel(self.ax_1_labels, labelpad=13)
            self.axes_2.set_ylabel(self.ax_2_labels, rotation=270, labelpad=19)
            self.axes_2.yaxis.tick_right()
        else:
            self.axes_2.get_yaxis().set_ticks([])


class PlotTool(PlotBase):
    """A single matplotlib figure with normalize and autoscale buttons."""

    def __init__(
        self,
        app,
        name: str = "Plot Tool",
        skip_datasets: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(app, name=name, **kwargs)

        self.axes = self.fig.add_subplot()
        self.axes_2 = self.axes.twinx()
        self.ax_lst = [self.axes, self.axes_2]

        self.skip_datasets = [] if skip_datasets is None else skip_datasets

        self.linewidth = 1

        self.plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.nav = NavigationToolbar(self.plot, self)
        self.nav.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # custom toolbar
        self.normalizebutton = QPushButton("normalize")
        self.normalizebutton.clicked.connect(self.toggle_normalize)
        self.normalizebutton.setCheckable(True)
        self.autoscalebutton = QPushButton("autoscale")
        self.autoscalebutton.clicked.connect(self.toggle_autoscale)
        self.autoscalebutton.setCheckable(True)
        self.autoscalebutton.setChecked(True)
        self.select_set_label = QLabel("Dataset:")
        self.select_set_drop = QComboBox()
        self.select_set_drop.addItems(
            x for x in app.data_sets if x not in self.skip_datasets
        )
        self.select_set_drop.currentIndexChanged.connect(self.selector_changed)

        self.controls = QHBoxLayout()
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
        """Update the dataset to plot using the current dataset in the dropdown.

        This function is called automatically when the dataset dropdown is changed.
        """
        current_text = self.select_set_drop.currentText()

        if current_text is not None:
            super().set_dataset(current_text)

    def set_dataset(self, dataset_name: str):
        """Specify which dataset the widget should display.

        Parameters
        ----------
        dataset_name : str
            Name of set in hc.App to plot
        """
        super().set_dataset(dataset_name)

        self.select_set_drop.clear()
        self.select_set_drop.addItems(
            x for x in self.app.data_sets if x not in self.skip_datasets
        )
        self.select_set_drop.setCurrentText(dataset_name)

    def update(self):
        """Update the plot widget with the most recent data."""
        super().update()

        self.axes.set_xlabel("Time (s)")
        labels = [l.get_label() for l in self.plot_obj_lst]
        self.axes.legend(self.plot_obj_lst, labels, loc=0)
        self.axes.grid(True)
        plt.locator_params(axis="y", nbins=6)
        self.plot.draw()


class MiniPlotTool(PlotBase):
    """A no-frills matplotlib figure.

    These objects contain neither axes nor labels. They merely consist of a
    small window that can be included, for example, in a status bar.
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
        """Update the plot widget with the most recent data."""
        super().update()

        self.axes.axis("off")
        self.axes.grid(True)
        self.plot.draw()
