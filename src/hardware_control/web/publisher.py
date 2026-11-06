"""Publish instrument parameters and alarms of a running App to an hc_web server.

The timer tick and the alarm slots run in the main (Qt) thread. They put what
they read on a ``queue.Queue``; a worker thread owns the ``Backlog`` (SQLite,
single thread only), pushes with ``WebClient`` and reports the result back with
the ``status_changed`` signal. The worker never touches a Qt object other than
emitting that signal.
"""

import collections
import hashlib
import logging
import math
import queue
import re
import threading
import time
import urllib.parse
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
MAX_PENDING = 10000  # items the worker keeps in memory if the backlog fails
_STOP = object()  # queue marker: the worker should finish
_UNKNOWN_STATES = ("None", "nan")


def default_backlog_file(url: str, token: str) -> Path:
    """The default backlog file for pushing to ``url`` with ``token``.

    It depends on the target only (the server and the id of the token, never
    the secret), not on the App: a restarted App finds the rows that were still
    waiting when the previous run ended.
    """
    parts = urllib.parse.urlsplit(url)
    target = f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path.rstrip('/')}"
    token_id = token.split(".", 1)[0] if "." in token else ""
    digest = hashlib.sha256(f"{target}|{token_id}".encode()).hexdigest()[:16]
    directory = Path(user_data_dir("hardware-control", "lbnl")) / "web_backlog"
    return directory / f"{digest}.sqlite"


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


