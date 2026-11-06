"""Viewer pages (overview, experiment plots), the Plotly bundle and the CSV export."""

import csv
import io
import json
import re
import shutil
import subprocess
from pathlib import Path

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


def test_anonymous_unknown_experiment_redirects_to_login(client):
    r = client.get("/experiment/nope")
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/login")


def test_csv_link_never_downloads_the_page(client, viewer, exp):
    html = client.get("/experiment/B").get_data(as_text=True)
    link = re.search(r"<a id=\"csv-link\"[^>]*>", html).group(0)
    assert "download" not in link  # the attachment header forces the download
    assert "href" not in link  # set by the script after the first load
    assert 'aria-disabled="true"' in link


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


@pytest.fixture
def no_plotly():
    from hc_web import views

    views._plotly_bundle.cache_clear()  # it is cached
    with pytest.MonkeyPatch.context() as m:
        yield m
    views._plotly_bundle.cache_clear()


def test_plotly_404_when_the_package_is_missing(client, no_plotly):
    def files(name):
        raise ModuleNotFoundError(name)

    no_plotly.setattr("hc_web.views.importlib.resources.files", files)
    assert client.get("/static/plotly.min.js").status_code == 404


def test_plotly_404_when_the_file_is_missing(client, no_plotly, tmp_path):
    no_plotly.setattr("hc_web.views.importlib.resources.files", lambda name: tmp_path)
    assert client.get("/static/plotly.min.js").status_code == 404


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
    values = ["=1+1", "-5", "@x", "\tx", "\rx", "\t5", "+cmd", "ok"]
    add_channel(conn, exp, "s", "state", [(float(i), v) for i, v in enumerate(values)])
    r = client.get("/api/v1/data.csv?channels=B/s&since=0")
    assert [row[3] for row in rows(r)[1:]] == [
        "'=1+1",
        "-5",
        "'@x",
        "'\tx",
        "'\rx",
        "'\t5",
        "'+cmd",
        "ok",
    ]


def test_json_data_endpoint_is_unchanged(client, viewer, data):
    r = client.get("/api/v1/data?channels=B/hv&since=0")
    assert r.status_code == 200
    assert r.get_json()["channels"]["B/hv"]["points"][1] == [20.0, None]


# --- the series code of plots.js, run with node (skipped without it) ------------

NODE = shutil.which("node")
STATIC = Path(__file__).parents[2] / "src" / "hc_web" / "static"


def run_series(tmp_path, body: str):
    """Evaluate ``body`` with ``S`` = window.hcSeries of plots.js; return its JSON."""
    if NODE is None:
        pytest.skip("node is not installed")
    script = tmp_path / "check.js"
    script.write_text(
        'const vm = require("vm"), fs = require("fs");\n'
        "const ctx = { window: {}, document: undefined, Date, Math, String, Number };\n"
        "vm.createContext(ctx);\n"
        f"vm.runInContext(fs.readFileSync({str(STATIC / 'plots.js')!r}, 'utf8'), ctx);\n"
        "const S = ctx.window.hcSeries;\n"
        f"console.log(JSON.stringify((function () {{ {body} }})()));\n"
    )
    done = subprocess.run(
        [NODE, str(script)], capture_output=True, text=True, timeout=60, check=True
    )
    return json.loads(done.stdout)


def test_state_values_reach_plotly_escaped(tmp_path):
    out = run_series(
        tmp_path,
        """return {
          plain: S.plain('<b>x</b> & <a href="u">y</a>'),
          steps: S.stateSeries([0, '<5V'], [[10, '<b>x</b>'], [20, null]], [], 5, 30),
        };""",
    )
    assert out["plain"] == '&lt;b&gt;x&lt;/b&gt; &amp; &lt;a href="u"&gt;y&lt;/a&gt;'
    values = [v for _, v in out["steps"] if v is not None]
    assert values == ["&lt;5V", "&lt;b&gt;x&lt;/b&gt;", "&lt;b&gt;x&lt;/b&gt;"]
    assert not any("<" in v for v in values)


