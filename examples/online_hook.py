#!/usr/bin/env python3
"""Demonstrate using a hook on the ONLINE parameter to track connection events.

This example shows how to attach a hook to the special ONLINE parameter that
every instrument has. The hook is called whenever the instrument's online status
changes, allowing you to trigger custom actions.

IMPORTANT: This example does NOT work in dummy mode! Dummy mode instruments
are always "online" and never disconnect, so the hook won't trigger when you
expect it to. To test this example:

1. Change the instrument and connection address to match your hardware
2. Run WITHOUT the --dummy flag
3. Power the instrument on/off to see the hook trigger
4. Watch the "Last Online" timestamp update when connection is established

Usage:
  online_hook.py [--debug] [--console] [--info]

Options:
  --debug    allow debug print statements
  --info     allow info print statements
  --console  Print logger output to console

Note: The --dummy flag is intentionally NOT supported for this example.
"""

import logging
import sys
from datetime import datetime

from docopt import docopt

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QLabel,
    QWidget,
    QGroupBox,
)
from PyQt6.QtCore import Qt

import hardware_control as hc

commands = docopt(__doc__)

logger = logging.getLogger(__name__)
hc.setup_logging_docopt(logger, commands)


class Demo(hc.HCMainWindow):
    def __init__(self):
        # Force dummy=False for this example
        super().__init__(dummy=False)

        self.setWindowTitle("ONLINE Hook Demo")

        # === CHANGE THIS TO YOUR INSTRUMENT ===
        # Replace with any instrument you have available
        # Examples:
        #   hc.instruments.Keysight_36300("ps", "192.168.0.10")
        #   hc.instruments.Rigol_DP800("ps", "192.168.0.20")
        #   hc.instruments.Alicat_M_Series("fc", "192.168.0.15")
        instrument = hc.instruments.Adam_6015("adam", "192.168.0.30")
        # ======================================

        self.app.add_instrument(instrument)

        # Track connection history
        self.connection_count = 0
        self.last_online_time = None
        self.last_offline_time = None

        # Add hook to ONLINE parameter
        self.app.add_hook(
            instrument.name,
            "ONLINE",
            "post_read_hooks",
            self.on_online_status_change,
        )

        # Create UI
        self.create_ui(instrument.name)

        self.show()

    def create_ui(self, instrument_name):
        """Create the user interface."""
        main_widget = QWidget()
        layout = QVBoxLayout()

        # Instructions
        instructions = QGroupBox("Instructions")
        instructions_layout = QVBoxLayout()

        info_text = QLabel(
            "This example demonstrates hooks on the ONLINE parameter.\n\n"
            "⚠️  This does NOT work in dummy mode!\n\n"
            "To test:\n"
            "1. Make sure you have a real instrument connected\n"
            "2. Change the instrument code to match your hardware\n"
            "3. Run without --dummy flag\n"
            "4. Power the instrument on/off to see updates below\n\n"
            f"Currently monitoring: {instrument_name}"
        )
        info_text.setWordWrap(True)
        instructions_layout.addWidget(info_text)
        instructions.setLayout(instructions_layout)
        layout.addWidget(instructions)

        # Connection status display
        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout()

        # Current status with HCLabel (auto-updates)
        self.current_status = hc.gui.widgets.HCLabel(
            self.app, instrument_name, "ONLINE", "Current Status:"
        )
        status_layout.addWidget(self.current_status)

        # Connection count
        self.connection_count_label = QLabel("Total Connections: 0")
        self.connection_count_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        status_layout.addWidget(self.connection_count_label)

        # Last online time
        self.last_online_label = QLabel("Last Online: Never")
        self.last_online_label.setStyleSheet("color: green; font-size: 12pt;")
        status_layout.addWidget(self.last_online_label)

        # Last offline time
        self.last_offline_label = QLabel("Last Offline: Never")
        self.last_offline_label.setStyleSheet("color: red; font-size: 12pt;")
        status_layout.addWidget(self.last_offline_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Event log
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout()

        self.event_log = QLabel("Waiting for connection events...")
        self.event_log.setWordWrap(True)
        self.event_log.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.event_log.setStyleSheet(
            "background-color: #f0f0f0; padding: 10px; font-family: monospace;"
        )
        self.event_log.setMinimumHeight(200)
        log_layout.addWidget(self.event_log)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def on_online_status_change(self, online_status):
        """Called whenever the ONLINE parameter changes.

        This hook is triggered by the framework whenever the instrument's
        online status is updated during connection attempts.

        Args:
            online_status: String "True" or "False"

        Returns:
            The online_status unchanged (required for hooks)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        if online_status == "True":
            # Instrument just came online
            self.connection_count += 1
            self.last_online_time = timestamp

            # Update UI
            self.connection_count_label.setText(
                f"Total Connections: {self.connection_count}"
            )
            self.last_online_label.setText(f"Last Online: {timestamp}")

            # Add to event log
            self.add_log_entry(f"[{timestamp}] ✓ ONLINE - Connection established")

            logger.info(f"Instrument came online at {timestamp}")

        elif online_status == "False":
            # Instrument went offline
            self.last_offline_time = timestamp

            # Update UI
            self.last_offline_label.setText(f"Last Offline: {timestamp}")

            # Add to event log
            self.add_log_entry(f"[{timestamp}] ✗ OFFLINE - Connection lost")

            logger.warning(f"Instrument went offline at {timestamp}")

        # IMPORTANT: Always return the value to allow the framework
        # to continue processing
        return online_status

    def add_log_entry(self, message):
        """Add an entry to the event log display."""
        current_log = self.event_log.text()

        # Clear "Waiting..." message on first event
        if "Waiting for" in current_log:
            current_log = ""

        # Add new message at the top
        if current_log:
            new_log = f"{message}\n{current_log}"
        else:
            new_log = message

        # Keep only last 20 entries
        lines = new_log.split("\n")
        if len(lines) > 20:
            lines = lines[:20]
            new_log = "\n".join(lines)

        self.event_log.setText(new_log)


print("=" * 60)
print("ONLINE Hook Example")
print("=" * 60)
print()
print("⚠️  IMPORTANT: This example does NOT work in dummy mode!")
print("              You must have a real instrument connected.")
print()
print("Before running, edit the code to match your instrument:")
print("  - Line 50: Change instrument class and connection address")
print()
print("Then test by power cycling your instrument to see the")
print("connection events logged below.")
print()
print("=" * 60)
print()

main_window = Demo()
sys.exit(main_window.app.exec_())
