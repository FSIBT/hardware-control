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
    channel_names : List
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
        channel_names: List,
        bkg_color: Optional[str] = "w",
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

        # Y-axis channel labels
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
        self.vmin_labs = []
        self.vmax_labs = []
        self.vmins = []
        self.vmaxs = []
        for ch_nm in self.channel_names:
            vmin_label = QLabel(f"{ch_nm} Min (V):")
            vmin = QDoubleSpinBox()
            vmin.setValue(1e-20)
            vmin.setMinimum(-np.inf)
            vmin.setMaximum(np.inf)
            vmin.setDecimals(5)
            vmax_label = QLabel(f"{ch_nm} Max (V):")
            vmax = QDoubleSpinBox()
            vmax.setValue(10.0)
            vmax.setMinimum(-np.inf)
            vmax.setMaximum(np.inf)
            vmax.setDecimals(5)
            self.vmin_labs.append(vmin_label)
            self.vmax_labs.append(vmax_label)
            self.vmins.append(vmin)
            self.vmaxs.append(vmax)
        self.p1.setYRange(self.left_min_lst[-1], self.left_max_lst[-1])
        self.p2.setYRange(self.right_min_lst[-1], self.right_max_lst[-1])

        self.range_btn = QPushButton()
        self.range_btn.setText("Set User Ranges")
        self.range_btn.setCheckable(True)
        self.range_btn.clicked.connect(self.click_range_btn)
        self.reset_range_btn = QPushButton()
        self.reset_range_btn.setText("Automate Ranges")
        self.reset_range_btn.setCheckable(True)
        self.reset_range_btn.clicked.connect(self.click_reset_range_btn)

        self.plot_items = {}
        for idx, channel in enumerate(self.channels):
            self.app.add_hook(
                self.instrument,
                f"CH{channel}_WAVEFORM",
                "post_read_hooks",
                self.create_load_waveform_hook(channel),
            )

            pen = pg.mkPen(
                color=channel_colors[idx], style=QtCore.Qt.SolidLine, width=2
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
        for vmin, vmax, vmin_label, vmax_label in zip(
            self.vmins, self.vmaxs, self.vmin_labs, self.vmax_labs
        ):
            self.input_layout.addWidget(vmin_label)
            self.input_layout.addWidget(vmin)
            self.input_layout.addWidget(vmax_label)
            self.input_layout.addWidget(vmax)
        self.input_layout.addWidget(self.range_btn)
        self.input_layout.addWidget(self.reset_range_btn)
        self.master_layout = QGridLayout()
        self.master_layout.addWidget(self.display, 0, 0, 5, 30)
        self.master_layout.addLayout(self.input_layout, 6, 0, 1, 20)
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

        return trace_string

    def user_resize(self):
        """Resize channel ranges accoridng to user inputs."""
        self.p1.setYRange(float(self.vmins[0].text()), float(self.vmaxs[0].text()))
        self.p2.setYRange(float(self.vmins[1].text()), float(self.vmaxs[1].text()))

    def automate_resize(self, wave, channel):
        """Resize according to channel trace min and max."""
        if channel == self.channels[0]:
            p = self.p1
        else:
            p = self.p2

        new_min = np.min(wave) - 0.2 * np.abs(np.min(wave))
        new_max = np.max(wave) + 0.2 * np.abs(np.max(wave))
        p.setYRange(new_min, new_max)

    def click_range_btn(self):
        """Uncheck automatic resizing button."""
        self.reset_range_btn.setChecked(False)

    def click_reset_range_btn(self):
        """Uncheck user resize button."""
        self.range_btn.setChecked(False)
