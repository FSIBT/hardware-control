"""
.. image:: /images/widgets/plot.png
"""

import logging
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QWidget,
    QMenu,
    QSizePolicy,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QComboBox,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
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
        self.autoscale_X = True
        self.autoscale_Y = True
        self.fmt = "o-"
        # name of the dataset
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

        # show data source yes/no within a dataset
        self.data_enabled = {}

        # used in self.update()
        self.ax_1_labels = []
        self.ax_2_labels = []
        self.plot_obj_lst = []

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

        if self.plot_set not in self.app.data_sets.keys():
            logger.error(f"{self.plot_set} dataset not in app.")
            return
        dataset = self.app.data_sets[self.plot_set]
        self.data_enabled = {}
        for inst, parameter, _ in dataset.instruments:
            key = f"{inst}:{parameter}"
            self.data_enabled[key] = True

    def toggle_autoscale_X(self):
        """Toggle the autoscale function.

        The autoscale function will automatically adjust the x axes to fit the
        data. This function toggles the autoscale function on and off.
        """
        self.autoscale_X = not self.autoscale_X

    def toggle_autoscale_Y(self):
        """Toggle the autoscale function.

        The autoscale function will automatically adjust the y axes to fit the
        data. This function toggles the autoscale function on and off.
        """
        self.autoscale_Y = not self.autoscale_Y

    def toggle_normalize(self):
        """Toggle the normalize function.

        The normalize function will automatically normalize the displayed data to
        have a maximum value of 1. This allows parameters of greatly different
        magnitudes to be viewed easily on the same chart. This function toggles
        the normalize function on and off.
        """
        self.normalize = not self.normalize

    def toggle_data(self, key):
        """Toggle the visibility of a data source."""
        if not key in self.data_enabled:
            logger.error(f"{key} not present in current dataset {self.plot_set}")
            return
        self.data_enabled[key] = not self.data_enabled[key]

    def select_all_data(self):
        """Select all data sources."""
        for key in self.data_enabled.keys():
            self.data_enabled[key] = True

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
            logger.error(f"Unkown data set {self.plot_set} in {self.plot_set}.")
            return

        dataset = self.app.data_sets[self.plot_set]

        if not self.autoscale_X:
            # remember window position
            xleft, xright = self.axes.get_xlim()

        if not self.autoscale_Y:
            # remember window position
            ybottom, ytop = self.axes.get_ylim()
            ybottom2, ytop2 = self.axes_2.get_ylim()

        for ax in self.ax_lst:
            ax.clear()

        self.ax_1_labels = []
        self.ax_2_labels = []
        self.plot_obj_lst = []
        for idx, instrument_tup in enumerate(dataset.instruments):
            key = f"{instrument_tup[0]}:{instrument_tup[1]}"

            if key not in self.data_enabled:
                logger.error(f"{key} not in current data set {self.plot_set}.")
                continue
            if not self.data_enabled[key]:
                continue

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

        if not self.autoscale_X:
            # reset to old position
            self.axes.set_xlim([xleft, xright])

        if not self.autoscale_Y:
            self.axes.set_ylim([ybottom, ytop])
            self.axes_2.set_ylim([ybottom2, ytop2])

        # Label axes if two axes are in use
        if len(self.ax_2_labels) != 0:
            self.ax_1_labels = ", ".join(self.ax_1_labels)
            self.ax_2_labels = ", ".join(self.ax_2_labels)
            self.axes.set_ylabel(self.ax_1_labels, labelpad=13)
            self.axes_2.set_ylabel(self.ax_2_labels, rotation=270, labelpad=19)
            self.axes_2.yaxis.set_label_position("right")
            self.axes_2.yaxis.tick_right()
        else:
            self.axes_2.get_yaxis().set_ticks([])


class PlotTool(PlotBase):
    """A single matplotlib figure with normalize and autoscale buttons."""

    def __init__(
        self,
        app,
        name: str = "Plot Tool",
        skip_datasets: Optional[list[str]] = None,
        **kwargs,
    ) -> None:
        super().__init__(app, name=name, **kwargs)

        self.axes = self.fig.add_subplot()
        self.axes_2 = self.axes.twinx()
        self.ax_lst = [self.axes, self.axes_2]

        self.skip_datasets = [] if skip_datasets is None else skip_datasets

        self.linewidth = 1

        self.plot.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.nav = NavigationToolbar(self.plot, self)
        self.nav.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # custom toolbar
        self.normalizebutton = QPushButton("normalize")
        self.normalizebutton.clicked.connect(self.toggle_normalize)
        self.normalizebutton.setCheckable(True)
        self.autoscaleXbutton = QPushButton("autoscale X")
        self.autoscaleXbutton.clicked.connect(self.toggle_autoscale_X)
        self.autoscaleXbutton.setCheckable(True)
        self.autoscaleXbutton.setChecked(True)
        self.autoscaleYbutton = QPushButton("autoscale Y")
        self.autoscaleYbutton.clicked.connect(self.toggle_autoscale_Y)
        self.autoscaleYbutton.setCheckable(True)
        self.autoscaleYbutton.setChecked(True)
        self.select_set_label = QLabel("Dataset:")
        self.select_set_drop = QComboBox()
        self.select_set_drop.addItems(
            x for x in app.data_sets if x not in self.skip_datasets
        )
        self.select_set_drop.currentIndexChanged.connect(self.selector_changed)

        # Add button for selecting data sources
        self.data_button = QPushButton("Select Data")
        self.data_button.clicked.connect(self.show_data_menu)

        self.controls = QHBoxLayout()
        self.controls.addWidget(self.normalizebutton)
        self.controls.addWidget(self.autoscaleXbutton)
        self.controls.addWidget(self.autoscaleYbutton)
        self.controls.addWidget(self.select_set_label)
        self.controls.addWidget(self.select_set_drop)
        self.controls.addWidget(self.data_button)
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

    def toggle_data(self, key, checked):
        """Toggle the visibility of a data source."""
        super().toggle_data(key)
        self.update_data_button_color()
        self.update()

    def select_all_data(self):
        """Select all data sources."""
        super().select_all_data()
        self.update_data_button_color()
        self.update()

    def show_data_menu(self):
        """Show a menu with checkboxes to select data sources."""
        menu = QMenu(self)
        for key in self.data_enabled.keys():
            dataset = self.app.data_sets[self.plot_set]
            if key in dataset.channel_names:
                name = dataset.channel_names[key]
            else:
                name = key

            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(self.data_enabled[key])
            action.toggled.connect(
                lambda checked, key=key: self.toggle_data(key, checked)
            )
            menu.addAction(action)

        # Add a select all / deselect all button
        select_all_action = QAction("Select All", self)
        select_all_action.triggered.connect(self.select_all_data)
        menu.addAction(select_all_action)

        menu.exec(self.data_button.mapToGlobal(self.data_button.rect().bottomLeft()))

    def update_data_button_color(self):
        """Update the color of the data button based on the selected data sources."""
        if all(self.data_enabled.values()):
            self.data_button.setStyleSheet("")
        else:
            self.data_button.setStyleSheet("background-color: orange")


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
