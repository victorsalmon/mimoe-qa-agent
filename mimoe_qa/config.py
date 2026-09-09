"""Validate configuration before making requests; inference stays local."""

from dataclasses import dataclass
import ipaddress
import math
import os
from urllib.parse import urlsplit


def local_url(value: str) -> str:
    """Allow localhost or literal private/loopback IPs, without credentials."""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
        allowed = host == "localhost"
        if host and not allowed:
            address = ipaddress.ip_address(host)
            allowed = (address.is_loopback or address.is_private) and not (
                address.is_unspecified or address.is_multicast or address.is_link_local
            )
        if (parsed.scheme not in {"http", "https"} or not allowed
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or port == 0):
            raise ValueError
    except ValueError:
        raise ValueError("Use an http(s) URL with localhost or a private IP, no credentials/query/fragment.") from None
    return value.rstrip("/")


@dataclass(frozen=True)
class Settings:
    """Environment-driven connection settings; never included in reports."""

    base_url: str
    model: str
    api_key: str
    timeout: float = 60.0

    @classmethod
    def from_environment(cls) -> "Settings":
        base = local_url(os.getenv("MIMOE_BASE_URL", "http://localhost:8083/mimik-ai/openai/v1"))
        model = os.getenv("MIMOE_MODEL", "smollm-360m").strip()
        key = os.getenv("MIMOE_API_KEY", "1234")
        try:
            timeout = float(os.getenv("MIMOE_TIMEOUT", "60"))
        except ValueError:
            raise ValueError("MIMOE_TIMEOUT must be a positive number of seconds.") from None
        if not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise ValueError("MIMOE_TIMEOUT must be between 0 and 300 seconds (exclusive of 0).")
        if not model or not key or any(c in key for c in "\r\n"):
            raise ValueError("MIMOE_MODEL and MIMOE_API_KEY must be nonempty; keys cannot contain newlines.")
        return cls(base, model, key, timeout)
