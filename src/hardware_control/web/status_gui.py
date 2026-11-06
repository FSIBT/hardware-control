"""Status bar indicator for the web publisher."""

from PyQt6.QtWidgets import QLabel

from .publisher import WebPublisher

STATE_COLORS = {"connected": "green", "buffering": "darkorange", "error": "red"}


class WebPublisherIndicator(QLabel):
    """Shows whether the web publisher reaches the server.

    Add it with ``statusBar().addPermanentWidget(WebPublisherIndicator(pub))``.
    """

    def __init__(self, publisher: WebPublisher, parent=None) -> None:
        super().__init__(parent)
        self.publisher = publisher
        publisher.status_changed.connect(self.show_status)
        self.show_status(*publisher.status)

    def show_status(self, state: str, count: int, message: str) -> None:
        """Show ``state`` ("connected", "buffering" or "error") and ``message``."""
        if state == "connected":
            text = "Web ✓"
        elif state == "buffering":
            text = f"Web: buffering {count}"
        else:
            text = "Web: error"
        self.setText(text)
        color = STATE_COLORS.get(state, "red")
        self.setStyleSheet(f"QLabel {{ color: {color}; }}")
        self.setToolTip(message)
