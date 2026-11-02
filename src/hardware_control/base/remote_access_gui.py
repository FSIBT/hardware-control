"""Widgets to change the remote access settings of an App."""

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QToolButton,
    QVBoxLayout,
)

from .remote_access import AccessMode, format_duration, generate_token

MODE_NAMES = {
    AccessMode.OFF: "Off",
    AccessMode.READ_ONLY: "Read-only",
    AccessMode.FULL: "Full control",
}
MODE_COLORS = {
    AccessMode.OFF: "gray",
    AccessMode.READ_ONLY: "darkorange",
    AccessMode.FULL: "red",
}


class RemoteAccessPopup(QFrame):
    """A compact popup to change the access mode, time limit and token."""

    def __init__(self, app, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.app = app
        self.clear_token = False
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Remote access (hc-query, hc-mcp)"))

        self.mode_group = QButtonGroup(self)
        self.mode_buttons = {}
        for mode, name in MODE_NAMES.items():
            button = QRadioButton(name)
            self.mode_group.addButton(button)
            self.mode_buttons[mode] = button
            layout.addWidget(button)

        self.keep = QCheckBox("Keep after restart")
        layout.addWidget(self.keep)

        row = QHBoxLayout()
        row.addWidget(QLabel("Time limit:"))
        self.duration = QLineEdit()
        self.duration.setToolTip(
            "0 for no limit, minutes, or a time like 2d8h4m. Goes back to off after."
        )
        row.addWidget(self.duration)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Token:"))
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setMinimumWidth(320)
        row.addWidget(self.token)
        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate)
        row.addWidget(self.generate_button)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear)
        row.addWidget(self.clear_button)
        layout.addLayout(row)

        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.message)

        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply)
        layout.addWidget(self.apply_button)

    def load(self) -> None:
        """Show the current settings."""
        access = self.app.remote_access
        self.mode_buttons[access.mode].setChecked(True)
        self.keep.setChecked(access.persist)
        remaining = access.remaining()
        self.duration.setText(format_duration(remaining) if remaining else "0")
        self.clear_token = False
        self.token.clear()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText("set" if access.token_required else "none")
        self.message.clear()

    def generate(self) -> None:
        """Create a token and show it, since it cannot be shown again later."""
        self.token.setText(generate_token())
        self.token.setEchoMode(QLineEdit.EchoMode.Normal)
        self.token.selectAll()
        self.message.setText("Copy this token, it will not be shown again.")

    def clear(self) -> None:
        """Remove the token when the settings are applied."""
        self.clear_token = True
        self.token.clear()
        self.token.setPlaceholderText("none")

    def selected_mode(self) -> AccessMode:
        """Return the mode of the checked radio button."""
        for mode, button in self.mode_buttons.items():
            if button.isChecked():
                return mode
        return AccessMode.OFF

    def apply(self) -> None:
        """Apply the settings, staying open if they are not valid."""
        token = None
        if self.token.text():
            token = self.token.text()
        elif self.clear_token:
            token = ""

        try:
            self.app.set_remote_access(
                self.selected_mode(), self.duration.text(), self.keep.isChecked(), token
            )
        except ValueError as e:
            self.message.setText(str(e))
            return
        self.close()

    def show_at(self, position: QPoint) -> None:
        """Show the popup with its bottom left corner at the position."""
        self.load()
        self.adjustSize()
        self.move(position - QPoint(0, self.height()))
        self.show()


class RemoteAccessIndicator(QToolButton):
    """Shows the access mode, e.g. in the status bar, and opens the popup on click."""

    def __init__(self, app, parent=None) -> None:
        super().__init__(parent)
        self.app = app
        self.setAutoRaise(True)
        self.popup = RemoteAccessPopup(app, self)
        self.clicked.connect(self.open_popup)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def refresh(self) -> None:
        """Show the current mode and any remaining time."""
        access = self.app.remote_access
        mode = access.mode
        remaining = access.remaining()
        text = f"Remote: {MODE_NAMES[mode]}"
        if remaining is not None:
            text += f" ({format_duration(remaining)})"
        self.setText(text)
        self.setStyleSheet(f"QToolButton {{ color: {MODE_COLORS[mode]}; }}")
        self.setToolTip("Click to change the remote access settings")

    def open_popup(self) -> None:
        """Open the popup just above this widget."""
        self.popup.show_at(self.mapToGlobal(QPoint(0, 0)))
