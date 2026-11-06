"""Administration CLI for the web monitor server.

Usage:
  hc-web token create <experiment> <name> [--read-only] [--config=<file>]
  hc-web token list [--config=<file>]
  hc-web token revoke <id> [--config=<file>]
  hc-web status [--config=<file>]
  hc-web cleanup [--config=<file>]
  hc-web serve [--port=<port>] [--config=<file>]
  hc-web (-h | --help)
  hc-web --version

Commands:
  token create  Create an API token for an experiment (printed once)
  token list    List tokens (never shows the secrets)
  token revoke  Revoke a token by id
  status        Show database and usage summary
  cleanup       Delete data older than retention_days now
  serve         Run the Flask development server (local testing only)

Options:
  --read-only       Create a read-only token (default: write)
  --port=<port>     Port for the development server [default: 5000]
  --config=<file>   Config file (else $HC_WEB_CONFIG, else /etc/hc-web/config.toml)
  -h --help         Show this help message
  --version         Show version
"""

import sys
import time
from pathlib import Path

from docopt import docopt

from . import db, retention, tokens
from .config import load_config


def _fmt_time(t: float | None) -> str:
    if t is None:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))


def _load(args: dict):
    path = args["--config"]
    return load_config(Path(path) if path else None)


def cmd_token_create(args: dict) -> int:
    conn = db.connect(_load(args).database)
    try:
        try:
            token = tokens.create_token(
                conn,
                args["<experiment>"],
                args["<name>"],
                scope="read" if args["--read-only"] else "write",
            )
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    finally:
        conn.close()
    print(token)
    return 0


def cmd_token_list(args: dict) -> int:
    conn = db.connect(_load(args).database)
    try:
        rows = tokens.list_tokens(conn)
    finally:
        conn.close()
    print(
        f"{'ID':>4}  {'EXPERIMENT':<20} {'NAME':<20} {'SCOPE':<6} "
        f"{'CREATED':<19}  {'LAST USED':<19}  REVOKED"
    )
    for r in rows:
        print(
            f"{r['id']:>4}  {r['experiment'] or '-':<20} {r['name'] or '-':<20} "
            f"{r['scope']:<6} {_fmt_time(r['created']):<19}  "
            f"{_fmt_time(r['last_used']):<19}  {'yes' if r['revoked'] else 'no'}"
        )
    return 0


def cmd_token_revoke(args: dict) -> int:
    try:
        token_id = int(args["<id>"])
    except ValueError:
        print(f"Error: invalid token id {args['<id>']!r}", file=sys.stderr)
        return 1
    conn = db.connect(_load(args).database)
    try:
        ok = tokens.revoke_token(conn, token_id)
    finally:
        conn.close()
    if not ok:
        print(f"Error: no token with id {token_id}", file=sys.stderr)
        return 1
    print(f"Revoked token {token_id}")
    return 0


def cmd_status(args: dict) -> int:
    config = _load(args)
    conn = db.connect(config.database)
    try:

        def count(sql: str) -> int:
            return conn.execute(sql).fetchone()[0]

        print(f"Database:    {config.database}")
        print(f"Origin:      {config.origin}")
        print(f"Experiments: {count('SELECT COUNT(*) FROM experiments')}")
        print(f"Channels:    {count('SELECT COUNT(*) FROM channels')}")
        print(f"Points:      {count('SELECT COUNT(*) FROM points')}")
        print(
            "Tokens:      "
            f"{count('SELECT COUNT(*) FROM tokens WHERE revoked = 0')} active, "
            f"{count('SELECT COUNT(*) FROM tokens WHERE revoked = 1')} revoked"
        )
        print(f"Users:       {count('SELECT COUNT(*) FROM users')}")
    finally:
        conn.close()
    return 0


def cmd_cleanup(args: dict) -> int:
    config = _load(args)
    conn = db.connect(config.database)
    try:
        deleted = retention.cleanup(conn, time.time(), config.retention_days)
    finally:
        conn.close()
    for table, n in deleted.items():
        print(f"{table}: {n}")
    return 0


def cmd_serve(args: dict) -> int:
    from .app import create_app

    try:
        port = int(args["--port"])
    except ValueError:
        print(f"Error: invalid port {args['--port']!r}", file=sys.stderr)
        return 1
    app = create_app(_load(args))
    print(
        "WARNING: Flask development server, for local testing only; "
        "use a production WSGI server for deployment.",
        file=sys.stderr,
    )
    app.run(port=port)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for hc-web CLI."""
    args = docopt(__doc__, argv=argv, version="hc-web 1.0.0")
    try:
        if args["token"]:
            if args["create"]:
                return cmd_token_create(args)
            if args["list"]:
                return cmd_token_list(args)
            if args["revoke"]:
                return cmd_token_revoke(args)
        if args["status"]:
            return cmd_status(args)
        if args["cleanup"]:
            return cmd_cleanup(args)
        if args["serve"]:
            return cmd_serve(args)
    except FileNotFoundError as e:
        print(f"Error: cannot read config: {e}", file=sys.stderr)
        return 1
    print("Error: No command specified", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
