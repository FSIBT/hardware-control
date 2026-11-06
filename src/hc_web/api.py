"""JSON API under /api/v1."""

import logging
import math
import time

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


@bp.get("/data")
def data():
    require_reader()
    now = time.time()
    names = [c for c in request.args.get("channels", "").split(",") if c]
    if not names:
        return _error(400, "channels is required")
    since = _number_arg("since")
    if since is None:
        return _error(400, "since is required")
    until = _number_arg("until")
    if until is not None and since > until:
        return _error(400, "since must not be after until")
    try:
        return jsonify(query.get_data(get_db(), names, since, until, now))
    except query.UnknownChannel as e:
        return _error(404, f"unknown channel {e.args[0]}")


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
