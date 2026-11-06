import re
import threading
import time

import pytest

pytest.importorskip("flask")
pytest.importorskip("webauthn")

from hc_web import db, users  # noqa: E402
from hc_web.tokens import check_token, create_token  # noqa: E402

# the login helpers of the auth tests, not duplicated here
from .test_server_auth import add_user, login_as  # noqa: E402

JSON = {"Content-Type": "application/json"}


@pytest.fixture
def conn(config):
    c = db.connect(config.database)
    yield c
    c.close()


@pytest.fixture
def admin(client, conn):
    uid = add_user(conn, "boss", "admin", "cred-boss")
    login_as(client, uid)
    return uid


def post(client, url, body=None):
    return client.post(url, json={} if body is None else body)


def role_of(conn, uid):
    return conn.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()[0]


def admin_count(conn):
    return conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]


GET_ROUTES = ["/admin", "/admin/api/users", "/admin/api/tokens", "/admin/api/warnings"]
POST_ROUTES = [
    "/admin/api/invite",
    "/admin/api/users/1/role",
    "/admin/api/users/1/delete",
    "/admin/api/tokens",
    "/admin/api/tokens/1/revoke",
]


# --- access control ----------------------------------------------------------


def test_viewer_gets_403(client, conn):
    login_as(client, add_user(conn, "vera", "viewer", "cred-v"))
    for url in GET_ROUTES:
        assert client.get(url).status_code == 403, url
    for url in POST_ROUTES:
        assert post(client, url, {"role": "viewer"}).status_code == 403, url


def test_unauthenticated_redirects_html_and_401_json(client):
    r = client.get("/admin")
    assert r.status_code == 302
    assert r.headers["Location"] == "/login"
    for url in GET_ROUTES[1:]:
        r = client.get(url)
        assert r.status_code == 401, url
        assert "error" in r.get_json()
    for url in POST_ROUTES:
        r = post(client, url, {"role": "viewer"})
        assert r.status_code == 401, url
        assert "error" in r.get_json()


def test_token_alone_does_not_grant_admin(client, conn):
    for scope in ("read", "write"):
        token = create_token(conn, "B", "pc", scope)
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/admin", headers=headers).status_code == 302
        for url in GET_ROUTES[1:]:
            assert client.get(url, headers=headers).status_code == 401, url
        r = client.post("/admin/api/tokens", json={}, headers=headers)
        assert r.status_code == 401


def test_deleted_user_session_stops_working(client, conn, admin):
    other = add_user(conn, "other", "admin", "cred-o")
    assert client.get("/admin/api/users").status_code == 200
    users.delete_user(conn, admin)
    assert client.get("/admin/api/users").status_code == 401
    assert other


@pytest.mark.parametrize("url", POST_ROUTES)
@pytest.mark.parametrize(
    "kwargs",
    [
        {"data": {"role": "viewer"}},  # an HTML form
        {"data": "{}", "headers": {"Content-Type": "text/plain"}},
        {"data": "{}"},
    ],
)
def test_post_requires_json_content_type(client, conn, admin, url, kwargs):
    before = (
        admin_count(conn),
        conn.execute("SELECT COUNT(*) FROM invites").fetchone()[0],
    )
    r = client.post(url, **kwargs)
    assert r.status_code == 415
    assert "error" in r.get_json()
    assert before == (
        admin_count(conn),
        conn.execute("SELECT COUNT(*) FROM invites").fetchone()[0],
    )


def test_form_post_415_before_login_check(client):
    # the content-type guard comes first, whoever the caller is
    assert client.post("/admin/api/invite", data={"role": "admin"}).status_code == 415


@pytest.mark.parametrize("url", POST_ROUTES)
@pytest.mark.parametrize("body", ["[]", '"x"', "3", "null", "not json"])
def test_post_body_must_be_an_object(client, admin, url, body):
    r = client.post(url, data=body, headers=JSON)
    assert r.status_code == 400
    assert "error" in r.get_json()


# --- page --------------------------------------------------------------------


