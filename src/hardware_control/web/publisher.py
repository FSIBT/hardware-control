"""Publish instrument parameters and alarms of a running App to an hc_web server.

The timer tick and the alarm slots run in the main (Qt) thread. They put what
they read on a ``queue.Queue``; a worker thread owns the ``Backlog`` (SQLite,
single thread only), pushes with ``WebClient`` and reports the result back with
the ``status_changed`` signal. The worker never touches a Qt object other than
emitting that signal.
"""

import hashlib
import logging
import math
import queue
import re
import threading
import time
import uuid
from pathlib import Path

from platformdirs import user_data_dir
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .backlog import Backlog
from hc_web.client import WebClient, WebClientConflict, WebClientError

logger = logging.getLogger(__name__)

CHANNEL_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
KINDS = ("sampled", "state")
MAX_BACKOFF = 300.0
BATCH_SIZE = 500
PRUNE_INTERVAL = 3600.0
_STOP = object()  # queue marker: the worker should finish
_UNKNOWN_STATES = ("None", "nan")


def default_backlog_file(app_name: str) -> Path:
    """The backlog file of an App, named like ``RemoteAccess.filename``."""
    digest = hashlib.sha256(app_name.encode()).hexdigest()[:16]
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", app_name)
    directory = Path(user_data_dir("hardware-control", "lbnl")) / "web_backlog"
    return directory / f"{safe_name}-{digest}.sqlite"


def _sampled_value(raw) -> float | None:
    """``raw`` as a finite float, else None (unknown)."""
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _state_value(raw) -> str | None:
    """``raw`` as the string of a state channel, None for unknown."""
    if raw is None or (isinstance(raw, str) and raw in _UNKNOWN_STATES):
        return None
    if isinstance(raw, float) and not math.isfinite(raw):
        return None
    return str(raw)


class _Worker:
    """What the worker thread does. Owns the backlog; no Qt except ``emit``."""

    def __init__(
        self,
        client: WebClient,
        backlog_file: Path,
        run: str,
        interval: float,
        channels: list,
        items: queue.Queue,
        stopping: threading.Event,
        emit,
    ) -> None:
        self.client = client
        self.backlog_file = backlog_file
        self.run_id = run
        self.interval = interval
        self.channels = channels  # shared with the publisher, only appended to
        self.items = items
        self.stopping = stopping
        self.emit = emit
        self.push_timeout = client.timeout
        self.deadline = 0.0  # monotonic, set by stop() for the final push
        self.latched: tuple = ()
        self.failures = 0
        self.next_attempt = 0.0  # monotonic
        self.backlog: Backlog | None = None

    # -- thread -------------------------------------------------------------

    def run(self) -> None:
        try:
            self._open_backlog()
            self._loop()
        except Exception:
            logger.exception("web publisher worker failed")
            self.emit("error", 0, "web publisher worker failed, see the log")
        finally:
            if self.backlog is not None:
                try:
                    self.backlog.close()
                except Exception:
                    logger.exception("cannot close the web backlog")

    def _open_backlog(self) -> None:
        try:
            self.backlog_file.parent.mkdir(parents=True, exist_ok=True)
            self.backlog = Backlog(self.backlog_file)
        except Exception as e:
            logger.warning(
                f"cannot open web backlog {self.backlog_file}: {e}; "
                "buffering in memory only"
            )
            self.backlog = Backlog(Path(":memory:"))
            self.emit("error", 0, f"cannot open {self.backlog_file}: {e}")

    def _loop(self) -> None:
        backlog = self.backlog
        next_prune = time.monotonic() + PRUNE_INTERVAL
        while True:
            now = time.monotonic()
            retrying = self.failures > 0
            wait = (self.next_attempt if retrying else next_prune) - now
            try:
                item = self.items.get(timeout=max(wait, 0.0))
            except queue.Empty:
                item = None
            if item is _STOP:
                break
            if item is not None:
                self._add(item)
                if self._drain():
                    break
            if self.stopping.is_set():
                break
            now = time.monotonic()
            if now >= self.next_attempt and backlog.count() > 0:
                self._flush()
            if now >= next_prune:
                backlog.prune(time.time())
                next_prune = now + PRUNE_INTERVAL
        self._drain()
        self._final_push()

    def _drain(self) -> bool:
        """Add everything queued to the backlog. True if the stop marker came."""
        while True:
            try:
                item = self.items.get_nowait()
            except queue.Empty:
                return False
            if item is _STOP:
                return True
            self._add(item)

    def _add(self, item) -> None:
        points, ticks, events, latched = item
        self.latched = latched
        self.backlog.add(points, ticks, events)

    # -- pushing ------------------------------------------------------------

    def _body(self, batch, shutdown: bool) -> dict:
        return {
            "run": self.run_id,
            "sent_at": time.time(),
            "interval": self.interval,
            "channels": list(self.channels),
            "points": batch.points,
            "ticks": batch.ticks,
            "events": batch.events,
            "latched": list(self.latched),
            "shutdown": shutdown,
        }

    def _flush(self) -> None:
        """Push the backlog batch by batch; on a failure back off."""
        backlog = self.backlog
        pushed = False
        while not self.stopping.is_set():
            batch = backlog.take(BATCH_SIZE)
            if not (batch.points or batch.ticks or batch.events):
                break
            try:
                self.client.push(self._body(batch, shutdown=False))
            except WebClientError as e:
                self._failed(e)
                return
            except Exception as e:  # e.g. a database error: keep rows, back off
                logger.exception("web push failed")
                self._failed(e)
                return
            backlog.remove(batch)
            pushed = True
        if pushed:
            self.failures = 0
            self.next_attempt = 0.0
            self.emit("connected", backlog.count(), f"Connected to {self.client.url}")

    def _failed(self, error: Exception) -> None:
        count = self.backlog.count()
        delay = min(self.interval * 2**self.failures, MAX_BACKOFF)
        self.failures = min(self.failures + 1, 30)
        self.next_attempt = time.monotonic() + delay
        status = getattr(error, "status", None)
        if isinstance(error, WebClientConflict) or not (
            isinstance(error, WebClientError) and (status is None or status >= 500)
        ):
            logger.warning(f"web push rejected: {error}")
            self.emit("error", count, str(error))
        else:
            logger.warning(f"web push failed, buffering {count} rows: {error}")
            self.emit("buffering", count, str(error))

    def _final_push(self) -> None:
        """Best effort: send what is left, the last batch with ``shutdown``."""
        backlog = self.backlog
        while True:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                return
            self.client.timeout = min(self.push_timeout, remaining)
            batch = backlog.take(BATCH_SIZE)
            last = backlog.count() <= len(batch.points) + len(batch.ticks) + len(
                batch.events
            )
            try:
                self.client.push(self._body(batch, shutdown=last))
            except WebClientError as e:
                logger.warning(f"final web push failed: {e}")
                return
            except Exception:
                logger.exception("final web push failed")
                return
            backlog.remove(batch)
            if last:
                return


