import json
import pyqtgraph as pg
import numpy as np
from typing import Optional, List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QGroupBox, QGridLayout, QLabel, QDoubleSpinBox, QPushButton

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

        # Y-axis range parameters
        self.left_min = 1e-20
        self.right_min = 1e-20
        self.left_max = 10.0
        self.right_max = 10.0

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
        right_label = ", ".join(right_label_items)
        self.p1.getAxis("right").setLabel(
            right_label, units="V", **{"font-size": "14pt"}
        )

        # Y-axis range widgets
        self.left_min = 1e-20
        self.left_max = 10.0
        self.right_min = 1e-20
        self.right_max = 10.0
        self.p1.setYRange(self.left_min, self.left_max)
        self.p2.setYRange(self.right_min, self.right_max)
        # Plot range parameters
        self.left_vmin_label = QLabel("Voltage Min")
        self.left_vmin = QDoubleSpinBox()
        self.left_vmin.setValue(1e-20)
        self.left_vmin.setDecimals(5)
        self.left_vmax_label = QLabel("Voltage Max")
        self.left_vmax = QDoubleSpinBox()
        self.left_vmax.setValue(10.0)
        self.left_vmax.setDecimals(5)
        self.right_vmin_label = QLabel("Current Min")
        self.right_vmin = QDoubleSpinBox()
        self.right_vmin.setValue(1e-20)
        self.right_vmin.setDecimals(5)
        self.right_vmax_label = QLabel("Current Max")
        self.right_vmax = QDoubleSpinBox()
        self.right_vmax.setValue(10.0)
        self.right_vmax.setDecimals(5)

        self.range_btn = QPushButton()
        self.range_btn.setText("Set Ranges")
        self.range_btn.setCheckable(True)

        channel_colors = {
            0: (3, 7, 252),
            1: (252, 3, 3),
            2: (0, 128, 0),
            3: (246, 190, 0),
        }

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

        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.display, 0, 0, 5, 20)
        self.master_layout.addWidget(self.left_vmin_label, 6, 0, 1, 1)
        self.master_layout.addWidget(self.left_vmin, 6, 1, 1, 1)
        self.master_layout.addWidget(self.left_vmax_label, 6, 2, 1, 1)
        self.master_layout.addWidget(self.left_vmax, 6, 3, 1, 1)
        self.master_layout.addWidget(self.right_vmin_label, 6, 4, 1, 1)
        self.master_layout.addWidget(self.right_vmin, 6, 5, 1, 1)
        self.master_layout.addWidget(self.right_vmax_label, 6, 6, 1, 1)
        self.master_layout.addWidget(self.right_vmax, 6, 7, 1, 1)
        self.master_layout.addWidget(self.range_btn, 6, 8, 1, 1)
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
        for function in self.loading_hooks:
            trace_string = function(trace_string)

        t, wave = json.loads(trace_string)

        self.plot_items[channel].setData(t, wave)

        # Range resizing
        if self.range_btn.isChecked():
            self.left_min = float(self.left_vmin.text())
            self.left_max = float(self.left_vmax.text())
            self.right_min = float(self.right_vmin.text())
            self.right_max = float(self.right_vmax.text())
            self.p1.setYRange(self.left_min, self.left_max)
            self.p2.setYRange(self.right_min, self.right_max)
        else:
            self.resize_range(wave)

        return trace_string

    def resize_range(self, wave):
        """Resize range of an axis if sum of axis min and max change by 100%."""
        for idx, channel in enumerate(self.channels):
            if len(wave) != 0:
                wv_max = np.max(wave)
                wv_min = np.min(wave)
                if idx % 2 == 0:
                    left_max = np.max([self.left_max, wv_max])
                    left_min = np.min([self.left_min, wv_max])
                else:
                    right_max = np.max([self.right_max, wv_max])
                    right_min = np.min([self.right_min, wv_max])

        left_range = self.left_max - self.left_min
        left_diff = np.abs(self.left_min - left_min) + np.abs(self.left_max - left_max)
        right_range = self.right_max - self.right_min
        right_diff = np.abs(self.right_min - right_min) + np.abs(
            self.right_max - right_max
        )

        if left_diff / left_range > 1.0:
            self.p1.setYRange(left_min, left_max)
        if right_diff / right_range > 1.0:
            self.p2.setYRange(right_min, right_max)

        self.left_min = left_min
        self.left_max = left_max
        self.right_min = right_min
        self.right_max = right_max
