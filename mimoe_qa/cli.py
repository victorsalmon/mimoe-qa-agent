"""User entry points and dependency wiring; business logic lives in modules."""

import argparse
import sys
from contextlib import nullcontext
from pathlib import Path

from .agent import run_agent
from .checks import load_suite
from .config import Settings, local_url
from .demo import demo_service
from .http_client import RequestError
from .inference import MimOEClient
from .reporting import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local API checks and draft bug analysis with mimOE.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Verify model discovery and a real completion.")
    for name in ("demo", "run"):
        help_text = "Run the included buggy API." if name == "demo" else "Check a local API using a JSON suite."
        command = sub.add_parser(name, help=help_text)
        command.add_argument(
            "--output", type=Path, default=Path("reports/latest"),
            help="Report directory; existing report files are replaced.")
        command.add_argument("--no-ai", action="store_true", help="Run deterministic checks without inference.")
        command.add_argument("--max-analyses", type=int, choices=range(1, 6), default=3, metavar="1..5")
        if name == "run":
            command.add_argument("--target", required=True, help="Local API base URL.")
            command.add_argument("--suite", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        settings = None if getattr(args, "no_ai", False) else Settings.from_environment()
        client = MimOEClient(settings) if settings else None
        if args.command == "doctor":
            models = client.models()
            if settings.model not in models:
                raise ValueError(f"Configured model is unavailable. Available model IDs: {', '.join(models)}")
            client.complete("Reply with a short greeting.")
            print(f"mimOE is ready: {settings.model}; discovery and completion succeeded.")
            return 0
        suite = args.suite if args.command == "run" else Path(__file__).with_name("demo_suite.json")
        checks = load_suite(suite)
        context = demo_service() if args.command == "demo" else nullcontext(local_url(args.target))
        print(f"Running {len(checks)} local checks; AI analysis {'enabled' if client else 'disabled'}.", flush=True)
        with context as target:
            report = run_agent(target, checks, client, settings.model if settings else None, args.max_analyses)
        md, structured = write_report(report, args.output)
        print(" | ".join(f"{key}: {value}" for key, value in report.counts.items()))
        print(f"Reports: {md.resolve()} and {structured.resolve()}")
        if report.analysis_errors:
            print("AI analysis failed; assertion evidence was preserved. See the report.", file=sys.stderr)
        if args.command == "demo":
            print("Expected demo result: 4 PASS, 2 FAIL (intentional defects); exit code 1.")
        return report.exit_code
    except (ValueError, OSError, RequestError, RecursionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
