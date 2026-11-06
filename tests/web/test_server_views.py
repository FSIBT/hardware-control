"""Viewer pages (overview, experiment plots), the Plotly bundle and the CSV export."""

import csv
import io
import re

import pytest

pytest.importorskip("flask")
pytest.importorskip("webauthn")

from hc_web import db, query  # noqa: E402
from hc_web.tokens import create_token, get_or_create_experiment  # noqa: E402

# the helpers of the other web tests, not duplicated here
from .test_server_auth import add_user, login_as  # noqa: E402
from .test_server_query import add_channel, add_coverage, auth  # noqa: E402


@pytest.fixture
def conn(config):
    c = db.connect(config.database)
    yield c
    c.close()


@pytest.fixture
def exp(conn):
    experiment_id = get_or_create_experiment(conn, "B")
    with conn:
        conn.execute(
            "UPDATE experiments SET interval = 10, current_run = 'A' WHERE id = ?",
            (experiment_id,),
        )
    return experiment_id


@pytest.fixture
def viewer(client, conn):
    login_as(client, add_user(conn, "vera", "viewer", "cred-v"))


# --- login and routing ---------------------------------------------------------


@pytest.mark.parametrize("url", ["/", "/experiment/B"])
def test_pages_require_login(client, exp, url):
    r = client.get(url)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/login")


def test_overview_renders_for_viewer(client, viewer):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    html = r.get_data(as_text=True)
    for ident in "alarm-banner cards notify-button empty error".split():
        assert f'id="{ident}"' in html, ident
    assert "/static/overview.js" in html
    assert 'id="logout-button"' in html


def test_overview_for_admin_too(client, conn):
    login_as(client, add_user(conn, "boss", "admin", "cred-boss"))
    assert client.get("/").status_code == 200


def test_experiment_page_renders(client, viewer, exp):
    r = client.get("/experiment/B")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'data-experiment="B"' in html
    for ident in "plots range-buttons csv-link notify-button".split():
        assert f'id="{ident}"' in html, ident
    for src in ("plotly.min.js", "plots.js"):
        assert f"/static/{src}" in html
    # the Plotly bundle is loaded before the script that uses it
    assert html.index("plotly.min.js") < html.index("plots.js")


def test_unknown_experiment_404(client, viewer):
    assert client.get("/experiment/nope").status_code == 404


def test_experiment_name_never_reaches_the_page_unescaped(client, viewer, exp):
    # not a valid experiment name, so it is just a 404 and nothing is echoed
    r = client.get("/experiment/<script>alert(1)<script>")
    assert r.status_code == 404
    assert "alert(1)" not in r.get_data(as_text=True)


def test_nav_links_to_the_overview(client, viewer):
    html = client.get("/").get_data(as_text=True)
    assert re.search(r'<nav.*href="/".*</nav>', html, re.S)


def test_pages_are_get_only(client, viewer):
    assert client.post("/", json={}).status_code in (405, 415)


# --- static files --------------------------------------------------------------


def test_plotly_served(client):
    r = client.get("/static/plotly.min.js")
    assert r.status_code == 200
    assert "javascript" in r.mimetype
    assert len(r.data) > 1_000_000
    r.close()


def test_page_scripts_served(client):
    for name in ("overview.js", "plots.js"):
        with client.get(f"/static/{name}") as r:
            assert r.status_code == 200, name


def test_page_scripts_do_not_use_innerhtml_or_eval(client):
    for name in ("common.js", "overview.js", "plots.js", "notify.js"):
        with client.get(f"/static/{name}") as r:
            assert r.status_code == 200, name
            text = r.get_data(as_text=True)
        assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML", text), name
        assert not re.search(r"\beval\s*\(|new Function|document\.write", text), name


def test_plots_use_svg_scatter_not_webgl(client):
    # scattergl needs 'unsafe-eval' (regl compiles code with Function()), which
    # the CSP does not allow
    with client.get("/static/plots.js") as r:
        text = r.get_data(as_text=True)
    assert "scattergl" not in text
    assert '"scatter"' in text


def test_no_inline_code_or_styles(client, viewer, exp):
    for url in ("/", "/experiment/B"):
        html = client.get(url).get_data(as_text=True)
        assert not re.search(r"<script(?![^>]*\ssrc=)", html), url
        assert not re.search(r"\son\w+\s*=", html), url
        assert "style=" not in html, url
        assert "<style" not in html, url
        assert "<link" in html and "https://" not in html, url


# --- Content-Security-Policy ---------------------------------------------------

STRICT = "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'"


def test_overview_has_the_strict_policy(client, viewer):
    assert client.get("/").headers["Content-Security-Policy"] == STRICT


def test_experiment_page_allows_inline_style_for_plotly_only(client, viewer, exp):
    csp = client.get("/experiment/B").headers["Content-Security-Policy"]
    assert "style-src 'self' 'unsafe-inline'" in csp
    assert "img-src 'self' data:" in csp
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-eval" not in csp
    # script-src is not widened: it falls back to default-src 'self'
    assert "script-src" not in csp