def test_admin_page(client, admin):
    r = client.get("/admin")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["Content-Security-Policy"] == (
        "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    )
    html = r.get_data(as_text=True)
    assert "/static/admin.js" in html
    # no inline scripts, handlers or styles: the CSP forbids them
    assert not re.search(r"<script(?![^>]*\ssrc=)", html)
    assert not re.search(r"\son\w+\s*=", html)
    assert "style=" not in html
    assert "<script src=" in html
    with client.get("/static/admin.js") as static:
        assert static.status_code == 200


def test_admin_page_inlines_no_server_data(client, conn, admin):
    evil = "<script>alert(1)</script>"
    add_user(conn, evil, "viewer", "cred-evil")
    create_token(conn, "B", evil.replace("/", "x"), "read")
    html = client.get("/admin").get_data(as_text=True)
    assert "alert(1)" not in html
    assert "boss" not in html


def test_admin_js_never_uses_innerhtml(client):
    with client.get("/static/admin.js") as r:
        js = r.get_data(as_text=True)
    for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert forbidden not in js


def test_admin_api_responses_not_cached(client, admin):
    for url in GET_ROUTES[1:]:
        assert client.get(url).headers["Cache-Control"] == "no-store"
    assert (
        post(client, "/admin/api/invite", {"role": "viewer"}).headers["Cache-Control"]
        == "no-store"
    )


# --- users -------------------------------------------------------------------


def test_list_users_with_credentials(client, conn, admin):
    users.touch_credential(conn, "cred-boss", 7, 1234.0)
    users.add_credential(conn, admin, "cred-2", b"secret-key-bytes", 0, "Phone")
    data = client.get("/admin/api/users").get_json()
    assert data["current_user"] == admin
    [boss] = data["users"]
    assert boss["id"] == admin
    assert boss["name"] == "boss"
    assert boss["role"] == "admin"
    assert isinstance(boss["created"], float)
    creds = {c["label"]: c for c in boss["credentials"]}
    assert set(creds) == {"test", "Phone"}
    assert creds["test"]["last_used"] == 1234.0
    assert creds["Phone"]["last_used"] is None
    assert isinstance(creds["Phone"]["created"], float)


def test_credential_secrets_not_exposed(client, conn, admin):
    users.add_credential(conn, admin, "cred-2", b"secret-key-bytes", 9, "Phone")
    r = client.get("/admin/api/users")
    text = r.get_data(as_text=True)
    assert "public_key" not in text
    assert "secret-key-bytes" not in text
    assert "c2VjcmV0" not in text  # base64 of the key
    assert "cred-2" not in text
    assert "cred-boss" not in text
    for u in r.get_json()["users"]:
        for c in u["credentials"]:
            assert set(c) == {"label", "created", "last_used"}


def test_user_named_like_a_script_only_via_json(client, conn, admin):
    evil = "<script>alert(1)</script>"
    uid = users.create_user(conn, evil, "viewer")
    r = client.get("/admin/api/users")
    assert r.mimetype == "application/json"
    assert {u["id"]: u["name"] for u in r.get_json()["users"]}[uid] == evil
    assert "alert(1)" not in client.get("/admin").get_data(as_text=True)


# --- invites -----------------------------------------------------------------


def test_admin_creates_invite_url(client, conn, admin, config):
    r = post(client, "/admin/api/invite", {"role": "viewer"})
    assert r.status_code == 200
    url = r.get_json()["url"]
    assert set(r.get_json()) == {"url"}
    assert url.startswith(config.origin.rstrip("/") + "/invite/")
    code = url.rsplit("/", 1)[1]
    assert users.invite_is_valid(conn, code, time.time())
    row = conn.execute("SELECT role, created_by FROM invites").fetchone()
    assert tuple(row) == ("viewer", admin)
    # the link opens the registration page
    assert client.get(f"/invite/{code}").status_code == 200

    code = post(client, "/admin/api/invite", {"role": "admin"}).get_json()["url"]
    assert conn.execute("SELECT role FROM invites ORDER BY id DESC").fetchone()[0] == (
        "admin"
    )
    assert code


@pytest.mark.parametrize("role", ["root", "", "ADMIN", None, 3, ["admin"], {}])
def test_invite_rejects_bad_role(client, conn, admin, role):
    r = post(client, "/admin/api/invite", {"role": role})
    assert r.status_code == 400
    assert "error" in r.get_json()
    assert conn.execute("SELECT COUNT(*) FROM invites").fetchone()[0] == 0
    assert post(client, "/admin/api/invite").status_code == 400  # missing role


# --- roles and deletion ------------------------------------------------------


def test_change_role(client, conn, admin):
    bob = add_user(conn, "bob", "viewer", "cred-b")
    r = post(client, f"/admin/api/users/{bob}/role", {"role": "admin"})
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}
    assert role_of(conn, bob) == "admin"
    assert (
        post(client, f"/admin/api/users/{bob}/role", {"role": "viewer"}).status_code
        == 200
    )
    assert role_of(conn, bob) == "viewer"


