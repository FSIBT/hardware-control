"""Server configuration."""

import math
import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_CONFIG_PATH = Path("/etc/hc-web/config.toml")


class ConfigError(ValueError):
    """The configuration is unusable; the message says what to fix."""


def _normalise_origin(origin: object) -> str:
    """``origin`` as browsers write it: scheme://host[:port], lower case.

    Raises ``ConfigError`` for anything else (no path, query, fragment or
    credentials; http or https only). A trailing ``/`` is accepted and removed.
    """
    if not isinstance(origin, str):
        raise ConfigError(f"origin must be a string, not {type(origin).__name__}")
    try:
        parts = urlsplit(origin)
        host = parts.hostname
        parts.port  # noqa: B018 - raises ValueError for a bad port
    except ValueError as e:
        raise ConfigError(f"origin {origin!r} is not a valid URL: {e}") from None
    problem = None
    if parts.scheme.lower() not in ("http", "https"):
        problem = "must start with http:// or https://"
    elif not host or any(c.isspace() for c in parts.netloc):
        problem = "must contain a host name"
    elif parts.username is not None or parts.password is not None:
        problem = "must not contain a user name or password"
    elif parts.path.strip("/") or parts.query or parts.fragment:
        problem = "must not contain a path, query or fragment"
    elif "?" in origin or "#" in origin:  # empty ones, as in https://host?
        problem = "must not contain a path, query or fragment"
    if problem:
        shown = origin if "@" not in origin else origin.split("@", 1)[1]
        raise ConfigError(
            f"origin {shown!r} {problem} "
            "(expected something like https://monitor.example.org)"
        )
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


def _check(name: str, ok: bool, wanted: str, value: object) -> None:
    if not ok:
        raise ConfigError(f"{name} must be {wanted}, not {value!r}")


@dataclass
class Config:
    origin: str
    database: Path
    retention_days: float = 7
    site_name: str = "HC monitor"
    secure_cookies: bool = True
    # Reverse proxies in front of the app whose X-Forwarded-For/-Proto/-Host
    # headers are trusted (the documented Apache setup is one hop); 0 trusts none
    proxy_hops: int = 1

    def __post_init__(self):
        self.origin = _normalise_origin(self.origin)
        days = self.retention_days
        _check(
            "retention_days",
            isinstance(days, int | float)
            and not isinstance(days, bool)
            and math.isfinite(days)
            and days > 0,
            "a number of days greater than zero",
            days,
        )
        _check(
            "site_name",
            isinstance(self.site_name, str) and bool(self.site_name.strip()),
            "a non-empty string",
            self.site_name,
        )
        _check(
            "secure_cookies",
            isinstance(self.secure_cookies, bool),
            "true or false",
            self.secure_cookies,
        )
        hops = self.proxy_hops
        _check(
            "proxy_hops",
            isinstance(hops, int) and not isinstance(hops, bool) and hops >= 0,
            "a whole number, 0 or more",
            hops,
        )

    @property
    def rp_id(self) -> str:
        """WebAuthn relying party id: the hostname of ``origin`` (never empty)."""
        host = urlsplit(self.origin).hostname
        if not host:
            raise ConfigError(f"origin {self.origin!r} has no host name")
        return host


def load_config(path: Path | None = None) -> Config:
    """Load the configuration from a TOML file.

    The file is ``path``, else the environment variable ``HC_WEB_CONFIG``,
    else ``/etc/hc-web/config.toml``. A relative ``database`` is resolved
    against the directory of the config file. A bad file raises
    ``ConfigError`` naming the file and the setting; a missing file raises
    ``FileNotFoundError``.
    """
    if path is None:
        path = Path(os.environ.get("HC_WEB_CONFIG", DEFAULT_CONFIG_PATH))
    path = Path(path)
    with path.open("rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{path}: {e}") from None
    try:
        return _from_dict(data, path)
    except ConfigError as e:
        raise ConfigError(f"{path}: {e}") from None


def _from_dict(data: dict, path: Path) -> Config:
    known = {f.name for f in fields(Config)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ConfigError(
            f"unknown setting {', '.join(map(repr, unknown))} "
            f"(known settings: {', '.join(sorted(known))})"
        )
    missing = [k for k in ("origin", "database") if k not in data]
    if missing:
        raise ConfigError(f"{' and '.join(missing)} required")
    data = dict(data)
    name = data.pop("database")
    _check("database", isinstance(name, str) and bool(name), "a file name", name)
    database = Path(name)
    if not database.is_absolute():
        database = path.parent / database
    return Config(database=database, **data)
