"""Fixtures for the web monitor tests.

flask and hc_web are imported inside the fixtures only, so that test modules
which do not need them still collect on a plain install.
"""

import pytest


@pytest.fixture
def config(tmp_path):
    pytest.importorskip("flask")
    from hc_web.config import Config

    return Config(
        origin="http://localhost",
        database=tmp_path / "hc_web.sqlite",
        secure_cookies=False,
    )


@pytest.fixture
def server_app(config):
    from hc_web.app import create_app

    app = create_app(config)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(server_app):
    return server_app.test_client()


@pytest.fixture
def live_server(config):
    """A real server on a free local port: yields (url, write_token, read_token)."""
    import threading

    from hc_web import db
    from hc_web.app import create_app
    from hc_web.tokens import create_token
    from werkzeug.serving import make_server

    app = create_app(config)
    conn = db.connect(config.database)
    try:
        write_token = create_token(conn, "B", "lab pc")
        read_token = create_token(conn, "B", "viewer", scope="read")
    finally:
        conn.close()
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", write_token, read_token
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
