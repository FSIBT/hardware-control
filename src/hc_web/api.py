"""JSON API under /api/v1."""

import time

from flask import Blueprint, abort, jsonify, make_response, request

from .app import get_db
from .ingest import PushError, ingest_push
from .tokens import TokenInfo, check_token

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


@bp.post("/push")
def push():
    token = require_token("write")
    now = time.time()
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict):
        return _error(400, "body must be a JSON object")
    try:
        ingest_push(get_db(), token, body, now)
    except PushError as e:
        return _error(e.status, e.message)
    return jsonify({"ok": True})