def _alarm_name(alarm) -> str:
    """The name of an alarm on the server: its alias, else instrument:parameter."""
    return alarm.alias or f"{alarm.instrument}:{alarm.parameter}"


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
        self.deadline = 0.0  # monotonic, set by stop() for the final push
        self.latched: tuple = ()
        self.failures = 0
        self.next_attempt = 0.0  # monotonic
        self.backlog: Backlog | None = None
        # items taken from the queue that the backlog could not store yet
        self.pending: collections.deque = collections.deque()
        self.last_count = 0
        self.store_retry_at = 0.0  # monotonic, after a backlog error

    # -- thread -------------------------------------------------------------

    def run(self) -> None:
        try:
            self._open_backlog()
            self._loop()
        except Exception:
            logger.exception("web publisher worker failed")
            self._emit("error", 0, "web publisher worker failed, see the log")
        finally:
            if self.backlog is not None:
                try:
                    self.backlog.close()
                except Exception:
                    logger.exception("cannot close the web backlog")

    def _emit(self, state: str, count: int, message: str) -> None:
        """Report the status. If the QObject is gone, ask the worker to stop."""
        try:
            self.emit(state, count, message)
        except RuntimeError:
            self.stopping.set()

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
            self._emit("error", 0, f"cannot open {self.backlog_file}: {e}")

    def _loop(self) -> None:
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
            stop_seen = False
            if item is not None:
                self._keep(item)
                stop_seen = self._drain()
            if stop_seen or self.stopping.is_set():
                break
            now = time.monotonic()
            if self._store_pending() and now >= self.next_attempt:
                ok, count = self._guard(self.backlog.count)
                if ok and count > 0:
                    self._flush()
                elif ok:
                    self.failures = 0  # nothing waits: no failure to retry
            if now >= next_prune:
                if self._guard(self.backlog.prune, time.time())[0]:
                    next_prune = now + PRUNE_INTERVAL
        self._drain()
        self._store_pending()
        self._final_push()

    def _drain(self) -> bool:
        """Take everything queued. True if the stop marker came."""
        while True:
            try:
                item = self.items.get_nowait()
            except queue.Empty:
                return False
            if item is _STOP:
                return True
            self._keep(item)

    def _keep(self, item) -> None:
        points, ticks, events, latched = item
        self.latched = latched
        self.pending.append((points, ticks, events))
        while len(self.pending) > MAX_PENDING:
            self.pending.popleft()
            logger.warning(
                f"web backlog cannot store rows, dropped the oldest of {MAX_PENDING}"
            )

    def _store_pending(self) -> bool:
        """Add the kept items to the backlog. False if that failed (kept)."""
        if self.pending and time.monotonic() < self.store_retry_at:
            return False
        while self.pending:
            try:
                self.backlog.add(*self.pending[0])
            except Exception as e:
                self._storage_failed(e)
                return False
            self.pending.popleft()
        return True

    def _guard(self, function, *args):
        """``(True, result)``, or ``(False, None)`` after a backlog error."""
        try:
            return True, function(*args)
        except Exception as e:
            self._storage_failed(e)
            return False, None

    def _backoff(self) -> None:
        delay = min(self.interval * 2**self.failures, MAX_BACKOFF)
        self.failures = min(self.failures + 1, 30)
        self.next_attempt = time.monotonic() + delay

    def _storage_failed(self, error: Exception) -> None:
        logger.warning(f"web backlog error: {error}")
        self._backoff()
        self.store_retry_at = self.next_attempt
        self._emit("error", self.last_count + len(self.pending), f"backlog: {error}")

    def _count(self) -> int:
        try:
            self.last_count = self.backlog.count()
        except Exception as e:
            logger.warning(f"cannot count the web backlog: {e}")
        return self.last_count

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
        """Push the backlog batch by batch; on a failure back off.

        A batch the server rejects with 400 will never be accepted, so it is
        dropped and the next one is tried. Any other failure keeps the rows.
        """
        backlog = self.backlog
        pushed = False
        rejected = None
        while not self.stopping.is_set():
            ok, batch = self._guard(backlog.take, BATCH_SIZE)
            if not ok:
                return
            if not (batch.points or batch.ticks or batch.events):
                break
            try:
                self.client.push(self._body(batch, shutdown=False))
            except WebClientError as e:
                if e.status != 400:
                    self._failed(e)
                    return
                rows = len(batch.points) + len(batch.ticks) + len(batch.events)
                logger.warning(f"web server rejected {rows} rows, dropped them: {e}")
                rejected = str(e)
            except Exception as e:  # not a request error: keep rows, back off
                logger.exception("web push failed")
                self._failed(e)
                return
            else:
                pushed = True
            if not self._guard(backlog.remove, batch)[0]:
                return
        if pushed or rejected is not None:
            self.failures = 0
            self.next_attempt = 0.0
            count = self._count()
            if rejected is not None:
                self._emit("error", count, rejected)
            else:
                self._emit("connected", count, f"Connected to {self.client.url}")

    def _failed(self, error: Exception) -> None:
        count = self._count()
        self._backoff()
        status = getattr(error, "status", None)
        if isinstance(error, WebClientConflict) or not (
            isinstance(error, WebClientError) and (status is None or status >= 500)
        ):
            logger.warning(f"web push rejected: {error}")
            self._emit("error", count, str(error))
        else:
            logger.warning(f"web push failed, buffering {count} rows: {error}")
            self._emit("buffering", count, str(error))

    def _final_push(self) -> None:
        """Best effort: send what is left, the last batch with ``shutdown``.

        The client's timeout is lowered for this and put back afterwards.
        """
        backlog = self.backlog
        timeout = self.client.timeout
        try:
            while True:
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    return
                self.client.timeout = min(timeout, remaining)
                batch = backlog.take(BATCH_SIZE)
                rows = len(batch.points) + len(batch.ticks) + len(batch.events)
                last = backlog.count() <= rows
                try:
                    self.client.push(self._body(batch, shutdown=last))
                except WebClientError as e:
                    logger.warning(f"final web push failed: {e}")
                    return
                backlog.remove(batch)
                if last:
                    return
        except Exception:
            logger.exception("final web push failed")
        finally:
            self.client.timeout = timeout


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
            else default_backlog_file(url, token)
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
        self._latched: tuple = ()
        self._queue: queue.Queue | None = None
        self._thread: threading.Thread | None = None
        self._worker: _Worker | None = None
        self._old_thread: threading.Thread | None = None  # one stop() did not end
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
        "on", sent at every interval like the others; the server keeps only the
        changes).
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
        for name, text in (("unit", unit), ("label", label)):
            if text is not None and not isinstance(text, str):
                raise TypeError(f"{name} must be a string or None, got {text!r}")
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
        if self._old_thread is not None and self._old_thread.is_alive():
            raise RuntimeError(
                "the worker of the previous run is still finishing; "
                "wait a moment before start()"
            )
        self.run_id = uuid.uuid4().hex
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
            self._old_thread = thread

    # -- main thread slots --------------------------------------------------

    def _set_status(self, state: str, count: int, message: str) -> None:
        self.status = (state, count, message)

    def _latched_aliases(self) -> tuple:
        return tuple(_alarm_name(a) for a in self.app.alarm_manager.alarms if a.latched)

    def _instrument_offline(self, instrument: str) -> bool:
        """True if the App knows that ``instrument`` is offline.

        Then the value the App still holds is the last one read, not current.
        Not in dummy mode (no hardware is contacted) and not for a virtual
        instrument (no ONLINE parameter, its values are set by the program).
        """
        app = self.app
        if app.dummy or instrument in app.virtual_instruments:
            return False
        try:
            return app.get_instrument_parameter(instrument, "ONLINE") == "False"
        except Exception as e:
            logger.debug(f"cannot read {instrument}:ONLINE: {e}")
            return False

    def tick(self) -> None:
        """Read the published parameters and queue them for the worker."""
        queue_ = self._queue
        if queue_ is None:
            return
        t = time.time()
        points = []
        offline: dict[str, bool] = {}
        for instrument, parameter, channel, kind in self._sources:
            if instrument not in offline:
                offline[instrument] = self._instrument_offline(instrument)
            try:
                raw = self.app.get_instrument_parameter(instrument, parameter)
            except Exception as e:
                logger.debug(f"cannot read {instrument}:{parameter}: {e}")
                raw = None
            if offline[instrument]:
                raw = None  # the stored value is old: unknown, not current
            if kind == "sampled":
                points.append({"channel": channel, "t": t, "v": _sampled_value(raw)})
                continue
            # Every tick, not only on a change: the server stores a value only
            # if it differs from the stored one or the time in between has a
            # gap, so a repeat costs nothing, while after a gap (a restart, a
            # long outage) the state is known again from the next tick.
            points.append({"channel": channel, "t": t, "v": _state_value(raw)})
        self._latched = self._latched_aliases()
        queue_.put((points, [t], [], self._latched))

    def _queue_event(self, alarm, action: str) -> None:
        queue_ = self._queue
        if queue_ is None:
            return
        t = time.time()
        event = {
            "t": t,
            "alarm": _alarm_name(alarm),
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
