from typing import Any
import logging

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from rich import print

from .alarm import Alarm

logger = logging.getLogger(__name__)


class AlarmManager(QObject):
    """Handle alarms.

    Keep a list of different alarms and call actions if the alarm triggers.

    Currenlty only playing sound is implemented, although other actions
    should be easy to add.
    """

    alarm_triggered = pyqtSignal(Alarm)
    """Emitted when an alarm has been triggered."""

    alarm_cleared = pyqtSignal(Alarm)
    """Emitted when an alarm has been cleared."""

    def __init__(self, app: Any) -> None:
        super().__init__()
        self.app = app
        self.alarms: list[Alarm] = []

        # keep track of players, so that we can stop sound and lean up
        self._active_sounds = {}

    def process_update(self, instrument: str, parameter: str, value: Any) -> None:
        """Function to check if an alarm got triggered.

        This is used in the main app whenever a new value arrives from an instrument.

        Note that there might be multiple alarms for the same
        inst/parameter combination, e.g., a high/low alarm.
        """
        for a in self.alarms:
            if a.instrument == instrument and a.parameter == parameter:
                if a.evaluate(value):
                    self._trigger(a)

    def add_alarm(self, alarm: Alarm) -> None:
        self.alarms.append(alarm)

    def remove_alarm(self, alarm: Alarm) -> None:
        try:
            self.alarms.remove(alarm)
        except ValueError:
            logger.debug(f"Alarm {alarm} not in active list - already removed")

    def clear(self, alarm: Alarm) -> None:
        """Clear an alarm.

        If a sounds was played, stop playing and clean up.
        """
        alarm.clear()
        if alarm.alarm_id in self._active_sounds:
            p, a = self._active_sounds[alarm.alarm_id]
            p.stop()
            p.deleteLater()
            a.deleteLater()
            del self._active_sounds[alarm.alarm_id]
        self.alarm_cleared.emit(alarm)

    def _trigger(self, alarm: Alarm) -> None:
        """Call the action on the alarm.

        If the action is a string, we assume it's a sounds file and will
        try to play it.
        """
        if isinstance(alarm.action, str):
            file = Path(alarm.action)
            if file.exists():
                self.play_sound(alarm, file)
            else:
                print(f"[red]ALARM[/] {alarm} ... sounds file cannot be found!")
        elif callable(alarm.action):
            alarm.action(alarm)
        self.alarm_triggered.emit(alarm)

    def play_sound(self, alarm: Alarm, filename: Path) -> None:
        """Play a sound.

        We probably should add more error checking here, e.g., if this
        actually is a sound file.
        """
        player = QMediaPlayer(self)
        audio = QAudioOutput(self)
        player.setAudioOutput(audio)
        player.setLoops(QMediaPlayer.Loops.Infinite)

        player.setSource(QUrl.fromLocalFile(str(filename.absolute())))
        audio.setVolume(1.0)

        player.play()

        # save information, so that we can clean up later
        self._active_sounds[alarm.alarm_id] = (player, audio)
