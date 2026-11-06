import pytest

pytest.importorskip("flask")

from hc_web import db  # noqa: E402
from hc_web.cli import main  # noqa: E402
from hc_web.tokens import (  # noqa: E402
    check_token,
    create_token,
    get_or_create_experiment,
    list_tokens,
    revoke_token,
)


@pytest.fixture
def conn(config):
    c = db.connect(config.database)
    yield c
    c.close()


def test_token_roundtrip(conn):
    info = check_token(conn, create_token(conn, "B", "lab pc"))
    assert info is not None
    assert info.experiment == "B"
    assert info.scope == "write"
    assert info.experiment_id == get_or_create_experiment(conn, "B")


def test_read_scope(conn):
    info = check_token(conn, create_token(conn, "B", "viewer", scope="read"))
    assert info.scope == "read"
    with pytest.raises(ValueError):
        create_token(conn, "B", "x", scope="admin")


def test_wrong_and_revoked_tokens(conn):
    token = create_token(conn, "B", "lab pc")
    token_id, secret = token.split(".", 1)
    assert check_token(conn, f"{token_id}.{secret[:-1]}x") is None
    assert check_token(conn, None) is None
    assert check_token(conn, "") is None
    assert check_token(conn, "garbage") is None
    assert check_token(conn, "999.abc") is None
    assert check_token(conn, token) is not None
    assert revoke_token(conn, int(token_id)) is True
    assert check_token(conn, token) is None
    assert revoke_token(conn, 999) is False


def test_last_used_updated(conn):
    token = create_token(conn, "B", "lab pc")
    assert list_tokens(conn)[0]["last_used"] is None
    check_token(conn, token)
    assert list_tokens(conn)[0]["last_used"] is not None


def test_plaintext_not_stored(conn):
    secret = create_token(conn, "B", "lab pc").split(".", 1)[1]
    for row in conn.execute("SELECT * FROM tokens"):
        assert all(secret not in str(value) for value in tuple(row))


def test_bad_experiment_name(conn):
    for name in ("B C", "a/b", "", "x" * 65):
        with pytest.raises(ValueError):
            get_or_create_experiment(conn, name)
        with pytest.raises(ValueError):
            create_token(conn, name, "pc")


def test_get_or_create_is_idempotent(conn):
    assert get_or_create_experiment(conn, "B") == get_or_create_experiment(conn, "B")
    assert get_or_create_experiment(conn, "B.1-x_") != get_or_create_experiment(
        conn, "C"
    )


def test_list_tokens(conn):
    create_token(conn, "B", "lab pc")
    (row,) = list_tokens(conn)
    assert set(row) == {
        "id",
        "experiment",
        "name",
        "scope",
        "created",
        "last_used",
        "revoked",
    }
    assert row["experiment"] == "B"
    assert row["revoked"] == 0


@pytest.fixture
def cfg(config, tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(f'origin = "http://localhost"\ndatabase = "{config.database}"\n')
    return str(path)


def test_cli_token_create_prints_once(config, cfg, capsys):
    assert main(["token", "create", "B", "pc", "--config", cfg]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    conn = db.connect(config.database)
    try:
        assert check_token(conn, lines[0]).experiment == "B"
    finally:
        conn.close()


def test_cli_read_only_list_revoke_status(config, cfg, capsys):
    assert main(["token", "create", "B", "pc", "--read-only", "--config", cfg]) == 0
    token = capsys.readouterr().out.strip()
    assert main(["token", "list", "--config", cfg]) == 0
    out = capsys.readouterr().out
    assert "read" in out and "pc" in out and token not in out
    assert main(["status", "--config", cfg]) == 0
    assert "tokens" in capsys.readouterr().out.lower()
    assert main(["token", "revoke", "1", "--config", cfg]) == 0
    assert main(["token", "revoke", "99", "--config", cfg]) == 1


def test_cli_bad_experiment_name(cfg, capsys):
    assert main(["token", "create", "a/b", "pc", "--config", cfg]) == 1
    assert "a/b" in capsys.readouterr().err


def test_cli_config_from_environment(config, cfg, capsys, monkeypatch):
    monkeypatch.setenv("HC_WEB_CONFIG", cfg)
    assert main(["status"]) == 0
    assert str(config.database) in capsys.readouterr().out