@pytest.mark.parametrize("role", ["root", "", None, 1, ["viewer"]])
def test_role_rejects_bad_role(client, conn, admin, role):
    bob = add_user(conn, "bob", "viewer", "cred-b")
    r = post(client, f"/admin/api/users/{bob}/role", {"role": role})
    assert r.status_code == 400
    assert role_of(conn, bob) == "viewer"
    assert post(client, f"/admin/api/users/{bob}/role").status_code == 400


def test_unknown_user_404(client, admin):
    assert (
        post(client, "/admin/api/users/999/role", {"role": "admin"}).status_code == 404
    )
    r = post(client, "/admin/api/users/999/delete")
    assert r.status_code == 404
    assert "error" in r.get_json()
    huge = "9" * 30
    assert post(client, f"/admin/api/users/{huge}/delete").status_code == 404
    assert post(client, "/admin/api/users/abc/delete").status_code == 404


def test_unknown_user_bad_role_is_400_or_404_never_500(client, admin):
    r = post(client, "/admin/api/users/999/role", {"role": "root"})
    assert r.status_code in (400, 404)


def test_delete_user_removes_credentials(client, conn, admin):
    bob = add_user(conn, "bob", "viewer", "cred-b")
    r = post(client, f"/admin/api/users/{bob}/delete")
    assert r.status_code == 200
    assert users.get_user(conn, bob) is None
    assert users.list_credentials(conn, bob) == []
    assert users.get_credential(conn, "cred-b") is None


def test_deleted_user_session_is_dead(server_app, client, conn, admin):
    bob = add_user(conn, "bob", "viewer", "cred-b")
    c2 = server_app.test_client()
    login_as(c2, bob)
    assert c2.get("/login").status_code == 200
    assert post(client, f"/admin/api/users/{bob}/delete").status_code == 200
    r = c2.get("/api/v1/status")
    assert r.status_code == 401


def test_last_admin_protected(client, conn, admin):
    # the only admin cannot delete or demote themselves
    r = post(client, f"/admin/api/users/{admin}/delete")
    assert r.status_code == 400
    assert "error" in r.get_json()
    r = post(client, f"/admin/api/users/{admin}/role", {"role": "viewer"})
    assert r.status_code == 400
    assert role_of(conn, admin) == "admin"
    assert users.get_user(conn, admin) is not None
    assert users.get_credential(conn, "cred-boss") is not None
    # an admin can still be re-assigned admin (no change)
    assert (
        post(client, f"/admin/api/users/{admin}/role", {"role": "admin"}).status_code
        == 200
    )


def test_last_admin_protected_when_other_user_is_viewer(client, conn, admin):
    bob = add_user(conn, "bob", "viewer", "cred-b")
    assert post(client, f"/admin/api/users/{admin}/delete").status_code == 400
    assert (
        post(client, f"/admin/api/users/{admin}/role", {"role": "viewer"}).status_code
        == 400
    )
    assert role_of(conn, bob) == "viewer"
    assert admin_count(conn) == 1


def test_admin_may_demote_self_if_another_admin_exists(client, conn, admin):
    other = add_user(conn, "other", "admin", "cred-o")
    r = post(client, f"/admin/api/users/{admin}/role", {"role": "viewer"})
    assert r.status_code == 200
    assert role_of(conn, admin) == "viewer"
    assert role_of(conn, other) == "admin"
    # now a viewer: admin access is gone
    assert client.get("/admin/api/users").status_code == 403


def test_admin_may_delete_self_if_another_admin_exists(client, conn, admin):
    other = add_user(conn, "other", "admin", "cred-o")
    r = post(client, f"/admin/api/users/{admin}/delete")
    assert r.status_code == 200
    assert users.get_user(conn, admin) is None
    assert users.get_credential(conn, "cred-boss") is None
    assert role_of(conn, other) == "admin"
    assert client.get("/admin/api/users").status_code == 401


