"""Passkey login, invites and session handling.

Every POST under ``/auth/`` must be ``application/json``. A cross-site form
cannot send that content type, and a cross-site ``fetch`` with it triggers a
CORS preflight that this server never approves; together with the
``SameSite=Lax`` cookie that is the CSRF guard.
"""

import functools
import logging
import secrets
import sqlite3
import time

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.exceptions import (
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from . import challenges, users
from .app import get_db

log = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)

# Credential ids are at most 1023 bytes, 1364 base64url characters.
MAX_CREDENTIAL_ID_LENGTH = 1400


def _error(status: int, message: str):
    return make_response(jsonify({"error": message}), status)


def current_user() -> sqlite3.Row | None:
    """Return the logged-in user, or None.

    A session whose user no longer exists is cleared.
    """
    user_id = session.get("user_id")
    if user_id is None:
        return None
    user = users.get_user(get_db(), user_id) if isinstance(user_id, int) else None
    if user is None:
        session.clear()
    return user


def _deny():
    if request.path.startswith("/api/"):
        return _error(401, "login required")
    # No ``next`` parameter: nothing user-controlled ends up in the redirect.
    return redirect(url_for("auth.login_page"))


def login_required(view):
    """HTML routes redirect to /login, /api routes get a 401 JSON error."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return _deny()
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    """Like ``login_required``, and a 403 for users who are not admins."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return _deny()
        if user["role"] != "admin":
            if request.path.startswith("/api/"):
                return _error(403, "admin required")
            return make_response("admin required", 403)
        return view(*args, **kwargs)

    return wrapper


@bp.before_request
def _require_json():
    if request.method == "POST" and request.path.startswith("/auth/"):
        if not request.is_json:
            return _error(415, "Content-Type must be application/json")
    return None


def _json_body() -> dict | None:
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


def _log_in(user_id: int) -> None:
    session.clear()  # never keep anything from before the login (fixation)
    session.permanent = True
    session["user_id"] = user_id


def _log_verify_failure(what: str, e: Exception) -> None:
    """Log a failed verification; only the library's own rejections are routine."""
    expected = (InvalidRegistrationResponse, InvalidAuthenticationResponse)
    level = logging.INFO if isinstance(e, expected) else logging.WARNING
    log.log(level, "passkey %s failed: %s: %s", what, type(e).__name__, e)


def _options_response(options):
    response = make_response(options_to_json(options))
    response.mimetype = "application/json"
    return response


# --- pages -----------------------------------------------------------------


def _page(template: str, **context):
    response = make_response(render_template(template, **context))
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; frame-ancestors 'none'"
    )
    return response


@bp.get("/login")
def login_page():
    return _page("login.html")


@bp.get("/invite/<code>")
def invite_page(code: str):
    valid = users.invite_is_valid(get_db(), code, time.time())
    return _page("invite.html", code=code, valid=valid)


# --- registration ----------------------------------------------------------


@bp.post("/auth/register/options")
def register_options():
    config = current_app.config["HC"]
    session.pop("challenge_id", None)
    body = _json_body()
    if body is None:
        return _error(400, "body must be a JSON object")

    pending = {}
    exclude = []
    if "code" in body:
        # New user with an invite. The invite is checked but not redeemed yet.
        code, name = body["code"], body.get("name")
        if not isinstance(code, str) or not code:
            return _error(400, "invalid invite")
        name = name.strip() if isinstance(name, str) else name
        if not users.valid_name(name):
            return _error(
                400, f"name must be 1-{users.MAX_NAME_LENGTH} printable characters"
            )
        conn = get_db()
        if not users.invite_is_valid(conn, code, time.time()):
            return _error(400, "invite is invalid or has expired")
        if conn.execute("SELECT 1 FROM users WHERE name = ?", (name,)).fetchone():
            return _error(400, "that name is already taken")
        pending.update(invite_hash=users.hash_code(code), name=name)
        user_name = name
    else:
        # A logged-in user adds another passkey to their own account.
        user = current_user()
        if user is None:
            return _error(401, "login required")
        pending["user_id"] = user["id"]
        user_name = user["name"]
        exclude = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["id"]))
            for c in users.list_credentials(get_db(), user["id"])
        ]

    options = generate_registration_options(
        rp_id=config.rp_id,
        rp_name=config.site_name,
        user_name=user_name,
        # A random handle: a stable one would make some authenticators replace
        # an existing passkey of the same user instead of adding a new one.
        user_id=secrets.token_bytes(32),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=exclude,
    )
    session["challenge_id"] = challenges.create_challenge(
        get_db(), "register", options.challenge, time.time(), **pending
    )
    return _options_response(options)


