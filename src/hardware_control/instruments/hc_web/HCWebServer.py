"""Read channels that another experiment publishes to an hc_web server.

The driver polls the server, keeps what it receives in a local history file
(see :class:`hardware_control.web.ChannelHistory`), and offers the newest value
of every channel as a parameter. This lets one experiment log the values of
another one.

"""

import hashlib
import logging
import re
import threading
import time
from pathlib import Path

from platformdirs import user_data_dir

from ...base import Instrument
from ...web.history import ChannelHistory
from hc_web.client import WebClient, WebClientError

logger = logging.getLogger(__name__)

CHANNEL_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}/[A-Za-z0-9_.-]{1,64}$")
PARAMETER_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
RESERVED_PARAMETERS = ("ONLINE", "IGNORE")
OVERLAP = 60.0  # seconds of data that are fetched again, to not miss a point
RETRY_INTERVAL = 60.0  # seconds before a failed poll is tried again, at most
UNKNOWN = "nan"  # what an unknown value is inside hardware-control


def default_history_file(instrument_name: str) -> Path:
    """The history file of an instrument: ``<name>.sqlite`` in the user data dir."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", instrument_name)
    if safe != instrument_name:  # two names must not share a file
        digest = hashlib.sha256(instrument_name.encode()).hexdigest()[:8]
        safe = f"{safe}-{digest}"
    directory = Path(user_data_dir("hardware-control", "lbnl")) / "web_history"
    return directory / f"{safe}.sqlite"


def parse_channels(channels) -> dict[str, str]:
    """Map parameter name -> ``experiment/channel`` from a list or a dict.

    In a list, ``"B/ng_on"`` becomes the parameter ``B_ng_on``.
    """
    if isinstance(channels, dict):
        items = list(channels.items())
    elif isinstance(channels, list | tuple):
        items = [
            (c.replace("/", "_") if isinstance(c, str) else c, c) for c in channels
        ]
    else:
        raise TypeError("channels must be a list or a dict of parameter: channel")
    if not items:
        raise ValueError("no channels given")

    result: dict[str, str] = {}
    for parameter, channel in items:
        if not isinstance(channel, str) or not CHANNEL_PATTERN.match(channel):
            raise ValueError(
                f"channel {channel!r} must look like experiment/channel, using "
                "A-Z a-z 0-9 _ . - (up to 64 characters each)"
            )
        if not isinstance(parameter, str) or not PARAMETER_PATTERN.match(parameter):
            raise ValueError(
                f"parameter name {parameter!r} may only use A-Z a-z 0-9 _ . -"
            )
        if parameter in RESERVED_PARAMETERS:
            raise ValueError(f"parameter name {parameter!r} is reserved")
        if parameter in result:
            raise ValueError(
                f"the channels {result[parameter]!r} and {channel!r} both give "
                f"the parameter {parameter!r}; use a dict to choose other names"
            )
        result[parameter] = channel

    for experiment in dict.fromkeys(c.partition("/")[0] for c in result.values()):
        online = f"{experiment}_online"
        if online in result:
            raise ValueError(
                f"the parameter {online!r} (channel {result[online]!r}) is used for "
                f"the online state of experiment {experiment!r}"
            )
    return result


class HCWebServer(Instrument):
    """Driver for the channels of an hc_web server.

    The values are polled every ``poll_interval`` seconds, which the adapter's
    connection check drives (no extra thread), and stored in ``self.history``,
    a :class:`hardware_control.web.ChannelHistory`. The first time, the last
    ``backfill_hours`` hours are fetched; later, everything since the last
    point and the last gap that was still open. Calling ``poll`` or ``history``
    from other threads is fine.

    A read token is enough, and it can read the channels of all experiments.

    Parameters
    ----------
    instrument_name
        The name of the instrument; also the name of the default history file
        ``<user data dir>/web_history/<instrument_name>.sqlite``.
    url
        The address of the server, e.g. ``https://monitor.example.org``.
    token
        An API token of the server.
    channels
        ``["B/ng_on", "B/hv"]`` (experiment and channel name) gives the
        parameters ``B_ng_on`` and ``B_hv``; a dict
        ``{"ng": "B/ng_on"}`` chooses the parameter names.
    poll_interval
        Seconds between two polls.
    backfill_hours
        How far back to fetch the first time (no history file yet).
    history_file
        Where to keep the history, instead of the default.
    verify_tls
        Check the certificate of an https server.

    PARAMETERS
        * <experiment>_<channel> (*str*)
            * The newest value, or "nan" if it is unknown: the experiment is
              offline, the last poll failed, or the value is null.
        * <experiment>_online (*str*)
            * "True" or "False", or "nan" if the last poll failed.

    COMMANDS
        * refresh
            * Poll the server now.
    """

    def __init__(
        self,
        instrument_name: str,
        url: str,
        token: str,
        channels: list[str] | dict[str, str],
        poll_interval: float = 300,
        backfill_hours: float = 24,
        history_file: Path | None = None,
        verify_tls: bool = True,
    ):
        super().__init__(instrument_name=instrument_name)
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        if backfill_hours <= 0:
            raise ValueError("backfill_hours must be positive")
        self.manufacturer = "hardware-control"
        self.model = "hc_web server"

        # parameter name -> channel, and per experiment: [(parameter, channel)]
        self._channels = parse_channels(channels)
        self._experiments: dict[str, list[tuple[str, str]]] = {}
        for parameter, channel in self._channels.items():
            experiment = channel.partition("/")[0]
            self._experiments.setdefault(experiment, []).append((parameter, channel))

        self._client = WebClient(url, token, verify_tls=verify_tls)
        self.poll_interval = float(poll_interval)
        self.backfill_hours = float(backfill_hours)
        if history_file is None:
            history_file = default_history_file(instrument_name)
        self.history = ChannelHistory(history_file)

        # What get_value returns. The adapter thread writes it in poll and reads
        # it for the app; assigning a dict item is atomic, so no lock is needed.
        self._values = {parameter: UNKNOWN for parameter in self._channels}
        for experiment in self._experiments:
            self._values[f"{experiment}_online"] = UNKNOWN
        self._poll_lock = threading.Lock()
        self._next_poll = 0.0  # time.monotonic() of the next poll
        self._last_ok = False
        self._missing: frozenset[str] = frozenset()  # channels already warned about
        self._connect_failed = False

        for name in self._values:
            self.add_parameter(
                name,
                read_command=lambda name=name: self._values[name],
                dummy_return=UNKNOWN,
            )
        self.add_command("refresh", self._refresh)

    # -- connection -----------------------------------------------------------

    def establish_connection(self) -> bool:
        """Ask the server for its status: True if it answers."""
        try:
            self._client.status()
        except WebClientError as e:
            # the adapter tries every few seconds: say it once
            log = logger.debug if self._connect_failed else logger.warning
            log(f"{self.name}: cannot connect to the web monitor: {e}")
            self._connect_failed = True
            return False
        self._connect_failed = False
        return True

    def check_connection(self) -> bool:
        """Poll if it is time to. The server being away is not a lost connection."""
        self.poll()
        return True

    def close(self) -> None:
        """Close the history file (it opens again if it is used later)."""
        self.history.close()
        super().close()

    # -- polling --------------------------------------------------------------

    def _refresh(self) -> None:
        self.poll(force=True)

    def poll(self, force: bool = False) -> bool:
        """Fetch what is new from the server, if ``poll_interval`` has passed.

        Returns True if the data is up to date, False if the server could not
        be reached (the values are then "nan"). Before the interval is over,
        nothing is fetched and the result of the last poll is returned. This
        never raises; problems are logged as warnings.
        """
        with self._poll_lock:
            if not force and time.monotonic() < self._next_poll:
                return self._last_ok
            try:
                ok = self._poll()
            except Exception as e:
                logger.warning(f"{self.name}: polling failed: {e}", exc_info=True)
                self._set_unknown()
                ok = False
            delay = (
                self.poll_interval if ok else min(self.poll_interval, RETRY_INTERVAL)
            )
            self._next_poll = time.monotonic() + delay
            self._last_ok = ok
            return ok

    def _set_unknown(self, experiments=None) -> None:
        """Make all values of the experiments (default: all) unknown."""
        for experiment in self._experiments if experiments is None else experiments:
            self._values[f"{experiment}_online"] = UNKNOWN
            for parameter, _channel in self._experiments[experiment]:
                self._values[parameter] = UNKNOWN

    def _poll(self) -> bool:
        """Poll every experiment. False if the server cannot be reached."""
        try:
            status = self._client.status()
        except WebClientError as e:
            logger.warning(f"{self.name}: poll failed: {e}")
            self._set_unknown()
            return False

        missing = set()
        ok = True
        remaining = list(self._experiments)
        while remaining:
            experiment = remaining.pop(0)
            try:
                missing |= self._poll_experiment(experiment, status)
            except WebClientError as e:
                logger.warning(f"{self.name}: poll of {experiment} failed: {e}")
                ok = False
                if e.status is None:  # no answer: the others will not get one
                    self._set_unknown()
                    return False
                self._set_unknown([experiment])
        self._warn_missing(frozenset(missing))
        return ok

    def _warn_missing(self, missing: frozenset[str]) -> None:
        if missing - self._missing:
            logger.warning(
                f"{self.name}: not on the server: {', '.join(sorted(missing))}"
            )
        self._missing = missing

    def _since(self, channels: list[str], kinds: dict[str, str], experiment, now):
        """Where to start fetching for the channels of an experiment."""
        backfill = now - self.backfill_hours * 3600
        candidates = []
        states = []
        for channel in channels:
            last = self.history.last_time(channel)
            if last is None:
                candidates.append(backfill)  # nothing yet: the backfill window
            elif kinds[channel] == "state":
                # A state is only stored when it changes, so its newest point
                # can be days old and says nothing about what we have seen.
                states.append(last - OVERLAP)
            else:
                candidates.append(last - OVERLAP)
        gap = self.history.open_gap_start(experiment)
        if gap is not None:
            candidates.append(gap)  # what we do not know yet: from its start
        return min(candidates or states)

    def _poll_experiment(self, experiment: str, status: dict) -> set[str]:
        """Fetch one experiment and update its values; returns channels not found."""
        pairs = self._experiments[experiment]
        info = status["experiments"].get(experiment)
        if info is None:  # nobody published to it yet
            self._set_unknown([experiment])
            return {channel for _parameter, channel in pairs}
        kinds = {f"{experiment}/{c['name']}": c["kind"] for c in info["channels"]}
        wanted = list(dict.fromkeys(channel for _parameter, channel in pairs))
        present = [c for c in wanted if c in kinds]
        missing = {c for c in wanted if c not in kinds}

        online = bool(info["online"])
        if present:
            since = self._since(present, kinds, experiment, time.time())
            answer = self._client.data(present, since)
            online = bool(answer["experiments"][experiment]["online"])
            for channel, data in answer["channels"].items():
                points = [(t, v) for t, v in data["points"]]
                if data.get("before") is not None:
                    # a state that changed before ``since``: its value now
                    points.insert(0, tuple(data["before"]))
                self.history.add_points(channel, points)
            gaps = answer["experiments"][experiment]["gaps"]
            self.history.replace_gaps(
                experiment, since, answer["now"], [(s, e) for s, e in gaps]
            )

        self._values[f"{experiment}_online"] = str(online)
        for parameter, channel in pairs:
            self._values[parameter] = self._current(channel, online, missing)
        return missing

    def _current(self, channel: str, online: bool, missing: set[str]) -> str:
        """The value of a channel as hardware-control wants it."""
        if not online or channel in missing:
            return UNKNOWN
        point = self.history.last_point(channel)
        if point is None or point[1] is None:
            return UNKNOWN
        return str(point[1])
