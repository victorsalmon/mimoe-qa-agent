"""Bounded agent workflow: execute checks, select failures, analyze, report."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from .checks import Check, CheckResult, run_check
from .http_client import RequestError


class Analyst(Protocol):
    """Injection boundary lets tests replace inference without loading a model."""

    def analyze(self, result: CheckResult) -> str: ...


@dataclass(frozen=True)
class RunReport:
    created_at: str
    results: list[CheckResult]
    analysis: dict[str, str]
    analysis_errors: dict[str, str]
    model: str | None

    @property
    def counts(self) -> dict[str, int]:
        return {state: sum(r.outcome == state for r in self.results)
                for state in ("PASS", "FAIL", "ERROR")}

    @property
    def exit_code(self) -> int:
        """2 = incomplete/error; 1 = observed failures; 0 = clean execution."""
        if self.counts["ERROR"] or self.analysis_errors:
            return 2
        return 1 if self.counts["FAIL"] else 0


def run_agent(base_url: str, checks: list[Check], analyst: Analyst | None,
              model: str | None, max_analyses: int = 3) -> RunReport:
    """Run sequentially; cap model calls and stop inference on its first error."""
    results = [run_check(base_url, check) for check in checks]
    analysis, errors = {}, {}
    failures = [result for result in results if result.outcome != "PASS"]
    if analyst is not None:
        for result in failures[:max_analyses]:
            try:
                analysis[result.check.id] = analyst.analyze(result)
            except RequestError as exc:
                errors[result.check.id] = str(exc)
                break
    return RunReport(datetime.now(UTC).isoformat(), results, analysis, errors, model)
