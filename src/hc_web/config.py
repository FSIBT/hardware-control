"""Server configuration."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_CONFIG_PATH = Path("/etc/hc-web/config.toml")


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

    @property
    def rp_id(self) -> str:
        """WebAuthn relying party id: the hostname of ``origin``."""
        return urlparse(self.origin).hostname or ""


def load_config(path: Path | None = None) -> Config:
    """Load the configuration from a TOML file.

    The file is ``path``, else the environment variable ``HC_WEB_CONFIG``,
    else ``/etc/hc-web/config.toml``. A relative ``database`` is resolved
    against the directory of the config file.
    """
    if path is None:
        path = Path(os.environ.get("HC_WEB_CONFIG", DEFAULT_CONFIG_PATH))
    path = Path(path)
    with path.open("rb") as f:
        data = tomllib.load(f)

    database = Path(data.pop("database"))
    if not database.is_absolute():
        database = path.parent / database
    return Config(database=database, **data)
