"""Client for the hc_web web monitor. One file, standard library only.

You can copy this file into your own project: it imports nothing but the
Python standard library (Python 3.11 or newer).

Push a value with ``curl`` (a write token belongs to one experiment; create
it on the server with ``hc-web token``). Only ``points`` is required, and a
channel that does not exist yet is created as a sampled channel::

    curl -H "Authorization: Bearer $TOKEN" \\
         -d '{"points": [{"channel": "temp", "t": 1762200000, "v": 21.5}]}' \\
         $URL/api/v1/push

``t`` is unix time in seconds and an unknown value is ``null``. The same
push from Python::

    from client import WebClient, WebClientError

    web = WebClient("https://monitor.example.org", token)
    try:
        web.send([("temp", time.time(), 21.5), ("humidity", time.time(), None)])
    except WebClientError as e:
        print("push failed:", e, "status:", e.status)  # status None: no answer

A push is also a heartbeat: the experiment is online while pushes keep
coming (by default one every 60 s is expected; pass ``"interval"`` to
``push()`` to say otherwise). Read data back with a read token::

    web = WebClient(url, read_token)
    web.data(["B/temp"], since=time.time() - 3600)  # channels are "<experiment>/<name>"
    web.status()
    web.events(since=time.time() - 86400)

Errors raise ``WebClientError``. Its ``status`` is the HTTP status, or
``None`` if there was no answer (connection refused, timeout, ...). A 409
(another run of this experiment is live) raises the subclass
``WebClientConflict``. The token is never part of an exception message or
of ``repr()``.

Proxy settings of the environment (``https_proxy`` and so on) are honoured, as
with any urllib program; to reach the server directly, add its host to
``no_proxy``.
"""

import http.client
import json
import math
import ssl
import urllib.error
import urllib.parse
import urllib.request

__all__ = ["WebClient", "WebClientConflict", "WebClientError"]


class WebClientError(Exception):
    """A request failed. ``status`` is the HTTP status, None without an answer."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class WebClientConflict(WebClientError):
    """HTTP 409: another run of the experiment is active."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: it could send the token to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _json_safe(value):
    """``value`` as JSON allows it: NaN and infinity (unknown) become None."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


class WebClient:
    """Talks to one hc_web server with one token.

    ``url`` is the base URL (http or https). With ``verify_tls=False`` the
    certificate of an https server is not checked (self-signed setups).
    """

    def __init__(
        self,
        url: str,
        token: str,
        timeout: float = 10.0,
        verify_tls: bool = True,
    ):
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError(f"url must start with http:// or https://, got {url!r}")
        if parts.username is not None or parts.password is not None:
            # not echoed: it would show the password
            raise ValueError("url must not contain user:password@")
        if (
            not token
            or not token.isascii()
            or any(c.isspace() or not c.isprintable() for c in token)
        ):
            # not echoed: it may be a secret
            raise ValueError(
                "token is empty or has non-ASCII, whitespace or control characters"
            )
        self.url = url.rstrip("/")
        self.timeout = timeout
        self._token = token
        self._context = None
        if parts.scheme == "https" and not verify_tls:
            self._context = ssl.create_default_context()
            self._context.check_hostname = False
            self._context.verify_mode = ssl.CERT_NONE
        elif parts.scheme == "https":
            self._context = ssl.create_default_context()
        handlers = [_NoRedirect()]
        if self._context is not None:
            handlers.append(urllib.request.HTTPSHandler(context=self._context))
        self._opener = urllib.request.build_opener(*handlers)

    def __repr__(self) -> str:
        return f"WebClient({self.url!r}, token=<hidden>)"

    # -- requests -----------------------------------------------------------

    def _request(self, path: str, body: dict | None = None) -> dict:
        data = None
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        if body is not None:
            try:
                data = json.dumps(body, allow_nan=False).encode()
            except (TypeError, ValueError) as e:
                raise WebClientError(f"body cannot be sent as JSON: {e}") from None
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.url + path, data=data, headers=headers)
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as e:
            with e:
                message = self._error_message(e)
            cls = WebClientConflict if e.code == 409 else WebClientError
            raise cls(f"HTTP {e.code}: {message}", e.code) from None
        except urllib.error.URLError as e:
            raise WebClientError(f"cannot reach {self.url}: {e.reason}") from None
        except http.client.HTTPException:
            # BadStatusLine, IncompleteRead, ...: their text can carry server data
            raise WebClientError(f"bad or incomplete answer from {self.url}") from None
        except (OSError, ValueError) as e:  # timeouts, resets
            raise WebClientError(f"request to {self.url} failed: {e}") from None
        try:
            result = json.loads(raw)
        except ValueError:
            raise WebClientError("the answer is not JSON", status) from None
        if not isinstance(result, dict):
            raise WebClientError("the answer is not a JSON object", status)
        return result

    @staticmethod
    def _error_message(error: urllib.error.HTTPError) -> str:
        """The server's ``{"error": ...}`` text, else the HTTP reason."""
        try:
            message = json.loads(error.read()).get("error")
        except (OSError, ValueError, AttributeError, http.client.HTTPException):
            message = None
        return str(message) if message else str(error.reason)

    def push(self, body: dict) -> dict:
        """POST a push body (a write token). Returns ``{"ok": true}``."""
        return self._request("/api/v1/push", body)

    def data(
        self, channels: list[str], since: float, until: float | None = None
    ) -> dict:
        """Points of ``"<experiment>/<channel>"`` names between since and until."""
        query = [("channels", ",".join(channels)), ("since", repr(float(since)))]
        if until is not None:
            query.append(("until", repr(float(until))))
        return self._request("/api/v1/data?" + urllib.parse.urlencode(query, safe="/,"))

    def status(self) -> dict:
        """Online state, latest values and latched alarms of all experiments."""
        return self._request("/api/v1/status")

    def events(self, since: float) -> dict:
        """Alarm events since ``since`` (unix time), oldest first."""
        query = urllib.parse.urlencode({"since": repr(float(since))})
        return self._request("/api/v1/events?" + query)

    def send(self, points: list[tuple[str, float, object]]) -> dict:
        """Push ``(channel, t, value)`` tuples with the minimal push body.

        An unknown value is ``None`` (NaN and infinity are sent as ``None``).
        Channels that do not exist yet are created as numeric (sampled)
        channels, so a first value that is a string is rejected with 400.
        """
        return self.push(
            {
                "points": [
                    {"channel": channel, "t": t, "v": _json_safe(value)}
                    for channel, t, value in points
                ]
            }
        )
