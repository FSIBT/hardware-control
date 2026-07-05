import time
from dataclasses import dataclass, field
from typing import Any, ClassVar

COMPARATORS = {
    ">": lambda v, t: v > t,
    "≥": lambda v, t: v >= t,
    "<": lambda v, t: v < t,
    "≤": lambda v, t: v <= t,
}


@dataclass
class Alarm:
    instrument: str
    parameter: str
    alias: str
    comparator: str  # ">", "≥", "<", "≤"
    threshold: float
    duration: float = 0.0  # seconds the condition must hold
    action: str = "beep"  # name of action in AlarmManager.action_library
    latched: bool = False  # becomes True when alarm fires
    _t0: float = 0.0  # private – when the limit was first crossed
    alarm_id: int = field(init=False)

    _next_id: ClassVar[int] = 0

    def __post_init__(self) -> None:
        Alarm._next_id += 1
        self.alarm_id = Alarm._next_id

    def evaluate(self, value: Any) -> bool:
        """Returns True when alarm becomes *newly* active.

        Note: once an alarm latches (``latched=True``), it stays latched even
        if the condition clears. It must be explicitly reset by calling
        :meth:`clear`. This is intentional — it ensures alarms are
        acknowledged by the user rather than silently auto-clearing.
        """

        try:
            v = float(value)
        except (TypeError, ValueError):
            return False

        if self.comparator not in COMPARATORS:
            return False

        is_limit_hit = COMPARATORS[self.comparator](v, self.threshold)

        # timing / persistence
        now = time.time()
        if is_limit_hit:
            if self._t0 == 0:
                self._t0 = now
            if self.duration > 0 and (now - self._t0) < self.duration:
                return False
        else:
            self._t0 = 0
            if not self.latched:  # already cleared
                return False

        # if we arrive here the limit is decisive
        if not self.latched and is_limit_hit:
            self.latched = True
            return True  # NEWLY triggered
        if not is_limit_hit and self.latched:
            # will auto-clear once user presses “Clear”
            return False
        return False

    def clear(self) -> None:
        self.latched = False
        self._t0 = 0.0
