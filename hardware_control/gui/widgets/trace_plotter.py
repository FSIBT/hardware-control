import json
import pyqtgraph as pg
import numpy as np
from typing import Optional, List

from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QPushButton,
)

import logging

logger = logging.getLogger(__name__)


class TracePlotter(QGroupBox):
    """Widget that displays a constantly refreshing plot of traces.

    Parameters
    ----------
    app : hc.base.App
        App instance to connect display to.
    instrument_name : str
        Instrument instance to connect display to.
    display_name : str
        Widget name shown in the control program
    channels : List
        Channels to display (first channel is 1; up to 4 channels allowed)
    channel_names : Optional[List]
        Names of channels to displayed on the y-axis
    bkg_color : Optional[str]
        Color of plot background
    loading_hooks : Optional[List]
        Hook functions to be executed on trace data before plotting
    """

    def __init__(
        self,
        app,
        instrument_name: str,
        display_name: str,
        channels: List,
        channel_names: Optional[List] = [],
        bkg_color: Optional[str] = "k",
        loading_hooks: Optional[List] = [],
    ):

        super().__init__(display_name)

        self.app = app
        self.instrument = instrument_name
        self.channels = channels
        self.channel_names = channel_names
        self.loading_hooks = loading_hooks

        self.left_min_lst = [1e-20]
        self.left_max_lst = [1.0]
        self.right_min_lst = [1e-20]
        self.right_max_lst = [1.0]

        channel_colors = {
            0: (3, 7, 252),
            1: (252, 3, 3),
            2: (0, 128, 0),
            3: (246, 190, 0),
        }

        # Create pyqtgraph plot widget
        self.display = pg.PlotWidget()
        self.display.show()
        self.display.setBackground(bkg_color)

        # First axis
        self.p1 = self.display.plotItem
        self.p1.showGrid(x=True, y=True)
        self.p1.setMenuEnabled(enableMenu=True)

        # Second axis
        self.p2 = pg.ViewBox()
        if len(self.channels) > 1:
            self.p1.showAxis("right")
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis("right").linkToView(self.p2)
        self.p2.setXLink(self.p1)
        if self.channel_names == []:
            left_label_items = [
                f"channel {idx}" for idx, ch in enumerate(self.channels) if idx % 2 == 0
            ]
            right_label_items = [
                f"channel {idx}" for idx, ch in enumerate(self.channels) if idx % 2 != 0
            ]
        else:
            left_label_items = [
                self.channel_names[idx]
                for idx, ch in enumerate(self.channels)
                if idx % 2 == 0
            ]
            right_label_items = [
                self.channel_names[idx]
                for idx, ch in enumerate(self.channels)
                if idx % 2 != 0
            ]
        left_label = ", ".join(left_label_items)
        self.p1.getAxis("left").setLabel(left_label, units="V", **{"font-size": "14pt"})
        self.p1.getAxis("left").setTextPen(channel_colors[0])
        right_label = ", ".join(right_label_items)
        self.p1.getAxis("right").setLabel(
            right_label, units="V", **{"font-size": "14pt"}
        )
        self.p1.getAxis("right").setTextPen(channel_colors[1])

        # Y-axis range widgets
        self.p1.setYRange(self.left_min_lst[-1], self.left_max_lst[-1])
        self.p2.setYRange(self.right_min_lst[-1], self.right_max_lst[-1])
        # Plot range parameters
        self.left_vmin_label = QLabel("Voltage Min:")
        self.left_vmin = QDoubleSpinBox()
        self.left_vmin.setValue(1e-20)
        self.left_vmax_label = QLabel("Voltage Max:")
        self.left_vmax = QDoubleSpinBox()
        self.left_vmax.setValue(10.0)
        self.right_vmin_label = QLabel("Current Min:")
        self.right_vmin = QDoubleSpinBox()
        self.right_vmin.setValue(1e-20)
        self.right_vmax_label = QLabel("Current Max:")
        self.right_vmax = QDoubleSpinBox()
        self.right_vmax.setValue(10.0)
        for spinbox in [
            self.left_vmin,
            self.left_vmax,
            self.right_vmin,
            self.right_vmax,
        ]:
            spinbox.setMinimum(-np.inf)
            spinbox.setMaximum(np.inf)
            spinbox.setDecimals(5)

        self.range_btn = QPushButton()
        self.range_btn.setText("Set User Ranges")
        self.range_btn.setCheckable(True)
        self.reset_range_btn = QPushButton()
        self.reset_range_btn.setText("Automate Ranges")
        self.reset_range_btn.setCheckable(True)

        self.plot_items = {}
        for idx, channel in enumerate(self.channels):
            self.app.add_hook(
                self.instrument,
                f"CH{channel}_WAVEFORM",
                "post_read_hooks",
                self.create_load_waveform_hook(channel),
            )

            pen = pg.mkPen(
                color=channel_colors[idx], style=QtCore.Qt.SolidLine, width=5
            )
            curve = pg.PlotCurveItem(pen=pen, symbol=None)
            self.plot_items[channel] = curve
            if idx % 2 == 0:
                self.p1.addItem(curve)
            else:
                self.p2.addItem(curve)

        self.updateViews()
        self.p1.vb.sigResized.connect(self.updateViews)

        self.input_layout = QHBoxLayout()
        self.input_layout.addWidget(self.left_vmin_label)
        self.input_layout.addWidget(self.left_vmin)
        self.input_layout.addWidget(self.left_vmax_label)
        self.input_layout.addWidget(self.left_vmax)
        self.input_layout.addWidget(self.right_vmin_label)
        self.input_layout.addWidget(self.right_vmin)
        self.input_layout.addWidget(self.right_vmax_label)
        self.input_layout.addWidget(self.right_vmax)
        self.input_layout.addWidget(self.range_btn)
        self.input_layout.addWidget(self.reset_range_btn)
        self.input_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.display, 0, 0, 5, 30)
        self.master_layout.addLayout(self.input_layout, 6, 0, 1, 10)
        self.setLayout(self.master_layout)

    def updateViews(self):
        """Update display with most recent trace."""
        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())

    def create_load_waveform_hook(self, channel):
        """Create a hook that returns trace info from instrument."""

        def load_waveform_hook(trace_string):
            return self.load_waveform(channel, trace_string)

        return load_waveform_hook

    def load_waveform(self, channel, trace_string):
        """Load waveform from the instrument and plot."""
        if trace_string is None:
            logger.warning(
                f"Scope {self.instrument}: no trace data available for channel {channel}"
            )
            return

        t, wave = json.loads(trace_string)
        self.plot_items[channel].setData(t, wave)

        # Range resizing
        if self.range_btn.isChecked():
            self.user_resize()
        elif self.reset_range_btn.isChecked():
            self.automate_resize(wave, channel)

        for function in self.loading_hooks:
            trace_string = function(self, channel, t, wave)

    def user_resize(self):
        """Resize channel ranges accoridng to user inputs."""
        self.left_min_lst = [float(self.left_vmin.text())]
        self.left_max_lst = [float(self.left_vmax.text())]
        self.right_min_lst = [float(self.right_vmin.text())]
        self.right_max_lst = [float(self.right_vmax.text())]
        self.p1.setYRange(self.left_min_lst[-1], self.left_max_lst[-1])
        self.p2.setYRange(self.right_min_lst[-1], self.right_max_lst[-1])

    def automate_resize(self, wave, channel):
        """Resize according to channel trace min and max."""
        if channel == self.channels[0]:
            self.left_min_lst = [np.min(wave)]
            self.left_max_lst = [np.max(wave)]
            p = self.p1
        else:
            self.right_min_lst = [np.min(wave)]
            self.right_max_lst = [np.max(wave)]
            p = self.p2

        new_min = np.min(wave) - 0.2 * np.abs(np.min(wave))
        new_max = np.max(wave) + 0.2 * np.abs(np.max(wave))
        p.setYRange(new_min, new_max)
