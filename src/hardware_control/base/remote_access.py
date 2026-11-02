"""Access control for requests from other programs, e.g. hc-query and hc-mcp."""

import enum
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import re
import secrets
import time

from platformdirs import user_config_dir

logger = logging.getLogger(__name__)

DURATION_PATTERN = re.compile(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?")


class AccessMode(enum.StrEnum):
    """What other programs are allowed to do."""

    OFF = "off"
    READ_ONLY = "read-only"
    FULL = "full"


def parse_duration(text: str | int) -> int:
    """Convert a duration into seconds.

    Parameters
    ----------
    text
        A number of minutes, or a combination of days, hours and minutes,
        e.g. "2d8h4m". 0 means no time limit.

    Raises
    ------
    ValueError
        If the text is not a valid duration
    """
    text = "".join(str(text).lower().split())
    if not text:
        return 0
    if text.isdigit():
        return int(text) * 60

    match = DURATION_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"Invalid duration '{text}', use e.g. 90 or 2d8h4m")
    days, hours, minutes = (int(group or 0) for group in match.groups())
    return (days * 24 * 60 + hours * 60 + minutes) * 60


def format_duration(seconds: float) -> str:
    """Format seconds in the format of parse_duration, rounding up to minutes."""
    minutes = int((seconds + 59) // 60)
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    parts = [
        f"{value}{unit}"
        for value, unit in ((days, "d"), (hours, "h"), (minutes, "m"))
        if value
    ]
    return "".join(parts) or "0m"


def generate_token() -> str:
    """Create a random token."""
    return secrets.token_urlsafe(32)


class RemoteAccess:
    """The access mode, its time limit and the optional token of an App.

    The mode starts as off, unless it was saved with persist=True. Only a
    salted hash of the token is kept.

    Parameters
    ----------
    app_name
        The name of the App, used to save settings per App
    directory
        Where to save the settings (default: the user's config directory)
    """

    def __init__(self, app_name: str, directory: str | Path | None = None) -> None:
        self.app_name = app_name
        if directory is None:
            directory = Path(user_config_dir("hardware-control", "lbnl"))
        self.directory = Path(directory) / "remote_access"

        self._mode = AccessMode.OFF
        self.expires_at = None
        self.persist = False
        self._token_salt = None
        self._token_hash = None
        self._load()

    @property
    def filename(self) -> Path:
        """The file with the saved settings of this App."""
        digest = hashlib.sha256(self.app_name.encode()).hexdigest()[:16]
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", self.app_name)
        return self.directory / f"{safe_name}-{digest}.json"

    @property
    def mode(self) -> AccessMode:
        """The current mode, going back to off if the time limit has passed."""
        if self.expires_at is not None and time.time() >= self.expires_at:
            logger.info(f"Remote access time limit reached for '{self.app_name}'")
            self.configure(AccessMode.OFF)
        return self._mode

    @property
    def token_required(self) -> bool:
        """Whether requests need to provide a token."""
        return self._token_hash is not None

    def remaining(self) -> float | None:
        """Return the seconds until the time limit, or None if there is none."""
        if self.mode is AccessMode.OFF or self.expires_at is None:
            return None
        return self.expires_at - time.time()

    def configure(
        self,
        mode: AccessMode | str,
        duration: str | int = 0,
        persist: bool = False,
        token: str | None = None,
    ) -> None:
        """Change the access settings.

        Parameters
        ----------
        mode
            The new mode
        duration
            See :func:`parse_duration`. The mode goes back to off afterwards.
        persist
            If True, the settings survive a restart of the program. A time
            limit keeps its end time, so a restart does not extend it.
        token
            A new token. An empty string removes the token and None keeps
            the current one.
        """
        mode = AccessMode(mode)
        seconds = parse_duration(duration)

        if token is not None:
            self._set_token(token)

        self._mode = mode
        self.expires_at = None
        self.persist = persist and mode is not AccessMode.OFF
        if seconds and mode is not AccessMode.OFF:
            self.expires_at = time.time() + seconds

        logger.info(
            f"Remote access for '{self.app_name}' set to '{mode}' "
            f"(time limit: {format_duration(seconds) if seconds else 'none'}, "
            f"keep after restart: {self.persist}, token: {self.token_required})"
        )
        self._save()

    def check_token(self, token: str | None) -> bool:
        """Return whether a request with this token may continue."""
        if self._token_hash is None:
            return True
        if not isinstance(token, str):
            return False
        return hmac.compare_digest(
            self._hash(token, self._token_salt), self._token_hash
        )

    @staticmethod
    def _hash(token: str, salt: str) -> str:
        return hashlib.sha256((salt + token).encode()).hexdigest()

    def _set_token(self, token: str) -> None:
        if not token:
            self._token_salt = self._token_hash = None
            return
        self._token_salt = secrets.token_hex(16)
        self._token_hash = self._hash(token, self._token_salt)

    def _save(self) -> None:
        """Save the settings if they should survive a restart."""
        try:
            if not self.persist:
                self.filename.unlink(missing_ok=True)
                return
            self.directory.mkdir(parents=True, exist_ok=True)
            data = {
                "mode": str(self._mode),
                "expires_at": self.expires_at,
                "token_salt": self._token_salt,
                "token_hash": self._token_hash,
            }
            # only the user may read or change this file
            fd = os.open(self.filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump(data, f)
        except OSError as e:
            logger.warning(f"Failed to save remote access settings: {e}")

    def _load(self) -> None:
        """Load saved settings. Anything invalid or expired leaves the mode off."""
        try:
            with open(self.filename) as f:
                data = json.load(f)
            mode = AccessMode(data["mode"])
            expires_at = data["expires_at"]
            salt, token_hash = data["token_salt"], data["token_hash"]
            if expires_at is not None:
                expires_at = float(expires_at)
        except FileNotFoundError:
            return
        except (OSError, ValueError, KeyError, TypeError) as e:
            logger.warning(f"Ignoring invalid remote access settings: {e}")
            return

        if expires_at is not None and time.time() >= expires_at:
            logger.info(f"Saved remote access for '{self.app_name}' has expired")
            self._save()
            return

        self._mode = mode
        self.expires_at = expires_at
        self.persist = True
        self._token_salt = salt
        self._token_hash = token_hash
        logger.info(f"Restored remote access mode '{mode}' for '{self.app_name}'")
