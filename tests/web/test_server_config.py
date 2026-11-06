"""Validation of the hc_web configuration file."""

import pytest

pytest.importorskip("flask")

from hc_web.cli import main  # noqa: E402
from hc_web.config import Config, ConfigError, load_config  # noqa: E402


def write(tmp_path, text):
    path = tmp_path / "config.toml"
    path.write_text(text)
    return path


def config_text(origin='"https://mon.example.org"', extra=""):
    return f'origin = {origin}\ndatabase = "x.sqlite"\n{extra}'


def test_a_plain_config_is_accepted(tmp_path):
    cfg = load_config(write(tmp_path, config_text()))
    assert cfg.origin == "https://mon.example.org"
    assert cfg.rp_id == "mon.example.org"
    assert cfg.proxy_hops == 1 and cfg.secure_cookies is True


@pytest.mark.parametrize(
    "origin, expected, rp_id",
    [
        ("https://mon.example.org/", "https://mon.example.org", "mon.example.org"),
        ("https://mon.example.org///", "https://mon.example.org", "mon.example.org"),
        ("http://localhost:8080", "http://localhost:8080", "localhost"),
        ("HTTPS://Mon.Example.ORG", "https://mon.example.org", "mon.example.org"),
        ("http://127.0.0.1:5000/", "http://127.0.0.1:5000", "127.0.0.1"),
    ],
)
def test_origin_is_normalised(tmp_path, origin, expected, rp_id):
    cfg = load_config(write(tmp_path, config_text(f'"{origin}"')))
    assert cfg.origin == expected
    assert cfg.rp_id == rp_id


@pytest.mark.parametrize(
    "origin",
    [
        "mon.example.org",  # no scheme
        "//mon.example.org",
        "ftp://mon.example.org",
        "https://",
        "https:///path",
        "https://mon.example.org/hc",
        "https://mon.example.org/?a=1",
        "https://mon.example.org?a=1",
        "https://mon.example.org/#top",
        "https://mon.example.org#top",
        "https://alice:secret@mon.example.org",
        "https://mon.example.org:notaport",
        "https://mon.example.org:99999",
        "",
        "https://mon example.org",
    ],
)
def test_bad_origins_are_refused(tmp_path, origin):
    with pytest.raises(ConfigError, match="origin"):
        load_config(write(tmp_path, config_text(f'"{origin}"')))


def test_a_refused_origin_does_not_print_a_password(tmp_path):
    with pytest.raises(ConfigError) as info:
        load_config(write(tmp_path, config_text('"https://alice:hunter2@mon.org"')))
    assert "hunter2" not in str(info.value)


@pytest.mark.parametrize("hops", ["0", "1", "3"])
def test_proxy_hops_accepts_non_negative_integers(tmp_path, hops):
    cfg = load_config(write(tmp_path, config_text(extra=f"proxy_hops = {hops}\n")))
    assert cfg.proxy_hops == int(hops)


@pytest.mark.parametrize("hops", ["-1", "true", "false", '"1"', "1.5", "[1]"])
def test_bad_proxy_hops_are_refused(tmp_path, hops):
    with pytest.raises(ConfigError, match="proxy_hops"):
        load_config(write(tmp_path, config_text(extra=f"proxy_hops = {hops}\n")))


@pytest.mark.parametrize(
    "line, name",
    [
        ("secure_cookies = 1", "secure_cookies"),
        ('secure_cookies = "false"', "secure_cookies"),
        ("retention_days = 0", "retention_days"),
        ("retention_days = -2", "retention_days"),
        ('retention_days = "7"', "retention_days"),
        ("retention_days = true", "retention_days"),
        ("retention_days = nan", "retention_days"),
        ("retention_days = inf", "retention_days"),
        ("site_name = 5", "site_name"),
        ('site_name = ""', "site_name"),
    ],
)
def test_wrong_types_and_values_are_refused(tmp_path, line, name):
    with pytest.raises(ConfigError, match=name):
        load_config(write(tmp_path, config_text(extra=line + "\n")))


def test_retention_days_may_be_fractional(tmp_path):
    cfg = load_config(write(tmp_path, config_text(extra="retention_days = 0.5\n")))
    assert cfg.retention_days == 0.5


def test_unknown_keys_are_refused_by_name(tmp_path):
    with pytest.raises(ConfigError, match="proxyhops") as info:
        load_config(write(tmp_path, config_text(extra="proxyhops = 2\n")))
    assert "unknown" in str(info.value)


@pytest.mark.parametrize("text", ["", 'origin = "http://localhost"\n'])
def test_origin_and_database_are_required(tmp_path, text):
    with pytest.raises(ConfigError, match="required"):
        load_config(write(tmp_path, text))


def test_database_must_be_a_string(tmp_path):
    with pytest.raises(ConfigError, match="database"):
        load_config(write(tmp_path, 'origin = "http://localhost"\ndatabase = 5\n'))


def test_invalid_toml_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="config.toml"):
        load_config(write(tmp_path, "origin = \n"))


def test_the_message_names_the_file(tmp_path):
    path = write(tmp_path, config_text(extra="proxy_hops = -1\n"))
    with pytest.raises(ConfigError, match=str(path)):
        load_config(path)


def test_rp_id_is_never_empty(tmp_path):
    # also a Config made in code is checked
    with pytest.raises(ConfigError, match="origin"):
        Config(origin="https://", database=tmp_path / "x")
    assert Config(origin="http://localhost", database=tmp_path / "x").rp_id == (
        "localhost"
    )


def test_the_cli_reports_a_bad_config_without_a_traceback(tmp_path, capsys):
    path = write(tmp_path, config_text('"https://mon.example.org/hc"'))
    assert main(["status", f"--config={path}"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("Error:") and "origin" in err
    assert "Traceback" not in err


def test_the_cli_reports_a_database_of_a_newer_version(tmp_path, capsys):
    import sqlite3

    path = write(tmp_path, config_text())
    raw = sqlite3.connect(tmp_path / "x.sqlite")
    raw.execute("PRAGMA user_version = 99")
    raw.commit()
    raw.close()
    assert main(["status", f"--config={path}"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("Error:") and "newer" in err
    assert "Traceback" not in err
