import json

import pkg_resources
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QGroupBox, QLabel, QGridLayout
import logging

logger = logging.getLogger(__name__)


class HC_MonitorTool(QGroupBox):
    def __init__(self, window, name: str = "Monitor"):

        super().__init__(name)

        self.settings = {}
        self.name = name
        self.app = window.app
        self.ignore = True

        self.hooks = {}

        # Load indicators
        self.green_indicator = QPixmap(
            pkg_resources.resource_filename("hardware_control", "icons/green_ind.svg")
        )
        self.grey_indicator = QPixmap(
            pkg_resources.resource_filename("hardware_control", "icons/grey_ind.svg")
        )
        self.darkgrey_indicator = QPixmap(
            pkg_resources.resource_filename(
                "hardware_control", "graphics/ind_darkgrey.png"
            )
        )
        self.red_indicator = QPixmap(
            pkg_resources.resource_filename("hardware_control", "icons/red_ind.svg")
        )
        self.blue_indicator = QPixmap(
            pkg_resources.resource_filename("hardware_control", "icons/blue_ind.svg")
        )

        self.widgets = []

        self.idx = 0
        self.indicator_grid = QGridLayout()

        self.master_layout = QGridLayout()
        self.master_layout.addLayout(self.indicator_grid, 0, 0)
        self.setLayout(self.master_layout)

        self.hook_timer = QTimer(self)
        self.hook_timer.timeout.connect(self.run_hooks)
        self.hook_timer.start(1000)

    def add_hook(self, hook_name: str, hook, show_indicator=True):

        # Add hook to list

        if hook_name in self.hooks:
            logger.warning(
                f"Failed to add hook '{hook_name}' because a hook with that name already exists."
            )

        self.hooks[hook_name] = (hook, self.idx)

        if show_indicator:
            self.widgets.append(QLabel(hook_name))
            self.indicator_grid.addWidget(self.widgets[-1], self.idx, 0)

            self.widgets.append(QLabel())
            self.widgets[-1].setPixmap(self.grey_indicator)
            self.indicator_grid.addWidget(self.widgets[-1], self.idx, 1)

        self.idx += 1

    def run_hooks(self):

        # # Clear layout
        # for i in reversed(range(self.instrument_grid.count())):
        #     self.instrument_grid.itemAt(i).widget().setParent(None)
        #
        # row = 0
        # for inst in self.app.instruments:
        #
        #     if inst.ignore:
        #         continue
        #
        #     label = QLabel(inst.name)
        #     indicator = QLabel()
        #     indicator.setPixmap(self.grey_indicator)
        #     indicator.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        #
        #     self.instrument_grid.addWidget(label, row, 0)
        #     self.instrument_grid.addWidget(indicator, row, 1)
        #     row += 1

        pass
