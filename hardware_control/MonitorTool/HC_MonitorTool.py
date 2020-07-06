import json

import pkg_resources
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QGroupBox, QLabel, QGridLayout, QSpacerItem, QSizePolicy
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
                "hardware_control", "icons/ind_darkgrey.png"
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

    def set_indicator(self, hook_name: str, color: str):

        # Make sure is valid hook
        if hook_name not in self.hooks:
            return

        row = self.hooks[hook_name][1]

        color = color.upper()

        if color == "BLUE":
            self.widgets[int(row) * int(2) + 1].setPixmap(self.blue_indicator)
        elif color == "GREY":
            self.widgets[int(row) * int(2) + 1].setPixmap(self.grey_indicator)
        elif color == "DARKGREY":
            self.widgets[int(row) * int(2) + 1].setPixmap(self.darkgrey_indicator)
        elif color == "RED":
            self.widgets[int(row) * int(2) + 1].setPixmap(self.red_indicator)
        elif color == "GREEN":
            self.widgets[int(row) * int(2) + 1].setPixmap(self.green_indicator)
        else:
            logger.debug("Color '{color}' not recognized")

    def add_spacer(self):

        self.bottom_spacer = QSpacerItem(
            10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        self.indicator_grid.addItem(self.bottom_spacer, self.idx, 0)
        self.idx += 1

    def add_hook(self, hook_name: str, hook, show_indicator=True):

        if hook_name in self.hooks:
            logger.warning(
                f"Failed to add hook '{hook_name}' because a hook with that name already exists."
            )

        self.hooks[hook_name] = (hook, self.idx)

        if show_indicator:
            self.widgets.append(QLabel(hook_name))
            self.widgets[-1].setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.indicator_grid.addWidget(self.widgets[-1], self.idx, 0)

            self.widgets.append(QLabel())
            self.widgets[-1].setPixmap(self.grey_indicator)
            self.widgets[-1].setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.indicator_grid.addWidget(self.widgets[-1], self.idx, 1)

        self.idx += 1

    def run_hooks(self):

        del_hooks = []

        # Call each hook
        for key in self.hooks:

            # Skip hook if not callable
            if not callable(self.hooks[key][0]):
                logger.warning(f"Hook '{key}' is not callable. Removing hook.")
                del_hooks.append(key)
                continue

            # Call hook
            self.hooks[key][0](self, key)

        # Delete non-callable hooks
        for dh in del_hooks:
            self.hooks.pop(dh)
