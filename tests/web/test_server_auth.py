import base64
import inspect
import logging
import threading
import time
from types import SimpleNamespace

import pytest

pytest.importorskip("flask")
webauthn = pytest.importorskip("webauthn")

from hc_web import db, users  # noqa: E402
from hc_web.auth import admin_required, login_required  # noqa: E402
from hc_web.cli import main, parse_duration  # noqa: E402

DAY = 86400.0


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@pytest.fixture
def conn(config):
    c = db.connect(config.database)
    yield c
    c.close()


@pytest.fixture
def cfg(config, tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(f'origin = "http://localhost"\ndatabase = "{config.database}"\n')
    return str(path)


class Verifier:
    """Stands in for webauthn's verify_* functions."""

    def __init__(self):
        self.reg_calls = []
        self.auth_calls = []
        self.fail = False
        self.cred_id = b"cred-1"
        self.sign_count = 0
        self.new_sign_count = 1

    def verify_registration_response(self, **kwargs):
        # a wrong or missing keyword must fail here, as it would in production
        inspect.signature(webauthn.verify_registration_response).bind(**kwargs)
        self.reg_calls.append(kwargs)
        if self.fail:
            raise ValueError("bad attestation")
        return SimpleNamespace(
            credential_id=self.cred_id,
            credential_public_key=b"public-key",
            sign_count=self.sign_count,
        )

    def verify_authentication_response(self, **kwargs):
        inspect.signature(webauthn.verify_authentication_response).bind(**kwargs)
        self.auth_calls.append(kwargs)
        if self.fail:
            raise ValueError("bad assertion")
        return SimpleNamespace(new_sign_count=self.new_sign_count)


@pytest.fixture
def verifier(monkeypatch):
    v = Verifier()
    monkeypatch.setattr(
        "hc_web.auth.verify_registration_response", v.verify_registration_response
    )
    monkeypatch.setattr(
        "hc_web.auth.verify_authentication_response", v.verify_authentication_response
    )
    return v


def unb64u(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def post(client, url, body=None):
    return client.post(url, json={} if body is None else body)


def invite(conn, role="viewer", **kw):
    return users.create_invite(conn, role, None, **kw)


def register(client, code, name="alice", cred_id=b"cred-1"):
    """Run options + verify for an invite; return the verify response."""
    r = post(client, "/auth/register/options", {"code": code, "name": name})
    assert r.status_code == 200, r.get_json()
    return post(
        client,
        "/auth/register/verify",
        {"id": b64u(cred_id), "rawId": b64u(cred_id), "type": "public-key"},
    )


def add_user(conn, name="bob", role="viewer", cred_id="cred-b"):
    uid = users.create_user(conn, name, role)
    users.add_credential(conn, uid, cred_id, b"pk", 5, "test")
    return uid


def login_as(client, user_id):
    with client.session_transaction() as s:
        s["user_id"] = user_id


def user_count(conn):
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


# --- invites ---------------------------------------------------------------


def test_invite_single_use_and_expiry(conn):
    code = invite(conn, "admin")
    now = time.time()
    assert users.redeem_invite(conn, code, now) == "admin"
    assert users.redeem_invite(conn, code, now) is None
    assert users.redeem_invite(conn, "nonsense", now) is None

    old = invite(conn, "viewer")
    assert users.redeem_invite(conn, old, time.time() + 3 * DAY + 1) is None
    assert users.redeem_invite(conn, old, time.time()) == "viewer"


def test_invite_code_is_random_and_not_stored(conn):
    a, b = invite(conn), invite(conn)
    assert a != b
    assert len(a) >= 43  # token_urlsafe(32)
    rows = conn.execute("SELECT * FROM invites").fetchall()
    assert len(rows) == 2
    for row in rows:
        assert a not in tuple(row) and b not in tuple(row)


def test_invite_rejects_bad_role_and_lifetime(conn):
    with pytest.raises(ValueError):
        users.create_invite(conn, "root", None)
    with pytest.raises(ValueError):
        users.create_invite(conn, "viewer", None, expires_s=0)


def test_invite_url(config):
    assert users.invite_url(config, "abc") == "http://localhost/invite/abc"


def test_concurrent_redemption_only_one_wins(config, conn):
    code = invite(conn)
    results = []
    barrier = threading.Barrier(8)

    def worker():
        c = db.connect(config.database)
        try:
            barrier.wait()
            results.append(users.redeem_invite(c, code, time.time()))
        finally:
            c.close()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(r for r in results if r is not None) == ["viewer"]
    assert len(results) == 8


def test_delete_user_removes_credentials(conn):
    uid = add_user(conn)
    other = add_user(conn, "carol", cred_id="cred-c")
    users.delete_user(conn, uid)
    assert users.get_user(conn, uid) is None
    assert users.get_credential(conn, "cred-b") is None
    assert users.get_credential(conn, "cred-c") is not None
    assert [u["id"] for u in users.list_users(conn)] == [other]
    assert users.set_role(conn, other, "admin")
    assert users.get_user(conn, other)["role"] == "admin"
    assert not users.set_role(conn, 999, "admin")
    with pytest.raises(ValueError):
        users.set_role(conn, other, "root")


# --- registration ----------------------------------------------------------


def test_register_with_invite_creates_user_and_session(client, conn, verifier):
    code = invite(conn, "admin")
    assert client.get("/api/v1/status").status_code == 401

    r = post(client, "/auth/register/options", {"code": code, "name": "alice"})
    assert r.status_code == 200
    opts = r.get_json()
    assert opts["rp"]["id"] == "localhost"
    assert opts["authenticatorSelection"]["residentKey"] == "required"
    assert opts["authenticatorSelection"]["userVerification"] == "preferred"
    # the invite is validated but not yet redeemed
    assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is None
    assert user_count(conn) == 0

    r = post(client, "/auth/register/verify", {"id": b64u(b"cred-1")})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True

    call = verifier.reg_calls[0]
    assert call["expected_origin"] == "http://localhost"
    assert call["expected_rp_id"] == "localhost"
    assert call["expected_challenge"] == unb64u(opts["challenge"])

    user = conn.execute("SELECT * FROM users").fetchone()
    assert (user["name"], user["role"]) == ("alice", "admin")
    cred = users.get_credential(conn, b64u(b"cred-1"))
    assert cred["user_id"] == user["id"]
    assert bytes(cred["public_key"]) == b"public-key"
    assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is not None

    # logged in: the read API works with the cookie and no token
    assert client.get("/api/v1/status").status_code == 200


def test_register_role_and_user_id_come_from_invite_only(client, conn, verifier):
    code = invite(conn, "viewer")
    other = add_user(conn, "mallory")
    r = post(
        client,
        "/auth/register/options",
        {"code": code, "name": "alice", "role": "admin", "user_id": other},
    )
    assert r.status_code == 200
    r = post(
        client,
        "/auth/register/verify",
        {"id": b64u(b"cred-1"), "role": "admin", "user_id": other},
    )
    assert r.status_code == 200
    row = conn.execute("SELECT * FROM users WHERE name = 'alice'").fetchone()
    assert row["role"] == "viewer"
    with client.session_transaction() as s:
        assert s["user_id"] == row["id"] != other


def test_register_strips_name(client, conn, verifier):
    assert register(client, invite(conn), name="  alice  ").status_code == 200
    assert conn.execute("SELECT name FROM users").fetchone()[0] == "alice"


@pytest.mark.parametrize(
    "name", ["", "   ", "x" * 65, "a\nb", "a\x00b", 5, None, ["a"], {"a": 1}]
)
def test_register_rejects_bad_names(client, conn, verifier, name):
    code = invite(conn)
    r = post(client, "/auth/register/options", {"code": code, "name": name})
    assert r.status_code == 400
    assert "error" in r.get_json()
    assert user_count(conn) == 0
    assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is None


def test_register_missing_name_or_bad_body(client, conn, verifier):
    code = invite(conn)
    assert post(client, "/auth/register/options", {"code": code}).status_code == 400
    r = client.post(
        "/auth/register/options", data="[1]", content_type="application/json"
    )
    assert r.status_code == 400
    r = client.post(
        "/auth/register/options", data="{nope", content_type="application/json"
    )
    assert r.status_code == 400
    r = post(client, "/auth/register/options", {"code": 5, "name": "alice"})
    assert r.status_code == 400


def test_register_verify_without_options_400(client, conn, verifier):
    assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert verifier.reg_calls == []
    assert user_count(conn) == 0


def test_register_rejected_invite_creates_nothing(client, conn, verifier):
    expired = invite(conn)
    conn.execute("UPDATE invites SET expires = ?", (time.time() - 1,))
    conn.commit()
    used = invite(conn)
    users.redeem_invite(conn, used, time.time())

    for code in (expired, used, "unknown-code"):
        r = post(client, "/auth/register/options", {"code": code, "name": "alice"})
        assert r.status_code == 400
        assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert user_count(conn) == 0
    assert verifier.reg_calls == []


def test_register_options_without_code_needs_login(client, verifier):
    r = post(client, "/auth/register/options", {})
    assert r.status_code == 401


def test_register_verify_failure_keeps_invite_usable(client, conn, verifier):
    code = invite(conn)
    verifier.fail = True
    r = post(client, "/auth/register/options", {"code": code, "name": "alice"})
    assert r.status_code == 200
    assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert user_count(conn) == 0
    assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is None
    with client.session_transaction() as s:
        assert "user_id" not in s

    verifier.fail = False
    assert register(client, code).status_code == 200
    assert user_count(conn) == 1


def test_register_challenge_not_reusable(client, conn, verifier):
    code = invite(conn)
    verifier.fail = True
    post(client, "/auth/register/options", {"code": code, "name": "alice"})
    assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 400
    # the challenge was consumed by the failed attempt
    verifier.fail = False
    assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert len(verifier.reg_calls) == 1
    assert user_count(conn) == 0


def test_register_second_redemption_fails(server_app, conn, verifier):
    code = invite(conn)
    c1, c2 = server_app.test_client(), server_app.test_client()
    for c, name in ((c1, "alice"), (c2, "bob")):
        r = post(c, "/auth/register/options", {"code": code, "name": name})
        assert r.status_code == 200  # both pass options: nothing is redeemed yet
    assert post(c1, "/auth/register/verify", {"id": "x"}).status_code == 200
    verifier.cred_id = b"cred-2"
    assert post(c2, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert [u["name"] for u in users.list_users(conn)] == ["alice"]
    with c2.session_transaction() as s:
        assert "user_id" not in s


def test_register_credential_id_collision_400(client, server_app, conn, verifier):
    add_user(conn, "bob", cred_id=b64u(b"cred-1"))
    code = invite(conn)
    r = register(client, code, name="alice", cred_id=b"cred-1")
    assert r.status_code == 400
    assert user_count(conn) == 1
    # nothing was created and the invite is still usable
    assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is None
    verifier.cred_id = b"cred-2"
    assert register(client, code, name="alice", cred_id=b"cred-2").status_code == 200


def test_register_name_taken_400(client, conn, verifier):
    add_user(conn, "alice")
    code = invite(conn)
    r = post(client, "/auth/register/options", {"code": code, "name": "alice"})
    assert r.status_code == 400
    assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is None


def test_register_name_taken_between_options_and_verify(
    server_app, client, conn, verifier
):
    code = invite(conn)
    post(client, "/auth/register/options", {"code": code, "name": "alice"})
    add_user(conn, "alice")
    r = post(client, "/auth/register/verify", {"id": "x"})
    assert r.status_code == 400
    assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is None
    assert user_count(conn) == 1


def test_register_session_fixation_cleared(client, conn, verifier):
    code = invite(conn)
    with client.session_transaction() as s:
        s["junk"] = "attacker"
    assert register(client, code).status_code == 200
    with client.session_transaction() as s:
        assert "junk" not in s
        assert s.permanent


def test_add_passkey_when_logged_in(client, conn, verifier):
    uid = add_user(conn, "bob", "viewer", cred_id=b64u(b"cred-b"))
    login_as(client, uid)
    r = post(client, "/auth/register/options", {"role": "admin", "name": "evil"})
    assert r.status_code == 200
    excluded = [c["id"] for c in r.get_json().get("excludeCredentials", [])]
    assert excluded == [b64u(b"cred-b")]
    verifier.cred_id = b"cred-new"
    r = post(client, "/auth/register/verify", {"id": "x", "role": "admin"})
    assert r.status_code == 200
    assert user_count(conn) == 1
    cred = users.get_credential(conn, b64u(b"cred-new"))
    assert cred["user_id"] == uid
    assert users.get_user(conn, uid)["role"] == "viewer"


def test_add_passkey_requires_same_user_at_verify(server_app, conn, verifier):
    uid = add_user(conn, "bob")
    other = add_user(conn, "carol", cred_id="cred-c")
    c = server_app.test_client()
    login_as(c, uid)
    post(c, "/auth/register/options", {})
    login_as(c, other)  # session swapped between options and verify
    assert post(c, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert users.get_credential(conn, b64u(b"cred-1")) is None


# --- login -----------------------------------------------------------------


def test_login_sets_30_day_permanent_session(client, server_app, conn, verifier):
    uid = add_user(conn, cred_id=b64u(b"cred-b"))
    r = post(client, "/auth/login/options")
    assert r.status_code == 200
    opts = r.get_json()
    assert opts["rpId"] == "localhost"
    assert opts.get("allowCredentials", []) == []

    r = post(client, "/auth/login/verify", {"id": b64u(b"cred-b"), "type": "x"})
    assert r.status_code == 200
    call = verifier.auth_calls[0]
    assert call["expected_challenge"] == unb64u(opts["challenge"])
    assert call["expected_origin"] == "http://localhost"
    assert call["expected_rp_id"] == "localhost"
    assert call["credential_public_key"] == b"pk"
    assert call["credential_current_sign_count"] == 5

    with client.session_transaction() as s:
        assert s["user_id"] == uid
        assert s.permanent
    assert server_app.permanent_session_lifetime.total_seconds() == 30 * DAY
    cookie = r.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Expires=" in cookie
    assert client.get("/api/v1/status").status_code == 200


def test_cookie_secure_by_default(config, tmp_path):
    from dataclasses import replace

    from hc_web.app import create_app

    app = create_app(replace(config, secure_cookies=True))
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["PERMANENT_SESSION_LIFETIME"].total_seconds() == 30 * DAY


def test_login_updates_sign_count_and_last_used(client, conn, verifier):
    add_user(conn, cred_id=b64u(b"cred-b"))
    verifier.new_sign_count = 9
    post(client, "/auth/login/options")
    before = time.time()
    assert (
        post(client, "/auth/login/verify", {"id": b64u(b"cred-b")}).status_code == 200
    )
    cred = users.get_credential(conn, b64u(b"cred-b"))
    assert cred["sign_count"] == 9
    assert cred["last_used"] >= before


def test_login_authenticator_with_zero_sign_count(client, conn, verifier):
    uid = users.create_user(conn, "bob", "viewer")
    users.add_credential(conn, uid, b64u(b"cred-b"), b"pk", 0, "t")
    verifier.new_sign_count = 0
    post(client, "/auth/login/options")
    assert (
        post(client, "/auth/login/verify", {"id": b64u(b"cred-b")}).status_code == 200
    )
    assert verifier.auth_calls[0]["credential_current_sign_count"] == 0
    assert users.get_credential(conn, b64u(b"cred-b"))["sign_count"] == 0


def test_login_unknown_credential_generic_failure(client, conn, verifier):
    add_user(conn, cred_id=b64u(b"cred-b"))
    post(client, "/auth/login/options")
    unknown = post(client, "/auth/login/verify", {"id": b64u(b"nobody")})
    assert unknown.status_code == 401
    assert verifier.auth_calls == []

    verifier.fail = True
    post(client, "/auth/login/options")
    failed = post(client, "/auth/login/verify", {"id": b64u(b"cred-b")})
    assert failed.status_code == unknown.status_code
    assert failed.get_json() == unknown.get_json()
    with client.session_transaction() as s:
        assert "user_id" not in s


@pytest.mark.parametrize(
    "body, status",
    [({}, 401), ({"id": 5}, 401), ({"id": None}, 401), ([], 400), ("x", 400)],
)
def test_login_malformed_credential(client, conn, verifier, body, status):
    post(client, "/auth/login/options")
    r = client.post("/auth/login/verify", json=body)
    assert r.status_code == status
    assert verifier.auth_calls == []


def test_login_verify_without_options_400(client, conn, verifier):
    add_user(conn, cred_id=b64u(b"cred-b"))
    r = post(client, "/auth/login/verify", {"id": b64u(b"cred-b")})
    assert r.status_code == 400
    assert verifier.auth_calls == []


def test_login_challenge_not_reusable(client, conn, verifier):
    add_user(conn, cred_id=b64u(b"cred-b"))
    post(client, "/auth/login/options")
    verifier.fail = True
    post(client, "/auth/login/verify", {"id": b64u(b"cred-b")})
    verifier.fail = False
    r = post(client, "/auth/login/verify", {"id": b64u(b"cred-b")})
    assert r.status_code == 400
    assert len(verifier.auth_calls) == 1


def test_login_clears_old_session(client, conn, verifier):
    old = add_user(conn, "old", cred_id="cred-old")
    new = add_user(conn, cred_id=b64u(b"cred-b"))
    login_as(client, old)
    with client.session_transaction() as s:
        s["junk"] = "attacker"
    post(client, "/auth/login/options")
    assert (
        post(client, "/auth/login/verify", {"id": b64u(b"cred-b")}).status_code == 200
    )
    with client.session_transaction() as s:
        assert "junk" not in s
        assert "challenge_id" not in s
        assert s["user_id"] == new


def test_deleted_user_session_cleared(client, conn):
    uid = add_user(conn)
    login_as(client, uid)
    assert client.get("/api/v1/status").status_code == 200
    users.delete_user(conn, uid)
    assert client.get("/api/v1/status").status_code == 401
    with client.session_transaction() as s:
        assert "user_id" not in s


# --- logout, CSRF guard, decorators ---------------------------------------


def test_logout_clears_session(client, conn):
    uid = add_user(conn)
    login_as(client, uid)
    with client.session_transaction() as s:
        s["junk"] = 1
    r = post(client, "/auth/logout")
    assert r.status_code == 200
    with client.session_transaction() as s:
        assert dict(s) == {}
    assert client.get("/api/v1/status").status_code == 401


def test_form_post_rejected_415(client, conn, verifier):
    uid = add_user(conn)
    login_as(client, uid)
    for url in (
        "/auth/logout",
        "/auth/register/options",
        "/auth/register/verify",
        "/auth/login/options",
        "/auth/login/verify",
    ):
        r = client.post(url, data={"a": "b"})
        assert r.status_code == 415, url
        r = client.post(url, data="{}", content_type="text/plain")
        assert r.status_code == 415, url
        r = client.post(url)
        assert r.status_code == 415, url
    # the session survived the rejected logout attempts
    assert client.get("/api/v1/status").status_code == 200


def test_auth_routes_only_accept_post(client):
    for url in ("/auth/logout", "/auth/login/options", "/auth/register/verify"):
        assert client.get(url).status_code == 405


@pytest.fixture
def guarded(server_app):
    @server_app.get("/_t/page")
    @login_required
    def page():
        return "page"

    @server_app.get("/api/_t/data")
    @login_required
    def api_data():
        return {"ok": True}

    @server_app.get("/_t/admin")
    @admin_required
    def admin_page():
        return "admin"

    @server_app.get("/api/_t/admin")
    @admin_required
    def admin_api():
        return {"ok": True}

    return server_app


def test_login_required_redirects_html_and_401_api(guarded, client):
    r = client.get("/_t/page")
    assert r.status_code == 302
    assert r.headers["Location"] == "/login"
    r = client.get("/api/_t/data")
    assert r.status_code == 401
    assert "error" in r.get_json()
    r = client.get("/_t/admin")
    assert r.status_code == 302
    assert r.headers["Location"] == "/login"
    assert client.get("/api/_t/admin").status_code == 401


def test_login_required_ignores_attacker_next(guarded, client):
    r = client.get("/_t/page?next=https://evil.example/")
    assert r.headers["Location"] == "/login"


def test_admin_required_403_for_viewer(guarded, client, conn):
    viewer = add_user(conn, "viewer", "viewer", "c1")
    admin = add_user(conn, "boss", "admin", "c2")
    login_as(client, viewer)
    assert client.get("/_t/page").status_code == 200
    assert client.get("/_t/admin").status_code == 403
    assert client.get("/api/_t/admin").status_code == 403
    login_as(client, admin)
    assert client.get("/_t/admin").status_code == 200
    assert client.get("/api/_t/admin").status_code == 200


# --- pages -----------------------------------------------------------------


def test_login_page(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert b"webauthn.js" in r.data
    assert b'type="password"' not in r.data
    for path in ("/static/webauthn.js", "/static/hcweb.css"):
        with client.get(path) as static:  # closing frees the served file
            assert static.status_code == 200


def test_invite_page(client, conn):
    code = invite(conn)
    r = client.get(f"/invite/{code}")
    assert r.status_code == 200
    assert code.encode() in r.data
    assert r.headers["Referrer-Policy"] == "no-referrer"
    assert "no-store" in r.headers["Cache-Control"]
    # viewing the page does not redeem the invite
    assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is None


def test_invite_page_unknown_or_used_code(client, conn):
    code = invite(conn)
    users.redeem_invite(conn, code, time.time())
    for c in (code, "nope"):
        r = client.get(f"/invite/{c}")
        assert r.status_code == 200
        assert b"invalid or has expired" in r.data
        assert b'id="invite-form"' not in r.data


def test_invite_page_escapes_code(client):
    r = client.get("/invite/%3Cscript%3Ealert(1)%3C%2Fscript%3E")
    assert b"<script>alert" not in r.data


# --- CLI -------------------------------------------------------------------


def test_cli_invite_prints_url(config, cfg, capsys, conn):
    assert main(["invite", "--admin", "--config", cfg]) == 0
    url = capsys.readouterr().out.strip()
    assert url.startswith("http://localhost/invite/")
    code = url.rsplit("/", 1)[1]
    row = conn.execute("SELECT * FROM invites").fetchone()
    assert row["created_by"] is None
    assert row["role"] == "admin"
    assert row["expires"] - row["created"] == pytest.approx(3 * DAY, abs=5)
    assert users.redeem_invite(conn, code, time.time()) == "admin"


def test_cli_invite_defaults_to_viewer_and_expiry(config, cfg, capsys, conn):
    assert main(["invite", "--expires=2h", "--config", cfg]) == 0
    capsys.readouterr()
    row = conn.execute("SELECT * FROM invites").fetchone()
    assert row["role"] == "viewer"
    assert row["expires"] - row["created"] == pytest.approx(7200, abs=5)


@pytest.mark.parametrize(
    "bad",
    ["", "3", "d", "3x", "-1d", "0d", "0m", "1.5d", "3 d", "abc", "٣d", "9999999d"],
)
def test_cli_invite_bad_duration(cfg, capsys, conn, bad):
    assert main(["invite", f"--expires={bad}", "--config", cfg]) != 0
    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert conn.execute("SELECT COUNT(*) FROM invites").fetchone()[0] == 0


def test_parse_duration():
    assert parse_duration("3d") == 3 * DAY
    assert parse_duration("12h") == 12 * 3600
    assert parse_duration("90m") == 5400
    for bad in ("", "3", "x", "0d", "-2h", "1w", "1.5h", " 3d", "3d "):
        with pytest.raises(ValueError):
            parse_duration(bad)


def test_real_verifiers_reject_garbage_cleanly(client, conn):
    """Without the monkeypatch the real py_webauthn rejects forged input."""
    code = invite(conn)
    post(client, "/auth/register/options", {"code": code, "name": "alice"})
    r = post(client, "/auth/register/verify", {"id": "x", "response": {}})
    assert r.status_code == 400
    assert user_count(conn) == 0
    assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is None

    add_user(conn, cred_id=b64u(b"cred-b"))
    post(client, "/auth/login/options")
    r = post(client, "/auth/login/verify", {"id": b64u(b"cred-b"), "response": {}})
    assert r.status_code == 401


# --- verifier arguments, challenge source, logging --------------------------


def test_register_challenge_comes_from_store_not_body(client, conn, verifier):
    code = invite(conn)
    r = post(client, "/auth/register/options", {"code": code, "name": "alice"})
    stored = unb64u(r.get_json()["challenge"])
    r = post(client, "/auth/register/verify", {"id": "x", "challenge": b64u(b"evil")})
    assert r.status_code == 200
    assert verifier.reg_calls[0]["expected_challenge"] == stored


def test_login_challenge_comes_from_store_not_body(client, conn, verifier):
    add_user(conn, cred_id=b64u(b"cred-b"))
    r = post(client, "/auth/login/options")
    stored = unb64u(r.get_json()["challenge"])
    body = {"id": b64u(b"cred-b"), "challenge": b64u(b"evil")}
    assert post(client, "/auth/login/verify", body).status_code == 200
    assert verifier.auth_calls[0]["expected_challenge"] == stored


def test_programming_errors_in_verify_are_logged_as_warnings(
    client, conn, monkeypatch, caplog
):
    def broken(**kwargs):
        raise TypeError("unexpected keyword")

    monkeypatch.setattr("hc_web.auth.verify_registration_response", broken)
    monkeypatch.setattr("hc_web.auth.verify_authentication_response", broken)
    code = invite(conn)
    add_user(conn, cred_id=b64u(b"cred-b"))
    with caplog.at_level(logging.INFO, logger="hc_web.auth"):
        post(client, "/auth/register/options", {"code": code, "name": "alice"})
        assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 400
        post(client, "/auth/login/options")
        r = post(client, "/auth/login/verify", {"id": b64u(b"cred-b")})
        assert r.status_code == 401
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert all("TypeError" in r.getMessage() for r in warnings)


def client_data(origin: str, **extra) -> str:
    import json

    return b64u(
        json.dumps({"type": "webauthn.get", "origin": origin, **extra}).encode()
    )


def test_library_rejections_are_warnings_with_both_origins(
    client, conn, monkeypatch, caplog
):
    from webauthn.helpers.exceptions import InvalidAuthenticationResponse

    def rejected(**kwargs):
        raise InvalidAuthenticationResponse("Unexpected client data origin")

    monkeypatch.setattr("hc_web.auth.verify_authentication_response", rejected)
    add_user(conn, cred_id=b64u(b"cred-b"))
    body = {
        "id": b64u(b"cred-b"),
        "response": {
            "clientDataJSON": client_data(
                "https://wrong.example.org", challenge="s3cret"
            )
        },
    }
    with caplog.at_level(logging.INFO, logger="hc_web.auth"):
        post(client, "/auth/login/options")
        post(client, "/auth/login/verify", body)
    assert [r.levelno for r in caplog.records] == [logging.WARNING]
    message = caplog.records[0].getMessage()
    assert "InvalidAuthenticationResponse" in message
    assert "expected origin 'http://localhost'" in message
    assert "reported origin 'https://wrong.example.org'" in message
    assert "s3cret" not in message  # the challenge is not logged


@pytest.mark.parametrize(
    "response",
    [
        None,
        "text",
        {},
        {"clientDataJSON": 5},
        {"clientDataJSON": "!!!not base64!!!"},
        {"clientDataJSON": b64u(b"not json")},
        {"clientDataJSON": b64u(b"[1, 2]")},
        {"clientDataJSON": b64u(b'{"origin": 7}')},
    ],
)
def test_an_unreadable_client_data_is_logged_as_unknown(
    client, conn, monkeypatch, caplog, response
):
    from webauthn.helpers.exceptions import InvalidAuthenticationResponse

    def rejected(**kwargs):
        raise InvalidAuthenticationResponse("bad")

    monkeypatch.setattr("hc_web.auth.verify_authentication_response", rejected)
    add_user(conn, cred_id=b64u(b"cred-b"))
    with caplog.at_level(logging.INFO, logger="hc_web.auth"):
        post(client, "/auth/login/options")
        r = post(
            client, "/auth/login/verify", {"id": b64u(b"cred-b"), "response": response}
        )
    assert r.status_code == 401
    assert "reported origin unknown" in caplog.records[-1].getMessage()


def test_a_reported_origin_cannot_inject_log_lines(client, conn, monkeypatch, caplog):
    from webauthn.helpers.exceptions import InvalidAuthenticationResponse

    def rejected(**kwargs):
        raise InvalidAuthenticationResponse("bad")

    monkeypatch.setattr("hc_web.auth.verify_authentication_response", rejected)
    add_user(conn, cred_id=b64u(b"cred-b"))
    evil = "https://x.org\nERROR forged line" + "A" * 1000
    body = {"id": b64u(b"cred-b"), "response": {"clientDataJSON": client_data(evil)}}
    with caplog.at_level(logging.INFO, logger="hc_web.auth"):
        post(client, "/auth/login/options")
        post(client, "/auth/login/verify", body)
    message = caplog.records[-1].getMessage()
    assert "\n" not in message
    assert len(message) < 500


def test_registration_failures_report_the_origin_too(client, conn, monkeypatch, caplog):
    from webauthn.helpers.exceptions import InvalidRegistrationResponse

    def rejected(**kwargs):
        raise InvalidRegistrationResponse("bad")

    monkeypatch.setattr("hc_web.auth.verify_registration_response", rejected)
    code = invite(conn)
    body = {
        "id": "x",
        "response": {"clientDataJSON": client_data("https://wrong.example.org")},
    }
    with caplog.at_level(logging.INFO, logger="hc_web.auth"):
        post(client, "/auth/register/options", {"code": code, "name": "alice"})
        assert post(client, "/auth/register/verify", body).status_code == 400
    assert [r.levelno for r in caplog.records] == [logging.WARNING]
    assert (
        "reported origin 'https://wrong.example.org'" in caplog.records[0].getMessage()
    )


# --- server-side challenge store -------------------------------------------


def session_cookie(client) -> str:
    return client.get_cookie("session").value


def replayed_client(server_app, cookie: str):
    c = server_app.test_client()
    c.set_cookie("session", cookie, domain="localhost")
    return c


def test_session_holds_only_a_challenge_id(server_app, client, conn, verifier):
    code = invite(conn)
    post(client, "/auth/register/options", {"code": code, "name": "alice"})
    serializer = server_app.session_interface.get_signing_serializer(server_app)
    data = serializer.loads(session_cookie(client))
    assert list(data) == ["challenge_id"]
    assert code not in str(data)
    # the table holds only the hash of the code
    row = conn.execute("SELECT * FROM challenges").fetchone()
    assert code not in [str(v) for v in tuple(row)]
    assert row["invite_hash"] == users.hash_code(code)
    assert row["name"] == "alice"
    assert row["purpose"] == "register"
    assert row["expires"] == pytest.approx(time.time() + 300, abs=5)


def test_register_verify_replay_with_old_cookie_fails(
    server_app, client, conn, verifier
):
    code = invite(conn)
    post(client, "/auth/register/options", {"code": code, "name": "alice"})
    old = session_cookie(client)
    assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 200
    replay = replayed_client(server_app, old)
    assert post(replay, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert len(verifier.reg_calls) == 1
    assert user_count(conn) == 1
    assert conn.execute("SELECT COUNT(*) FROM challenges").fetchone()[0] == 0


def test_login_verify_replay_with_old_cookie_fails(server_app, client, conn, verifier):
    uid = add_user(conn, cred_id=b64u(b"cred-b"))
    post(client, "/auth/login/options")
    old = session_cookie(client)
    body = {"id": b64u(b"cred-b")}
    assert post(client, "/auth/login/verify", body).status_code == 200
    replay = replayed_client(server_app, old)
    assert post(replay, "/auth/login/verify", body).status_code == 400
    assert len(verifier.auth_calls) == 1
    with replay.session_transaction() as s:
        assert "user_id" not in s
    assert uid


def test_failed_verify_consumes_challenge_even_when_cookie_replayed(
    server_app, client, conn, verifier
):
    add_user(conn, cred_id=b64u(b"cred-b"))
    post(client, "/auth/login/options")
    old = session_cookie(client)
    verifier.fail = True
    assert post(client, "/auth/login/verify", {"id": "z"}).status_code == 401
    verifier.fail = False
    replay = replayed_client(server_app, old)
    assert (
        post(replay, "/auth/login/verify", {"id": b64u(b"cred-b")}).status_code == 400
    )
    assert verifier.auth_calls == []


def test_expired_challenge_rejected(client, conn, verifier, monkeypatch):
    now = [time.time()]
    monkeypatch.setattr("hc_web.auth.time.time", lambda: now[0])
    code = invite(conn)
    add_user(conn, cred_id=b64u(b"cred-b"))

    post(client, "/auth/register/options", {"code": code, "name": "alice"})
    now[0] += 301
    assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert verifier.reg_calls == []

    post(client, "/auth/login/options")
    now[0] += 301
    assert (
        post(client, "/auth/login/verify", {"id": b64u(b"cred-b")}).status_code == 400
    )
    assert verifier.auth_calls == []

    # inside the lifetime it still works, and the invite was never burnt
    post(client, "/auth/register/options", {"code": code, "name": "alice"})
    now[0] += 299
    assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 200


def test_challenge_purpose_mismatch(server_app, client, conn, verifier):
    add_user(conn, cred_id=b64u(b"cred-b"))
    # a login challenge is useless at register/verify
    post(client, "/auth/login/options")
    cookie = session_cookie(client)
    assert post(client, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert verifier.reg_calls == []
    # ... and it was consumed by the attempt
    replay = replayed_client(server_app, cookie)
    assert (
        post(replay, "/auth/login/verify", {"id": b64u(b"cred-b")}).status_code == 400
    )

    # a register challenge is useless at login/verify
    code = invite(conn)
    post(client, "/auth/register/options", {"code": code, "name": "alice"})
    assert (
        post(client, "/auth/login/verify", {"id": b64u(b"cred-b")}).status_code == 400
    )
    assert verifier.auth_calls == []
    assert user_count(conn) == 1


def test_add_passkey_challenge_bound_to_user_in_store(server_app, conn, verifier):
    uid = add_user(conn, "bob")
    other = add_user(conn, "carol", cred_id="cred-c")
    c = server_app.test_client()
    login_as(c, uid)
    post(c, "/auth/register/options", {})
    row = conn.execute("SELECT * FROM challenges").fetchone()
    assert row["user_id"] == uid
    assert row["invite_hash"] is None
    login_as(c, other)
    assert post(c, "/auth/register/verify", {"id": "x"}).status_code == 400
    assert verifier.reg_calls == []


def test_expired_challenges_deleted_when_new_one_is_created(client, conn, verifier):
    with conn:
        conn.execute(
            "INSERT INTO challenges (id, challenge, purpose, expires) "
            "VALUES ('old', x'00', 'login', ?)",
            (time.time() - 1,),
        )
    post(client, "/auth/login/options")
    ids = [r[0] for r in conn.execute("SELECT id FROM challenges")]
    assert "old" not in ids
    assert len(ids) == 1


# --- credential id length ---------------------------------------------------


@pytest.mark.parametrize("size, status", [(1023, 200), (1050, 200), (1051, 400)])
def test_register_credential_id_length_cap(client, conn, verifier, size, status):
    from hc_web.auth import MAX_CREDENTIAL_ID_LENGTH

    assert MAX_CREDENTIAL_ID_LENGTH == 1400
    cred = b"\x01" * size
    verifier.cred_id = cred
    code = invite(conn)
    r = register(client, code, cred_id=cred)
    assert r.status_code == status
    if status == 400:
        assert user_count(conn) == 0
        assert conn.execute("SELECT used_at FROM invites").fetchone()[0] is None


def test_longest_registrable_credential_id_can_log_in(server_app, conn, verifier):
    cred = b"\x02" * 1050  # 1400 base64url characters
    verifier.cred_id = cred
    c = server_app.test_client()
    assert register(c, invite(conn), cred_id=cred).status_code == 200
    c2 = server_app.test_client()
    post(c2, "/auth/login/options")
    assert post(c2, "/auth/login/verify", {"id": b64u(cred)}).status_code == 200
