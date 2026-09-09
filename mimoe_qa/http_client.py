"""Small HTTP boundary with bounded responses, no proxies, and no redirects."""

from dataclasses import dataclass
from http.client import HTTPException
import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_RESPONSE_BYTES = 64 * 1024


class RequestError(RuntimeError):
    """Transport or protocol failure safe to display without request secrets."""


class NoRedirects(HTTPRedirectHandler):
    """Never forward local requests or authorization to another origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Response:
    status: int
    body: str

    def json(self):
        try:
            return json.loads(self.body)
        except (ValueError, RecursionError):
            raise RequestError("Endpoint returned invalid JSON.") from None


def request(url: str, *, payload: dict | None = None,
            headers: dict | None = None, timeout: float = 10.0) -> Response:
    """Return HTTP errors as responses so checks can assert 4xx/5xx status."""
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=request_headers)
    opener = build_opener(ProxyHandler({}), NoRedirects())
    try:
        try:
            response = opener.open(req, timeout=timeout)
        except HTTPError as exc:
            response = exc
        with response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise RequestError("Response exceeded the 64 KiB limit.")
            return Response(response.code, body.decode("utf-8", errors="replace"))
    except (URLError, OSError, ValueError, HTTPException) as exc:
        # Do not include exception text: it can contain URLs or credentials.
        raise RequestError(f"Local request failed ({type(exc).__name__}); check the service, address, and timeout.") from None
