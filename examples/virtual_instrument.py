#!/usr/bin/env python3
"""Demonstrate virtual instruments for non-hardware data sources.

Virtual instruments allow you to integrate data from sources like web APIs,
calculations, or user input into the hardware_control framework. They work
seamlessly with widgets, datasets, alarms, and hooks just like physical instruments.

This example shows:
- A random number generator updating a virtual parameter
- User input via QLineEdit updating another virtual parameter
- HCLabels automatically displaying both parameters
- Dataset tracking and plotting the values over time

Usage:
  virtual_instrument.py [--dummy] [--debug] [--console] [--info]

Options:
  --dummy    use dummy connection for instruments that return semi-random data
             so that one run the program away from the test stand
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console
"""

import logging
import sys
import random

from docopt import docopt

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTabWidget,
    QLabel,
    QLineEdit,
    QGroupBox,
)
from PyQt6.QtCore import QTimer

import hardware_control as hc

commands = docopt(__doc__)
dummy = commands["--dummy"]

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self, dummy):
        super().__init__(dummy=dummy)

        self.setWindowTitle("Virtual Instrument Demo")

        # Create a virtual instrument with two parameters
        self.app.add_virtual_instrument("DataSource", ["random_value", "user_input"])

        # Add formatting hook to show 2 decimal places
        self.app.add_hook(
            "DataSource",
            "random_value",
            "post_read_hooks",
            hc.hooks.format_float(".2f"),
        )

        # Create Tab 1: Input/Output demonstration
        self.create_io_tab()

        # Create Tab 2: Dataset and plotting
        self.create_dataset_tab()

        # Set up timer to update random value every second
        self.random_timer = QTimer()
        self.random_timer.timeout.connect(self.update_random_value)
        self.random_timer.start(1000)  # 1000 ms = 1 second

        # Display tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.io_widget, "Input/Output")
        self.tabs.addTab(self.dataset_widget, "Dataset View")

        self.setCentralWidget(self.tabs)
        self.show()

    def create_io_tab(self):
        """Create the input/output demonstration tab."""
        self.io_widget = QWidget()
        layout = QVBoxLayout()

        # Random Value Section
        random_group = QGroupBox("Random Number Generator")
        random_layout = QVBoxLayout()

        # QLabel showing the random number (not connected to framework)
        qlabel_layout = QHBoxLayout()
        qlabel_layout.addWidget(QLabel("QLabel (direct):"))
        self.random_qlabel = QLabel("0.00")
        qlabel_layout.addWidget(self.random_qlabel)
        qlabel_layout.addStretch()
        random_layout.addLayout(qlabel_layout)

        # HCLabel showing the same value via virtual instrument
        self.random_hclabel = hc.gui.widgets.HCLabel(
            self.app, "DataSource", "random_value", "HCLabel (via virtual instrument):"
        )
        random_layout.addWidget(self.random_hclabel)

        random_layout.addWidget(
            QLabel(
                "Both labels show the same value. The HCLabel automatically\n"
                "updates when the virtual instrument parameter changes."
            )
        )
        random_group.setLayout(random_layout)
        layout.addWidget(random_group)

        # User Input Section
        input_group = QGroupBox("User Input")
        input_layout = QVBoxLayout()

        # QLineEdit for user input
        lineedit_layout = QHBoxLayout()
        lineedit_layout.addWidget(QLabel("Enter a value:"))
        self.user_lineedit = QLineEdit()
        self.user_lineedit.setPlaceholderText("Type a number and press Enter")
        self.user_lineedit.editingFinished.connect(self.update_user_input)
        lineedit_layout.addWidget(self.user_lineedit)
        input_layout.addLayout(lineedit_layout)

        # HCLabel showing the user input value
        self.input_hclabel = hc.gui.widgets.HCLabel(
            self.app, "DataSource", "user_input", "Current value:"
        )
        input_layout.addWidget(self.input_hclabel)

        input_layout.addWidget(
            QLabel("The HCLabel automatically updates when you finish editing.")
        )
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        layout.addStretch()
        self.io_widget.setLayout(layout)

    def create_dataset_tab(self):
        """Create the dataset and plotting tab."""
        # Create a dataset to track both virtual parameters
        self.dataset = hc.Dataset("virtual_data", self.app)
        self.dataset.track_instrument("DataSource", "random_value", alias="Random")
        self.dataset.track_instrument("DataSource", "user_input", alias="User Input")

        # Automatically update the dataset every 2 seconds
        self.dataset.start_updates(2)

        # Add dataset to the app
        self.app.add_dataset(self.dataset)

        # Create a plot widget
        self.plot = hc.gui.PlotTool(self.app)
        self.plot.set_dataset("virtual_data")

        self.dataset_widget = self.plot

    def update_random_value(self):
        """Update the random value (called every second by timer)."""
        # Generate a random value between 0 and 100
        random_value = random.uniform(0, 100)

        # Update the QLabel directly
        self.random_qlabel.setText(f"{random_value:.2f}")

        # Update the virtual instrument parameter
        # This will automatically update the HCLabel, trigger alarms, and log to dataset
        self.app.update_virtual_instrument_parameter(
            "DataSource", "random_value", random_value
        )

    def update_user_input(self):
        """Update the user input value (called when QLineEdit editing finishes)."""
        try:
            # Get the value from the line edit
            value = float(self.user_lineedit.text())

            # Update the virtual instrument parameter
            # This will automatically update the HCLabel and log to dataset
            self.app.update_virtual_instrument_parameter(
                "DataSource", "user_input", value
            )

            logger.info(f"User input updated to: {value}")
        except ValueError:
            logger.warning(f"Invalid input: {self.user_lineedit.text()}")


main_window = Demo(dummy=dummy)
sys.exit(main_window.app.exec_())