class WebPublisher(QObject):
    """Pushes chosen instrument parameters and alarms of ``app`` to hc_web.

    Register parameters with ``publish()``, then call ``start()``. Pushes go
    out every ``interval`` seconds; while the server cannot be reached the data
    is kept in a backlog file and sent later.

    ``status_changed(state, count, message)`` is emitted when a push was tried:
    ``state`` is "connected", "buffering" (cannot reach the server, ``count``
    rows are waiting) or "error" (the server refused, e.g. another run of this
    experiment is live).
    """

    status_changed = pyqtSignal(str, int, str)

    def __init__(
        self,
        app,
        url: str,
        token: str,
        interval: float = 10.0,
        backlog_file: Path | None = None,
        verify_tls: bool = True,
    ) -> None:
        super().__init__()
        if not interval > 0:
            raise ValueError("interval must be positive")
        self.app = app
        self.interval = float(interval)
        self.backlog_file = (
            Path(backlog_file)
            if backlog_file is not None
            else default_backlog_file(app.app_name)
        )
        self.client = WebClient(url, token, verify_tls=verify_tls)
        self.status: tuple[str, int, str] = (
            "buffering",
            0,
            "waiting for the first push",
        )
        self.run_id: str | None = None

        self._channels: list[dict] = []  # declared to the server, read by the worker
        self._sources: list[tuple[str, str, str, str]] = []  # inst, param, name, kind
        self._last_state: dict[str, str | None] = {}
        self._latched: tuple = ()
        self._queue: queue.Queue | None = None
        self._thread: threading.Thread | None = None
        self._worker: _Worker | None = None
        self._stopping: threading.Event | None = None
        self._quit_connected = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)

        # stored first, so that other receivers see the new status
        self.status_changed.connect(self._set_status)
        alarms = app.alarm_manager
        alarms.alarm_triggered.connect(self._alarm_triggered)
        alarms.alarm_cleared.connect(self._alarm_cleared)

    # -- setup --------------------------------------------------------------

    def publish(
        self,
        instrument: str,
        parameter: str,
        channel: str | None = None,
        kind: str = "sampled",
        unit: str | None = None,
        label: str | None = None,
    ) -> None:
        """Send ``instrument``'s ``parameter`` as channel ``channel``.

        The channel defaults to ``<instrument>_<parameter>``. ``kind`` is
        "sampled" (a number, e.g. a voltage) or "state" (a string such as
        "on", sent when it changes).
        """
        if channel is None:
            channel = f"{instrument}_{parameter}"
        if not CHANNEL_PATTERN.match(channel):
            raise ValueError(
                f"channel name {channel!r} must be 1-64 characters of "
                "A-Z a-z 0-9 _ . -; pass channel= to choose another one"
            )
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}, got {kind!r}")
        if any(c["name"] == channel for c in self._channels):
            raise ValueError(f"channel {channel!r} is already published")
        self.app.add_auto_update_instrument_parameter(instrument, parameter)
        self._sources.append((instrument, parameter, channel, kind))
        self._channels.append(
            {"name": channel, "kind": kind, "unit": unit, "label": label}
        )

    def start(self) -> None:
        """Start the timer and the worker thread, with a new run id."""
        if self._thread is not None:
            logger.warning("web publisher is already running")
            return
        self.run_id = uuid.uuid4().hex
        self._last_state = {}
        self._queue = queue.Queue()
        self._stopping = threading.Event()
        self._worker = _Worker(
            self.client,
            self.backlog_file,
            self.run_id,
            self.interval,
            self._channels,
            self._queue,
            self._stopping,
            self.status_changed.emit,
        )
        self._thread = threading.Thread(
            target=self._worker.run, name="web-publisher", daemon=True
        )
        self._thread.start()
        if not self._quit_connected:
            self.app.aboutToQuit.connect(self.stop)
            self._quit_connected = True
        self._timer.start(max(1, round(self.interval * 1000)))

    def stop(self, timeout: float = 3.0) -> None:
        """Send a final push with ``shutdown`` (best effort) and end the worker.

        Safe to call more than once, or without ``start()``. Returns after
        ``timeout`` seconds at the latest.
        """
        self._timer.stop()
        thread, self._thread = self._thread, None
        if thread is None:
            return
        worker, queue_, stopping = self._worker, self._queue, self._stopping
        self._queue = None
        worker.deadline = time.monotonic() + 0.8 * timeout
        stopping.set()
        queue_.put(_STOP)
        thread.join(timeout)
        if thread.is_alive():
            logger.warning("web publisher worker did not finish in time")

    # -- main thread slots --------------------------------------------------

    def _set_status(self, state: str, count: int, message: str) -> None:
        self.status = (state, count, message)

    def _latched_aliases(self) -> tuple:
        return tuple(a.alias for a in self.app.alarm_manager.alarms if a.latched)

    def tick(self) -> None:
        """Read the published parameters and queue them for the worker."""
        queue_ = self._queue
        if queue_ is None:
            return
        t = time.time()
        points = []
        for instrument, parameter, channel, kind in self._sources:
            try:
                raw = self.app.get_instrument_parameter(instrument, parameter)
            except Exception as e:
                logger.debug(f"cannot read {instrument}:{parameter}: {e}")
                raw = None
            if kind == "sampled":
                points.append({"channel": channel, "t": t, "v": _sampled_value(raw)})
                continue
            value = _state_value(raw)
            if channel in self._last_state and self._last_state[channel] == value:
                continue
            self._last_state[channel] = value
            points.append({"channel": channel, "t": t, "v": value})
        self._latched = self._latched_aliases()
        queue_.put((points, [t], [], self._latched))

    def _queue_event(self, alarm, action: str) -> None:
        queue_ = self._queue
        if queue_ is None:
            return
        t = time.time()
        event = {
            "t": t,
            "alarm": alarm.alias or f"{alarm.instrument}:{alarm.parameter}",
            "action": action,
            "message": (
                f"{alarm.instrument}:{alarm.parameter} "
                f"{alarm.comparator} {alarm.threshold}"
            ),
        }
        self._latched = self._latched_aliases()
        queue_.put(([], [], [event], self._latched))

    def _alarm_triggered(self, alarm) -> None:
        self._queue_event(alarm, "triggered")

    def _alarm_cleared(self, alarm) -> None:
        self._queue_event(alarm, "cleared")