def test_categories_and_trace_use_the_same_escaped_strings():
    # string-level: the category list is built with plain(), like stateSeries
    text = (STATIC / "plots.js").read_text()
    assert "const text = plain(v)" in text
    assert "plain(before[1])" in text
    assert "plain(p[1])" in text
    assert "categoryarray = ch.categories" in text


def test_decimate_keeps_extremes_order_and_nulls(tmp_path):
    out = run_series(
        tmp_path,
        """const pts = [];
        for (let i = 0; i < 1000; i++) pts.push([i, i === 500 ? 99 : (i === 501 ? -99 : 0)]);
        pts.splice(300, 0, [299.5, null]);
        const d = S.decimate(pts, 100);
        return {d: d, n: pts.length};""",
    )
    d = out["d"]
    assert len(d) < out["n"] / 4
    assert [p[0] for p in d] == sorted(p[0] for p in d)  # still in time order
    assert sum(1 for p in d if p[1] is None) == 1  # the unknown value survives
    values = [p[1] for p in d if p[1] is not None]
    assert max(values) == 99 and min(values) == -99
    short = run_series(tmp_path, "return S.decimate([[1, 1], [2, 2]], 100);")
    assert short == [[1, 1], [2, 2]]


def test_sampled_series_breaks_at_gaps_and_unknowns(tmp_path):
    out = run_series(
        tmp_path,
        "return S.sampledSeries([[1,1],[2,2],[5,5],[6,null],[7,7],[10,10]], [[3,5],[8,null]]);",
    )
    assert out == [
        [1, 1],
        [2, 2],
        [3, None],
        [5, 5],
        [6, None],
        [7, 7],
        [8, None],
        [10, 10],
    ]


def test_state_series_holds_value_up_to_a_gap(tmp_path):
    out = run_series(
        tmp_path,
        "return S.stateSeries(null, [[10, 'a']], [[20, 30]], 0, 50);",
    )
    assert out == [[10, "a"], [20, "a"], [20, None]]


def test_merge_gaps_joins_what_touches(tmp_path):
    out = run_series(
        tmp_path,
        "return [S.mergeGaps([[0,50],[60,null]],[[70,null]],70), S.mergeGaps([[0,50],[80,null]],[[70,null]],70)];",
    )
    assert out == [[[0, 50], [60, None]], [[0, 50], [70, None]]]


def run_overview(tmp_path, body: str):
    """Evaluate ``body`` with ``O`` = window.hcOverview of overview.js (no DOM)."""
    if NODE is None:
        pytest.skip("node is not installed")
    script = tmp_path / "overview_check.js"
    script.write_text(
        'const vm = require("vm"), fs = require("fs");\n'
        "const ctx = { window: {}, document: { addEventListener() {} }, Date, Math,\n"
        "  String, Number };\n"
        "vm.createContext(ctx);\n"
        f"for (const f of ['common.js', 'overview.js'])\n"
        f"  vm.runInContext(fs.readFileSync({str(STATIC)!r} + '/' + f, 'utf8'), ctx);\n"
        "ctx.window.hc.formatTime = function (t) { return 'T' + t; };\n"
        "const O = ctx.window.hcOverview;\n"
        f"console.log(JSON.stringify((function () {{ {body} }})()));\n"
    )
    done = subprocess.run(
        [NODE, str(script)], capture_output=True, text=True, timeout=60, check=True
    )
    return json.loads(done.stdout)


def test_overview_shows_values_of_an_online_experiment(tmp_path):
    out = run_overview(
        tmp_path,
        "return O.valueView({last: [100, 12.5], unit: 'V'}, true);",
    )
    assert out == {"text": "12.5 V", "title": "at T100"}


