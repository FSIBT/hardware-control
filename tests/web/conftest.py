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
