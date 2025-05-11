from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QPushButton,
    QVBoxLayout,
)

from ...base.alarm import Alarm


class AlarmPanel(QWidget):
    """Shows every configured alarm, its current state and a 'Clear' button.

    The clear button will deactivate the alarm and can stop, e.g.,  playing sounds.
    """

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.manager = self.app.alarm_manager

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(
            [
                "Active",
                "Clear",
                "Instrument",
                "Parameter",
                "Cmp",
                "Thresh",
                "Dur [s]",
            ]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        lay = QVBoxLayout(self)
        lay.addWidget(self.table)

        # update whenever list changes or an alarm toggles
        self.manager.alarm_cleared.connect(self._refresh)
        self.manager.alarm_triggered.connect(self._refresh)
        self._refresh()

    def _refresh(self, *_):
        alarms: list[Alarm] = self.manager.alarms
        self.table.setRowCount(len(alarms))
        for row, a in enumerate(alarms):
            # LED indicator
            led = LED_Widget(colour_on="red")
            led.set_on(a.latched)
            self.table.setCellWidget(row, 0, led)

            # clear button
            btn_clear = QPushButton("Clear")
            btn_clear.clicked.connect(lambda _=None, alarm=a: self.manager.clear(alarm))
            self.table.setCellWidget(row, 1, btn_clear)

            # alarm information
            for col, text in enumerate(
                (
                    a.instrument,
                    a.parameter,
                    a.comparator,
                    str(a.threshold),
                    str(a.duration),
                ),
                start=2,
            ):
                self.table.setItem(row, col, QTableWidgetItem(text))


class LED_Widget(QWidget):
    """Simple round LED that can be switched on/off (latches red)."""

    def __init__(
        self,
        diameter: int = 16,
        colour_on: QColor | str = "red",
        colour_off: QColor | str = "grey",
    ):
        super().__init__()
        self._diameter = diameter
        self._on_colour = QColor(colour_on)
        self._off_colour = QColor(colour_off)
        self._state = False
        self.setFixedSize(QSize(diameter + 2, diameter + 2))

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(self._on_colour if self._state else self._off_colour)
        p.setPen(Qt.PenStyle.NoPen)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.drawEllipse(r)

    def set_on(self, on: bool = True):
        self._state = on
        self.update()
