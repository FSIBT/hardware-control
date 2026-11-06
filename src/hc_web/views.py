"""Browser pages and the JSON routes behind them.

``admin`` is the administrator surface: ``GET /admin`` and the JSON routes
under ``/admin/api/``. Every route in it requires a logged-in admin session; an
API token never grants access. Every POST must be ``application/json`` (the
CSRF guard described in ``auth``), and that is checked before anything else.
"""

from flask import Blueprint, current_app, jsonify, make_response, request

from . import tokens, users
from .app import get_db
from .auth import (
    admin_required,
    current_user,
    json_body,
    render_page,
    require_json_post,
)

WARNING_LIMIT = 200
MAX_TOKEN_NAME_LENGTH = users.MAX_NAME_LENGTH

# --- administrator surface ---------------------------------------------------

admin = Blueprint("admin", __name__, url_prefix="/admin")
admin.before_request(require_json_post)


@admin.after_request
def _no_store(response):
    # Responses carry user lists and, once, a new token: never cache them.
    response.headers["Cache-Control"] = "no-store"
    return response


def _error(status: int, message: str):
    return make_response(jsonify({"error": message}), status)


@admin.get("")
@admin_required
def admin_page():
    return render_page("admin.html")


@admin.get("/api/users")
@admin_required
def list_users():
    conn = get_db()
    result = []
    for user in users.list_users(conn):
        # Only what the page displays: neither the credential id nor its key.
        credentials = [
            {"label": c["label"], "created": c["created"], "last_used": c["last_used"]}
            for c in users.list_credentials(conn, user["id"])
        ]
        result.append(
            {
                "id": user["id"],
                "name": user["name"],
                "role": user["role"],
                "created": user["created"],
                "credentials": credentials,
            }
        )
    return jsonify({"users": result, "current_user": current_user()["id"]})


@admin.post("/api/invite")
@admin_required
def create_invite():
    body = json_body()
    if body is None:
        return _error(400, "body must be a JSON object")
    role = body.get("role")
    if role not in users.ROLES:  # also false for a list, number or null
        return _error(400, f"role must be one of {', '.join(users.ROLES)}")
    code = users.create_invite(get_db(), role, current_user()["id"])
    return jsonify({"url": users.invite_url(current_app.config["HC"], code)})


@admin.post("/api/users/<int(max=9223372036854775807):user_id>/role")
@admin_required
def set_user_role(user_id: int):
    body = json_body()
    if body is None:
        return _error(400, "body must be a JSON object")
    role = body.get("role")
    if role not in users.ROLES:
        return _error(400, f"role must be one of {', '.join(users.ROLES)}")
    try:
        found = users.set_role_keeping_an_admin(get_db(), user_id, role)
    except users.LastAdminError as e:
        return _error(400, str(e))
    if not found:
        return _error(404, "no such user")
    return jsonify({"ok": True})


@admin.post("/api/users/<int(max=9223372036854775807):user_id>/delete")
@admin_required
def delete_user(user_id: int):
    if json_body() is None:
        return _error(400, "body must be a JSON object")
    try:
        found = users.delete_user_keeping_an_admin(get_db(), user_id)
    except users.LastAdminError as e:
        return _error(400, str(e))
    if not found:
        return _error(404, "no such user")
    return jsonify({"ok": True})


@admin.get("/api/tokens")
@admin_required
def list_tokens():
    # list_tokens selects neither the salt nor the hash, and the secret is not stored.
    rows = tokens.list_tokens(get_db())
    for row in rows:
        row["revoked"] = bool(row["revoked"])
    return jsonify({"tokens": rows})


@admin.post("/api/tokens")
@admin_required
def create_token():
    body = json_body()
    if body is None:
        return _error(400, "body must be a JSON object")
    name = body.get("name")
    name = name.strip() if isinstance(name, str) else name
    if not users.valid_name(name):
        return _error(
            400, f"name must be 1-{MAX_TOKEN_NAME_LENGTH} printable characters"
        )
    try:
        token = tokens.create_token(
            get_db(), body.get("experiment"), name, body.get("scope")
        )
    except ValueError as e:
        return _error(400, str(e))
    return jsonify({"token": token})


@admin.post("/api/tokens/<int(max=9223372036854775807):token_id>/revoke")
@admin_required
def revoke_token(token_id: int):
    if json_body() is None:
        return _error(400, "body must be a JSON object")
    if not tokens.revoke_token(get_db(), token_id):
        return _error(404, "no such token")
    return jsonify({"ok": True})


@admin.get("/api/warnings")
@admin_required
def list_warnings():
    rows = get_db().execute(
        "SELECT w.id, e.name AS experiment, w.t, w.message "
        "FROM warnings w LEFT JOIN experiments e ON e.id = w.experiment_id "
        "ORDER BY w.t DESC, w.id DESC LIMIT ?",
        (WARNING_LIMIT,),
    )
    return jsonify({"warnings": [dict(r) for r in rows]})