@bp.post("/auth/register/verify")
def register_verify():
    config = current_app.config["HC"]
    conn = get_db()
    # Single use, whatever the outcome: the row is deleted by this call.
    pending = challenges.consume_challenge(
        conn, session.pop("challenge_id", None), "register", time.time()
    )
    body = _json_body()
    if pending is None or body is None:
        return _error(400, "no registration in progress")

    user = None
    if pending["invite_hash"] is None:
        # Adding a passkey: the challenge was issued to this very user.
        user = current_user()
        if user is None or user["id"] != pending["user_id"]:
            return _error(400, "no registration in progress")

    try:
        verified = verify_registration_response(
            credential=body,
            expected_challenge=bytes(pending["challenge"]),
            expected_rp_id=config.rp_id,
            expected_origin=config.origin,
        )
        cred_id = bytes_to_base64url(verified.credential_id)
    except Exception as e:
        _log_verify_failure("registration", e)
        return _error(400, "registration failed")
    if len(cred_id) > MAX_CREDENTIAL_ID_LENGTH:
        return _error(400, "registration failed")

    if pending["invite_hash"] is not None:
        try:
            user_id = users.register_with_invite(
                conn,
                pending["invite_hash"],
                pending["name"],
                cred_id,
                verified.credential_public_key,
                verified.sign_count,
                time.time(),
            )
        except users.RegistrationError as e:
            return _error(400, str(e))
        _log_in(user_id)
        return jsonify({"ok": True})

    try:
        users.add_credential(
            conn,
            user["id"],
            cred_id,
            verified.credential_public_key,
            verified.sign_count,
            "Passkey",
        )
    except sqlite3.IntegrityError:
        return _error(400, "that passkey is already registered")
    return jsonify({"ok": True})


# --- login -----------------------------------------------------------------


@bp.post("/auth/login/options")
def login_options():
    config = current_app.config["HC"]
    session.pop("challenge_id", None)
    options = generate_authentication_options(
        rp_id=config.rp_id,
        # Discoverable credentials: the passkey itself says who is logging in.
        allow_credentials=[],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    session["challenge_id"] = challenges.create_challenge(
        get_db(), "login", options.challenge, time.time()
    )
    return _options_response(options)


@bp.post("/auth/login/verify")
def login_verify():
    config = current_app.config["HC"]
    conn = get_db()
    # Single use, whatever the outcome: the row is deleted by this call.
    pending = challenges.consume_challenge(
        conn, session.pop("challenge_id", None), "login", time.time()
    )
    body = _json_body()
    if pending is None or body is None:
        return _error(400, "no login in progress")

    def failed():
        # One answer for unknown credentials and failed verification alike.
        return _error(401, "login failed")

    cred_id = body.get("id")
    if (
        not isinstance(cred_id, str)
        or not cred_id
        or len(cred_id) > MAX_CREDENTIAL_ID_LENGTH
        or body.get("rawId", cred_id) != cred_id
    ):
        return failed()
    cred = users.get_credential(conn, cred_id)
    if cred is None:
        return failed()
    try:
        verified = verify_authentication_response(
            credential=body,
            expected_challenge=bytes(pending["challenge"]),
            expected_rp_id=config.rp_id,
            expected_origin=config.origin,
            credential_public_key=bytes(cred["public_key"]),
            # The library accepts a counter of 0 from authenticators that do
            # not count, and rejects a non-increasing one otherwise.
            credential_current_sign_count=cred["sign_count"] or 0,
        )
    except Exception as e:
        _log_verify_failure("login", e)
        return failed()

    users.touch_credential(conn, cred_id, verified.new_sign_count, time.time())
    _log_in(cred["user_id"])
    return jsonify({"ok": True})


@bp.post("/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})
