"""Skeleton tests for the hc_web server: config, schema, import isolation."""

import subprocess
import sys

import pytest

pytest.importorskip("flask")

from hc_web import db  # noqa: E402
from hc_web.app import create_app  # noqa: E402
from hc_web.config import load_config  # noqa: E402

TABLES = {
    "meta",
    "experiments",
    "channels",
    "points",
    "coverage",
    "events",
    "latched",
    "warnings",
    "tokens",
    "users",
    "credentials",
    "invites",
}


def test_import_does_not_load_hardware_control():
    code = (
        "import hc_web.app, sys; "
        "assert 'hardware_control' not in sys.modules "
        "and 'PyQt6' not in sys.modules"
    )
    result = subprocess.run([sys.executable, "-c", code])
    assert result.returncode == 0


def test_load_config(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('origin = "https://mon.example.org"\ndatabase = "x.sqlite"\n')
    cfg = load_config(path)
    assert cfg.rp_id == "mon.example.org"
    assert cfg.retention_days == 7
    assert cfg.database == tmp_path / "x.sqlite"


def test_load_config_from_env(tmp_path, monkeypatch):
    path = tmp_path / "env.toml"
    path.write_text(
        'origin = "http://localhost:8080"\n'
        'database = "/var/lib/hc/db.sqlite"\n'
        "retention_days = 2\n"
        'site_name = "Lab"\n'
    )
    monkeypatch.setenv("HC_WEB_CONFIG", str(path))
    cfg = load_config()
    assert cfg.rp_id == "localhost"
    assert str(cfg.database) == "/var/lib/hc/db.sqlite"
    assert cfg.retention_days == 2
    assert cfg.site_name == "Lab"


def test_schema_created(config):
    conn = db.connect(config.database)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert TABLES <= {r["name"] for r in rows}
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.close()


def test_meta_roundtrip(config):
    conn = db.connect(config.database)
    assert db.get_meta(conn, "k") is None
    db.set_meta(conn, "k", "v1")
    db.set_meta(conn, "k", "v2")
    assert db.get_meta(conn, "k") == "v2"
    conn.close()


def test_secret_key_persisted(config):
    first = create_app(config).config["SECRET_KEY"]
    second = create_app(config).config["SECRET_KEY"]
    assert first == second
    assert len(first) == 64


def test_get_db_one_per_request(server_app):
    from hc_web.app import get_db

    seen = []

    @server_app.get("/_probe")
    def probe():
        seen.append(get_db())
        seen.append(get_db())
        return "ok"

    response = server_app.test_client().get("/_probe")
    assert response.status_code == 200
    assert seen[0] is seen[1]