def test_demoting_or_deleting_one_of_two_admins_then_the_last(client, conn, admin):
    other = add_user(conn, "other", "admin", "cred-o")
    assert (
        post(client, f"/admin/api/users/{other}/role", {"role": "viewer"}).status_code
        == 200
    )
    assert post(client, f"/admin/api/users/{admin}/delete").status_code == 400
    assert (
        post(client, f"/admin/api/users/{admin}/role", {"role": "viewer"}).status_code
        == 400
    )
    assert admin_count(conn) == 1


def test_admins_demoting_each_other_concurrently_keep_one(server_app, conn):
    for round_ in range(5):
        a = add_user(conn, f"a{round_}", "admin", f"ca{round_}")
        b = add_user(conn, f"b{round_}", "admin", f"cb{round_}")
        conn.execute("UPDATE users SET role = 'viewer' WHERE id NOT IN (?, ?)", (a, b))
        conn.commit()
        barrier = threading.Barrier(2)
        codes = {}

        def demote(me, target):
            c = server_app.test_client()
            login_as(c, me)
            barrier.wait()
            codes[me] = post(
                c, f"/admin/api/users/{target}/role", {"role": "viewer"}
            ).status_code

        threads = [
            threading.Thread(target=demote, args=(a, b)),
            threading.Thread(target=demote, args=(b, a)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert admin_count(conn) == 1, codes
        assert sorted(codes.values()) == [200, 400]
        conn.execute("DELETE FROM credentials WHERE user_id IN (?, ?)", (a, b))
        conn.execute("DELETE FROM users WHERE id IN (?, ?)", (a, b))
        conn.commit()


def test_admins_deleting_each_other_concurrently_keep_one(server_app, conn):
    a = add_user(conn, "a", "admin", "ca")
    b = add_user(conn, "b", "admin", "cb")
    barrier = threading.Barrier(2)
    codes = {}

    def delete(me, target):
        c = server_app.test_client()
        login_as(c, me)
        barrier.wait()
        codes[me] = post(c, f"/admin/api/users/{target}/delete").status_code

    threads = [
        threading.Thread(target=delete, args=(a, b)),
        threading.Thread(target=delete, args=(b, a)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert admin_count(conn) == 1
    assert sorted(codes.values()) == [200, 400]


# --- tokens ------------------------------------------------------------------


def test_admin_token_create_and_revoke(client, conn, admin):
    r = post(
        client,
        "/admin/api/tokens",
        {"experiment": "B", "name": "lab pc", "scope": "write"},
    )
    assert r.status_code == 200
    token = r.get_json()["token"]
    assert set(r.get_json()) == {"token"}
    info = check_token(conn, token)
    assert info is not None
    assert (info.experiment, info.scope) == ("B", "write")

    [row] = client.get("/admin/api/tokens").get_json()["tokens"]
    assert row["id"] == info.id
    assert row["experiment"] == "B"
    assert row["name"] == "lab pc"
    assert row["scope"] == "write"
    assert not row["revoked"]
    assert row["last_used"] is not None  # the check above

    r = post(client, f"/admin/api/tokens/{row['id']}/revoke")
    assert r.status_code == 200
    assert check_token(conn, token) is None
    [row] = client.get("/admin/api/tokens").get_json()["tokens"]
    assert row["revoked"]


def test_token_scope_defaults_to_nothing_and_read_works(client, conn, admin):
    r = post(
        client,
        "/admin/api/tokens",
        {"experiment": "B", "name": "viewer pc", "scope": "read"},
    )
    assert r.status_code == 200
    assert check_token(conn, r.get_json()["token"]).scope == "read"


def test_token_secret_never_in_listing(client, conn, admin):
    token = post(
        client, "/admin/api/tokens", {"experiment": "B", "name": "pc", "scope": "write"}
    ).get_json()["token"]
    secret = token.split(".", 1)[1]
    row = conn.execute("SELECT salt, hash FROM tokens").fetchone()
    for url in (
        "/admin/api/tokens",
        "/admin/api/users",
        "/admin/api/warnings",
        "/admin",
    ):
        text = client.get(url).get_data(as_text=True)
        assert secret not in text, url
        assert token not in text, url
        assert row["hash"] not in text, url
        assert row["salt"] not in text, url
    for item in client.get("/admin/api/tokens").get_json()["tokens"]:
        assert set(item) == {
            "id",
            "experiment",
            "name",
            "scope",
            "created",
            "last_used",
            "revoked",
        }


def test_token_secret_not_logged(client, admin, caplog):
    with caplog.at_level("DEBUG"):
        token = post(
            client,
            "/admin/api/tokens",
            {"experiment": "B", "name": "pc", "scope": "write"},
        ).get_json()["token"]
    assert token.split(".", 1)[1] not in caplog.text


@pytest.mark.parametrize(
    "body",
    [
        {"experiment": "B", "name": "pc", "scope": "admin"},
        {"experiment": "B", "name": "pc", "scope": ""},
        {"experiment": "B", "name": "pc", "scope": None},
        {"experiment": "B", "name": "pc", "scope": ["write"]},
        {"experiment": "B", "name": "pc"},
        {"experiment": "bad name!", "name": "pc", "scope": "write"},
        {"experiment": "", "name": "pc", "scope": "write"},
        {"experiment": "x" * 65, "name": "pc", "scope": "write"},
        {"experiment": 5, "name": "pc", "scope": "write"},
        {"experiment": None, "name": "pc", "scope": "write"},
        {"experiment": ["B"], "name": "pc", "scope": "write"},
        {"name": "pc", "scope": "write"},
        {"experiment": "B", "name": "", "scope": "write"},
        {"experiment": "B", "name": "   ", "scope": "write"},
        {"experiment": "B", "name": 5, "scope": "write"},
        {"experiment": "B", "name": {"a": 1}, "scope": "write"},
        {"experiment": "B", "name": "x" * 65, "scope": "write"},
        {"experiment": "B", "name": "a\nb", "scope": "write"},
        {"experiment": "B", "scope": "write"},
    ],
)
def test_token_create_rejects_bad_input(client, conn, admin, body):
    r = post(client, "/admin/api/tokens", body)
    assert r.status_code == 400
    assert "error" in r.get_json()
    assert conn.execute("SELECT COUNT(*) FROM tokens").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0] == 0


def test_revoke_unknown_token_404(client, admin):
    r = post(client, "/admin/api/tokens/999/revoke")
    assert r.status_code == 404
    assert "error" in r.get_json()
    assert post(client, f"/admin/api/tokens/{'9' * 30}/revoke").status_code == 404
    assert post(client, "/admin/api/tokens/abc/revoke").status_code == 404


# --- warnings ----------------------------------------------------------------


def test_warnings_listed(client, conn, admin, monkeypatch):
    # the clock-skew push of the push tests
    token = create_token(conn, "B", "lab pc")
    # hc_web.api.time is the global time module: restore it before the admin
    # request, or the session cookie would look like it comes from the future
    with monkeypatch.context() as m:
        m.setattr("hc_web.api.time.time", lambda: 1000.0)
        r = client.post(
            "/api/v1/push",
            json={
                "run": "A",
                "sent_at": 940.0,
                "interval": 10.0,
                "ticks": [940.0],
                "points": [],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200
    [w] = client.get("/admin/api/warnings").get_json()["warnings"]
    assert w["experiment"] == "B"
    assert w["t"] == 1000.0
    assert "clock skew" in w["message"]
    assert set(w) == {"id", "experiment", "t", "message"}


def test_warnings_newest_first_and_limited(client, conn, admin):
    eid = conn.execute(
        "INSERT INTO experiments (name, created) VALUES ('B', 0)"
    ).lastrowid
    conn.executemany(
        "INSERT INTO warnings (experiment_id, t, message) VALUES (?, ?, ?)",
        [(eid, float(i), f"w{i}") for i in range(250)],
    )
    conn.execute(
        "INSERT INTO warnings (experiment_id, t, message) VALUES (NULL, 500, 'orphan')"
    )
    conn.commit()
    warnings = client.get("/admin/api/warnings").get_json()["warnings"]
    assert len(warnings) == 200
    assert warnings[0]["message"] == "orphan"
    assert warnings[0]["experiment"] is None
    assert [w["t"] for w in warnings] == sorted(
        (w["t"] for w in warnings), reverse=True
    )
    assert warnings[1]["message"] == "w249"
