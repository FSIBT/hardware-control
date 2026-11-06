"""JSON API under /api/v1."""

import csv
import io
import logging
import math
import time
from datetime import UTC, datetime

from flask import Blueprint, abort, current_app, jsonify, make_response, request

from . import auth, query
from .app import get_db
from .ingest import PushError, ingest_push
from .retention import maybe_cleanup
from .tokens import TokenInfo, check_token

log = logging.getLogger(__name__)

bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _error(status: int, message: str, **headers):
    response = make_response(jsonify({"error": message}), status)
    response.headers.update(headers)
    return response


def _bearer_token() -> str | None:
    scheme, _, value = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer":
        return None
    return value.strip() or None


def require_token(scope: str) -> TokenInfo:
    """Return the caller's token info, or abort with 401 (no/bad) or 403."""
    info = check_token(get_db(), _bearer_token())
    if info is None:
        abort(_error(401, "missing or invalid token", **{"WWW-Authenticate": "Bearer"}))
    if info.scope != scope:
        abort(_error(403, f"a {scope} token is required"))
    return info


def require_reader() -> None:
    """Allow a token of any scope or a logged-in session; else abort with 401."""
    if check_token(get_db(), _bearer_token()) is not None:
        return
    if auth.current_user() is not None:
        return
    abort(_error(401, "missing or invalid token", **{"WWW-Authenticate": "Bearer"}))


def _number_arg(name: str, default: float | None = None) -> float | None:
    """A finite float query parameter, or ``default`` if absent (400 if bad)."""
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not math.isfinite(value):
        abort(_error(400, f"{name} must be a finite number"))
    return value


@bp.post("/push")
def push():
    token = require_token("write")
    now = time.time()
    try:
        maybe_cleanup(get_db(), now, current_app.config["HC"].retention_days)
    except Exception:
        log.exception("retention cleanup failed")
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict):
        return _error(400, "body must be a JSON object")
    try:
        ingest_push(get_db(), token, body, now)
    except PushError as e:
        return _error(e.status, e.message)
    return jsonify({"ok": True})


def _data_params() -> tuple[list[str], float, float | None]:
    """The ``channels``, ``since`` and ``until`` of a data request (400 if bad)."""
    names = [c for c in request.args.get("channels", "").split(",") if c]
    if not names:
        abort(_error(400, "channels is required"))
    since = _number_arg("since")
    if since is None:
        abort(_error(400, "since is required"))
    until = _number_arg("until")
    if until is not None and since > until:
        abort(_error(400, "since must not be after until"))
    return names, since, until


@bp.get("/data")
def data():
    require_reader()
    now = time.time()
    names, since, until = _data_params()
    try:
        return jsonify(query.get_data(get_db(), names, since, until, now))
    except query.UnknownChannel as e:
        return _error(404, f"unknown channel {e.args[0]}")


def _iso(t: float) -> str:
    try:
        moment = datetime.fromtimestamp(t, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return ""
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _csv_cell(v):
    """A value for a CSV cell: unknown is empty, text cannot become a formula."""
    if v is None:
        return ""
    if isinstance(v, str):
        if v[:1] in ("\t", "\r"):
            return "'" + v
        if v[:1] in ("=", "+", "-", "@"):
            try:
                float(v)  # a number such as "-5" is data, not a formula
            except ValueError:
                return "'" + v
    return v


@bp.get("/data.csv")
def data_csv():
    """The points of ``/data`` as a download: ``time,time_iso,channel,value``.

    Channel by channel in the requested order, each oldest first. ``time`` is
    unix seconds, an unknown value is an empty cell. Over ``MAX_CSV_POINTS``
    points the answer is 413: the file is built in memory.
    """
    require_reader()
    names, since, until = _data_params()
    try:
        result = query.get_data(
            get_db(), names, since, until, time.time(), max_points=query.MAX_CSV_POINTS
        )
    except query.UnknownChannel as e:
        return _error(404, f"unknown channel {e.args[0]}")
    except query.TooManyPoints:
        return _error(413, "too many points to export; narrow the time range")
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["time", "time_iso", "channel", "value"])
    for name, channel in result["channels"].items():
        for t, v in channel["points"]:
            writer.writerow([t, _iso(t), name, _csv_cell(v)])
    response = make_response(out.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = 'attachment; filename="hc_web_data.csv"'
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/status")
def status():
    require_reader()
    return jsonify(query.get_status(get_db(), time.time()))


@bp.get("/events")
def events():
    require_reader()
    now = time.time()
    since = _number_arg("since", default=0.0)
    return jsonify({"now": now, "events": query.get_events(get_db(), since)})
