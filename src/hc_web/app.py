"""Flask application factory."""

import secrets
import sqlite3
from datetime import timedelta

from flask import Flask, current_app, g

from . import db
from .config import Config, load_config


def get_db() -> sqlite3.Connection:
    """Return the database connection of the current request."""
    if "db" not in g:
        g.db = db.connect(current_app.config["HC"].database)
    return g.db


def _close_db(exc=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def _secret_key(conn: sqlite3.Connection) -> str:
    """Return the persistent secret key, generating it on first start."""
    key = db.get_meta(conn, "secret_key")
    if key is None:
        # Several workers may start at once: the first insert wins.
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('secret_key', ?)",
                (secrets.token_hex(32),),
            )
        key = db.get_meta(conn, "secret_key")
    return key


def create_app(config: Config | None = None) -> Flask:
    if config is None:
        config = load_config()
    app = Flask(__name__)
    app.config["HC"] = config
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
    app.config["SESSION_COOKIE_SECURE"] = config.secure_cookies
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    config.database.parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(config.database)
    try:
        app.config["SECRET_KEY"] = _secret_key(conn)
    finally:
        conn.close()

    app.teardown_appcontext(_close_db)

    @app.context_processor
    def _site_context():
        return {"site_name": config.site_name}

    # imported here: these modules need get_db from this module
    from . import api, auth, views

    app.register_blueprint(api.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(views.admin)
    return app
