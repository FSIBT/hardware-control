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


class RestartableServer:
    """A live server that can be stopped and started again on the same port."""

    def __init__(self, app):
        self.app = app
        self.port = 0
        self._server = None
        self._thread = None

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    @property
    def running(self):
        return self._server is not None

    def start(self):
        import threading

        from werkzeug.serving import make_server

        self._server = make_server("127.0.0.1", self.port, self.app)
        self.port = self._server.server_port  # the free port chosen the first time
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self._server is None:
            return
        self._server.shutdown()
        self._thread.join()
        self._server.server_close()
        self._server = self._thread = None


@pytest.fixture
def restartable_server(config):
    """Like ``live_server``, but a ``RestartableServer`` with ``start``/``stop``.

    Yields ``(server, write_token, read_token)``; the same port is reused.
    """
    from hc_web import db
    from hc_web.app import create_app
    from hc_web.tokens import create_token

    app = create_app(config)
    conn = db.connect(config.database)
    try:
        write_token = create_token(conn, "B", "lab pc")
        read_token = create_token(conn, "B", "viewer", scope="read")
    finally:
        conn.close()
    server = RestartableServer(app)
    server.start()
    try:
        yield server, write_token, read_token
    finally:
        server.stop()
