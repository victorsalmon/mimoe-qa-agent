"""Deterministic API assertions: the model never decides pass or fail."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

from .config import local_url
from .http_client import RequestError, request


@dataclass(frozen=True)
class Check:
    id: str
    description: str
    path: str
    expected_status: int
    expected_json: dict


@dataclass(frozen=True)
class CheckResult:
    check: Check
    outcome: str
    actual_status: int | None
    actual_body: str
    assertions: list[str]
    duration_ms: float

    def to_dict(self) -> dict:
        return asdict(self)


def load_suite(path: Path) -> list[Check]:
    """Reject malformed suites up front, including paths that escape the target."""
    if path.stat().st_size > 64 * 1024:
        raise ValueError("Suite exceeds 64 KiB.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not 1 <= len(raw) <= 50:
        raise ValueError("Suite must contain 1 to 50 checks.")
    checks, ids = [], set()
    fields = {"id", "description", "path", "expected_status", "expected_json"}
    for item in raw:
        if not isinstance(item, dict) or set(item) != fields:
            raise ValueError(f"Each check must have exactly these fields: {', '.join(sorted(fields))}.")
        if any(not isinstance(item[k], str) or not item[k].strip() for k in ("id", "description", "path")):
            raise ValueError("Check id, description, and path must be nonempty strings.")
        path_value = item["path"]
        parsed = urlsplit(path_value)
        if (not path_value.startswith("/") or path_value.startswith("//")
                or parsed.scheme or parsed.netloc or parsed.fragment
                or "\\" in path_value or any(ord(c) <= 32 for c in path_value)):
            raise ValueError("Check paths must start with one slash and contain no host, fragment, whitespace, or backslash.")
        if item["id"] in ids:
            raise ValueError("Check ids must be unique.")
        if type(item["expected_status"]) is not int or not 100 <= item["expected_status"] <= 599:
            raise ValueError("expected_status must be an integer HTTP status from 100 to 599.")
        if not isinstance(item["expected_json"], dict):
            raise ValueError("expected_json must be an object of top-level fields to compare.")
        ids.add(item["id"])
        checks.append(Check(**item))
    return checks


def run_check(base_url: str, check: Check, timeout: float = 10.0) -> CheckResult:
    """Compare status and each specified top-level JSON value, with strict types."""
    base_url = local_url(base_url)
    started = time.monotonic()
    status, body, errors, outcome = None, "", [], "PASS"
    try:
        response = request(base_url + check.path, timeout=timeout)
        status, body = response.status, response.body
        if status != check.expected_status:
            errors.append(f"Expected HTTP {check.expected_status}; received HTTP {status}.")
        if check.expected_json:
            actual = response.json()
            for key, expected in check.expected_json.items():
                if not isinstance(actual, dict) or key not in actual:
                    errors.append(f"Missing JSON field {key!r}.")
                elif type(actual[key]) is not type(expected) or actual[key] != expected:
                    errors.append(f"Field {key!r}: expected {json.dumps(expected)}; received {json.dumps(actual[key])}.")
        if errors:
            outcome = "FAIL"
    except RequestError as exc:
        outcome = "ERROR"
        errors.append(str(exc))
    return CheckResult(check, outcome, status, body[:4000], errors,
                       round((time.monotonic() - started) * 1000, 2))
