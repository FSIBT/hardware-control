"""The pages are styled with the vendored Pico CSS and stay self-contained."""

import re
from pathlib import Path

import pytest

pytest.importorskip("flask")
pytest.importorskip("webauthn")

from hc_web import db  # noqa: E402

# the helpers of the auth tests, not duplicated here
from .test_server_auth import add_user, invite, login_as  # noqa: E402


@pytest.fixture
def conn(config):
    c = db.connect(config.database)
    yield c
    c.close()


def pages(client, conn):
    """Every HTML page, as (name, html text); the admin page needs an admin."""
    code = invite(conn)
    result = {
        "login": client.get("/login"),
        "invite": client.get(f"/invite/{code}"),
        "invite-invalid": client.get("/invite/not-a-real-code"),
    }
    login_as(client, add_user(conn, "boss", "admin", "cred-boss"))
    result["admin"] = client.get("/admin")
    for name, r in result.items():
        assert r.status_code == 200, name
    return {name: r.get_data(as_text=True) for name, r in result.items()}


def test_pico_is_served(client):
    r = client.get("/static/pico.min.css")
    assert r.status_code == 200
    assert r.mimetype == "text/css"
    assert 10_000 < len(r.data) < 150_000
    assert b"Pico CSS" in r.data[:200]
    assert b"v2." in r.data[:200]


def test_licence_ships_in_the_package():
    import hc_web

    static = Path(hc_web.__file__).parent / "static"
    licence = (static / "PICO-LICENSE.txt").read_text()
    assert "MIT License" in licence
    assert "2.1.1" in licence
    assert (static / "pico.min.css").is_file()


def test_pages_link_pico_before_hcweb_css(client, conn):
    for name, html in pages(client, conn).items():
        pico = html.find('href="/static/pico.min.css"')
        ours = html.find('href="/static/hcweb.css"')
        assert 0 <= pico < ours, name
        assert '<main class="container">' in html, name
        assert "data-theme" not in html, name


def test_pages_are_self_contained(client, conn):
    for name, html in pages(client, conn).items():
        assert not re.search(r"https?://", html), name
        assert "<style" not in html.lower(), name
        assert not re.search(r"\sstyle\s*=", html, re.I), name
        assert not re.search(r"\son[a-z]+\s*=", html, re.I), name
        for script in re.findall(r"<script\b[^>]*>", html, re.I):
            assert "src=" in script, name
        assert 'type="password"' not in html, name


def test_pages_keep_the_strict_csp(client, conn):
    for name, r in {
        "login": client.get("/login"),
        "invite": client.get(f"/invite/{invite(conn)}"),
    }.items():
        assert (
            r.headers["Content-Security-Policy"]
            == "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        ), name


def test_nav_follows_the_current_user(client, conn):
    anonymous = client.get("/login").get_data(as_text=True)
    assert "<nav" in anonymous
    assert 'id="logout-button"' not in anonymous
    assert 'href="/admin"' not in anonymous

    login_as(client, add_user(conn, "vera", "viewer", "cred-v"))
    # no viewer page exists yet, so look at an invite page while logged in
    viewer = client.get("/invite/x").get_data(as_text=True)
    assert 'id="logout-button"' in viewer
    assert 'href="/admin"' not in viewer

    login_as(client, add_user(conn, "boss", "admin", "cred-boss"))
    admin = client.get("/admin").get_data(as_text=True)
    assert 'id="logout-button"' in admin
    assert 'href="/admin"' in admin


def test_nav_script_is_served(client):
    assert client.get("/static/nav.js").status_code == 200


def test_admin_keeps_the_ids_the_script_uses(client, conn):
    html = pages(client, conn)["admin"]
    for ident in (
        "invite-form invite-role invite-result invite-url invite-copy "
        "users-body token-form token-experiment token-name token-scope "
        "token-result token-value token-copy tokens-body warnings-body error"
    ).split():
        assert f'id="{ident}"' in html, ident