def test_overview_shows_an_offline_experiment_as_unknown(tmp_path):
    out = run_overview(
        tmp_path,
        """return [
          O.valueView({last: [100, 12.5], unit: 'V'}, false),
          O.valueView({last: [100, '<b>on</b>'], unit: null}, false),
          O.valueView({last: [100, null], unit: 'V'}, false),
          O.valueView({last: null, unit: 'V'}, false),
          O.valueView({last: null, unit: 'V'}, true),
        ];""",
    )
    assert out == [
        {"text": "unknown", "title": "Last known: 12.5 V at T100"},
        {"text": "unknown", "title": "Last known: <b>on</b> at T100"},  # as text only
        {"text": "unknown", "title": "Last known: unknown at T100"},
        {"text": "no data", "title": ""},
        {"text": "no data", "title": ""},
    ]


def test_overview_puts_values_on_the_page_as_text_only():
    text = (STATIC / "overview.js").read_text()
    assert "innerHTML" not in text and "insertAdjacentHTML" not in text
    assert "view.text" in text and "value.title" in text


def run_notify(tmp_path, body: str):
    """Evaluate ``body`` with ``N`` = window.hcNotify of notify.js and a fake storage."""
    if NODE is None:
        pytest.skip("node is not installed")
    script = tmp_path / "notify_check.js"
    script.write_text(
        'const vm = require("vm"), fs = require("fs");\n'
        "const store = {};\n"
        "const localStorage = {\n"
        "  getItem(k) { return k in store ? store[k] : null; },\n"
        "  setItem(k, v) { store[k] = String(v); },\n"
        "};\n"
        "const ctx = { window: { localStorage }, document: { addEventListener() {} },\n"
        "  Date, Math, String, Number };\n"
        "vm.createContext(ctx);\n"
        f"vm.runInContext(fs.readFileSync({str(STATIC / 'notify.js')!r}, 'utf8'), ctx);\n"
        "const N = ctx.window.hcNotify;\n"
        f"console.log(JSON.stringify((function () {{ {body} }})()));\n"
    )
    done = subprocess.run(
        [NODE, str(script)], capture_output=True, text=True, timeout=60, check=True
    )
    return json.loads(done.stdout)


def test_notify_first_load_starts_at_the_newest_id(tmp_path):
    out = run_notify(
        tmp_path,
        "return N.planEvents(null, {last_id: 7, events: [{id: 7, t: 1}]});",
    )
    assert out == {"next": 7, "fresh": []}  # history is not replayed


def test_notify_announces_late_events_with_older_times(tmp_path):
    out = run_notify(
        tmp_path,
        """const first = N.planEvents(5, {last_id: 6, events: [
          {id: 6, t: 100, experiment: 'B', action: 'triggered'}]});
        // an event of another experiment arrives later, with an older t
        const second = N.planEvents(first.next, {last_id: 7, events: [
          {id: 7, t: 50, experiment: 'C', action: 'triggered'}]});
        return [first, second];""",
    )
    assert [[e["id"] for e in plan["fresh"]] for plan in out] == [[6], [7]]
    assert [plan["next"] for plan in out] == [6, 7]


def test_notify_does_not_repeat_and_follows_a_reset_database(tmp_path):
    out = run_notify(
        tmp_path,
        """return [
          N.planEvents(7, {last_id: 7, events: []}),
          N.planEvents(7, {last_id: 7, events: [{id: 7}]}),  // seen in another tab
          N.planEvents(40, {last_id: 3, events: []}),  // the server's ids restarted
        ];""",
    )
    assert out == [
        {"next": 7, "fresh": []},
        {"next": 7, "fresh": []},
        {"next": 3, "fresh": []},
    ]


def test_notify_remembers_the_id_in_local_storage(tmp_path):
    out = run_notify(
        tmp_path,
        """const before = N.readLastId();
        N.writeLastId(12);
        return [before, N.readLastId()];""",
    )
    assert out == [None, 12]
