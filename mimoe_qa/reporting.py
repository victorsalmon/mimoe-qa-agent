"""Serialize evidence and visibly separate it from unverified model output."""

import json
from pathlib import Path

from .agent import RunReport


def block(text: str) -> str:
    """Indent untrusted content so it cannot inject report headings or HTML."""
    return "\n".join("    " + line.rstrip() if line.strip() else ""
                     for line in text.splitlines()) or "    (empty)"


def write_report(report: RunReport, directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1, "created_at": report.created_at,
        "counts": report.counts, "exit_code": report.exit_code, "model": report.model,
        "results": [result.to_dict() for result in report.results],
        "analysis": report.analysis, "analysis_errors": report.analysis_errors,
    }
    json_path, md_path = directory / "report.json", directory / "report.md"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Local QA report", "", f"Run: {report.created_at}", "",
             " | ".join(f"{key}: {value}" for key, value in report.counts.items()), "",
             "Assertions determine outcomes. AI notes are unverified drafts for human review.", "",
             "Model: " + (report.model or "disabled"), "",
             "Bodies are limited to 4,000 characters. No follow-up tests suggested by AI were executed.", ""]
    for index, result in enumerate(report.results, 1):
        lines.extend([f"## Check {index}: {result.outcome}", "", block(
            f"ID: {result.check.id}\n{result.check.description}\n"
            f"Reproduce: GET {result.check.path}\n"
            f"Expected HTTP: {result.check.expected_status}\n"
            f"Expected JSON fields: {json.dumps(result.check.expected_json)}\n"
            f"Actual HTTP: {result.actual_status}\nDuration: {result.duration_ms} ms"
        ), "", "### Assertion evidence", "", block("\n".join(result.assertions) or "All assertions passed."), "",
            "### Response body", "", block(result.actual_body), ""])
        if result.outcome != "PASS":
            lines.extend(["### Bug draft — derived from assertions", "", block(
                f"Title: {result.check.description}\n"
                f"Steps: Send GET {result.check.path}; compare the response with the expected contract above.\n"
                f"Observed: {' '.join(result.assertions)}\n"
                "Root cause and severity: not established by these checks."
            ), ""])
        if result.check.id in report.analysis:
            lines.extend(["### AI draft — unverified", "", block(report.analysis[result.check.id]), ""])
        elif result.check.id in report.analysis_errors:
            lines.extend(["### Analysis unavailable", "", block(report.analysis_errors[result.check.id]), ""])
        elif result.outcome != "PASS":
            lines.extend(["AI analysis was skipped (disabled, budget reached, or an earlier inference error).", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path