def test_other_pages_do_not_allow_inline_style(client, conn, viewer):
    login_as(client, add_user(conn, "boss", "admin", "cred-boss"))
    for url in ("/", "/admin", "/login"):
        csp = client.get(url).headers["Content-Security-Policy"]
        assert "unsafe-inline" not in csp, url
        assert "unsafe-eval" not in csp, url
        assert "img-src 'self' data:" in csp, url


# --- CSV export ----------------------------------------------------------------


@pytest.fixture
def data(conn, exp):
    add_coverage(conn, exp, 0, 100)
    add_channel(
        conn,
        exp,
        "hv",
        "sampled",
        [(10.0, 1.5), (20.0, None), (30.0, -2.0)],
        unit="V",
    )
    add_channel(
        conn,
        exp,
        "mode",
        "state",
        [(10.0, "Standby"), (20.0, 'a,"b"'), (30.0, None)],
    )


def rows(response):
    return list(csv.reader(io.StringIO(response.get_data(as_text=True))))


def test_csv_for_a_session_user(client, viewer, data):
    r = client.get("/api/v1/data.csv?channels=B/hv,B/mode&since=0")
    assert r.status_code == 200
    assert r.mimetype == "text/csv"
    assert r.headers["Content-Type"] == "text/csv; charset=utf-8"
    disposition = r.headers["Content-Disposition"]
    assert disposition.startswith("attachment") and ".csv" in disposition
    assert r.headers["Cache-Control"] == "no-store"
    assert rows(r) == [
        ["time", "time_iso", "channel", "value"],
        ["10.0", "1970-01-01T00:00:10.000Z", "B/hv", "1.5"],
        ["20.0", "1970-01-01T00:00:20.000Z", "B/hv", ""],
        ["30.0", "1970-01-01T00:00:30.000Z", "B/hv", "-2.0"],
        ["10.0", "1970-01-01T00:00:10.000Z", "B/mode", "Standby"],
        ["20.0", "1970-01-01T00:00:20.000Z", "B/mode", 'a,"b"'],
        ["30.0", "1970-01-01T00:00:30.000Z", "B/mode", ""],
    ]


def test_csv_quotes_with_the_csv_module(client, viewer, data):
    text = client.get("/api/v1/data.csv?channels=B/mode&since=0").get_data(as_text=True)
    assert '"a,""b"""' in text
    assert "\r\n" in text  # csv module default line terminator


def test_csv_range(client, viewer, data):
    r = client.get("/api/v1/data.csv?channels=B/hv&since=15&until=25")
    assert [row[0] for row in rows(r)[1:]] == ["20.0"]


@pytest.mark.parametrize("scope", ["read", "write"])
def test_csv_with_a_token_of_any_scope(client, conn, data, scope):
    token = create_token(conn, "B", "t", scope)
    r = client.get("/api/v1/data.csv?channels=B/hv&since=0", headers=auth(token))
    assert r.status_code == 200
    assert len(rows(r)) == 4


def test_csv_needs_a_login_or_token(client, data):
    r = client.get("/api/v1/data.csv?channels=B/hv&since=0")
    assert r.status_code == 401
    assert "error" in r.get_json()
    bad = client.get(
        "/api/v1/data.csv?channels=B/hv&since=0", headers=auth("not-a-token")
    )
    assert bad.status_code == 401


def test_csv_unknown_channel_404(client, viewer, data):
    r = client.get("/api/v1/data.csv?channels=B/hv,B/nope&since=0")
    assert r.status_code == 404
    assert r.get_json() == {"error": "unknown channel B/nope"}


@pytest.mark.parametrize(
    "query_string",
    [
        "since=0",  # no channels
        "channels=B/hv",  # no since
        "channels=B/hv&since=abc",
        "channels=B/hv&since=nan",
        "channels=B/hv&since=10&until=5",
    ],
)
def test_csv_bad_parameters_400(client, viewer, data, query_string):
    r = client.get(f"/api/v1/data.csv?{query_string}")
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_csv_refuses_more_than_the_row_cap(client, viewer, data, monkeypatch):
    monkeypatch.setattr(query, "MAX_CSV_POINTS", 5)
    ok = client.get("/api/v1/data.csv?channels=B/hv&since=0")
    assert ok.status_code == 200  # 3 points
    r = client.get("/api/v1/data.csv?channels=B/hv,B/mode&since=0")  # 6 points
    assert r.status_code == 413
    assert "narrow" in r.get_json()["error"]


def test_csv_does_not_turn_state_values_into_formulas(client, viewer, conn, exp):
    add_channel(conn, exp, "s", "state", [(1.0, "=1+1"), (2.0, "-5"), (3.0, "@x")])
    r = client.get("/api/v1/data.csv?channels=B/s&since=0")
    assert [row[3] for row in rows(r)[1:]] == ["'=1+1", "-5", "'@x"]


def test_json_data_endpoint_is_unchanged(client, viewer, data):
    r = client.get("/api/v1/data?channels=B/hv&since=0")
    assert r.status_code == 200
    assert r.get_json()["channels"]["B/hv"]["points"][1] == [20.0, None]
