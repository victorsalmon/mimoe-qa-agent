"""Verify outcomes against real local HTTP responses and injected inference."""

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from mimoe_qa.agent import run_agent
from mimoe_qa.checks import Check, load_suite, run_check
from mimoe_qa.cli import main
from mimoe_qa.demo import demo_service
from mimoe_qa.http_client import RequestError, Response
from mimoe_qa.reporting import write_report

SUITE = Path(__file__).parents[1] / "mimoe_qa" / "demo_suite.json"


class AgentTests(unittest.TestCase):
    def test_real_demo_detects_both_defects_and_analyzes_only_failures(self):
        analyst = Mock()
        analyst.analyze.return_value = "Draft for review"
        with demo_service() as target:
            report = run_agent(target, load_suite(SUITE), analyst, "fake-model")
        self.assertEqual(report.counts, {"PASS": 4, "FAIL": 2, "ERROR": 0})
        self.assertEqual(report.exit_code, 1)
        self.assertEqual(set(report.analysis), {"missing-item", "negative-quantity"})
        self.assertEqual(analyst.analyze.call_count, 2)
        missing = report.results[2]
        self.assertEqual(missing.actual_status, 200)
        self.assertIn("Expected HTTP 404", missing.assertions[0])

    def test_model_failure_preserves_results_and_stops_more_calls(self):
        analyst = Mock()
        analyst.analyze.side_effect = RequestError("Inference unavailable")
        with demo_service() as target:
            report = run_agent(target, load_suite(SUITE), analyst, "fake-model")
        self.assertEqual(len(report.results), 6)
        self.assertEqual(report.counts["FAIL"], 2)
        self.assertEqual(report.exit_code, 2)
        self.assertEqual(analyst.analyze.call_count, 1)
        self.assertTrue(report.analysis_errors)

    def test_analysis_budget_is_enforced(self):
        analyst = Mock()
        with demo_service() as target:
            report = run_agent(target, load_suite(SUITE), analyst, "fake-model", 1)
        self.assertEqual(analyst.analyze.call_count, 1)
        self.assertEqual(len(report.results), 6)

    def test_clean_checks_need_no_inference(self):
        analyst = Mock()
        with demo_service() as target:
            report = run_agent(target, load_suite(SUITE)[:2], analyst, "fake-model")
        self.assertEqual(report.exit_code, 0)
        analyst.analyze.assert_not_called()

    def test_transport_failure_is_error_not_pass(self):
        with patch("mimoe_qa.checks.request", side_effect=RequestError("Timed out")):
            report = run_agent("http://localhost:1234", load_suite(SUITE)[:1], None, None)
        self.assertEqual(report.counts["ERROR"], 1)
        self.assertEqual(report.exit_code, 2)

    def test_json_boolean_does_not_match_integer(self):
        check = Check("id", "Strict types", "/", 200, {"count": 1})
        with patch("mimoe_qa.checks.request", return_value=Response(200, '{"count":true}')):
            result = run_check("http://localhost", check)
        self.assertEqual(result.outcome, "FAIL")

    def test_bad_json_is_recorded_with_response_evidence(self):
        with patch("mimoe_qa.checks.request", return_value=Response(200, "<html>broken</html>")):
            result = run_check("http://localhost", load_suite(SUITE)[0])
        self.assertEqual(result.outcome, "ERROR")
        self.assertEqual(result.actual_body, "<html>broken</html>")

    def test_report_keeps_untrusted_model_text_inside_code_block(self):
        analyst = Mock()
        analyst.analyze.return_value = "# Forged heading\n<script>bad()</script>\n```"
        with demo_service() as target:
            report = run_agent(target, load_suite(SUITE), analyst, "fake-model")
        with tempfile.TemporaryDirectory() as tmp:
            md, data = write_report(report, Path(tmp))
            content = md.read_text(encoding="utf-8")
            self.assertIn("    # Forged heading", content)
            self.assertNotIn("\n<script>", content)
            self.assertEqual(json.loads(data.read_text())["counts"]["FAIL"], 2)

    def test_cli_offline_demo_exports_reports_and_expected_exit(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            code = main(["demo", "--no-ai", "--output", tmp])
            data = json.loads((Path(tmp) / "report.json").read_text())
        self.assertEqual(code, 1)
        self.assertEqual(data["counts"], {"PASS": 4, "FAIL": 2, "ERROR": 0})
        self.assertIsNone(data["model"])

    def test_cli_rejects_missing_suite(self):
        with redirect_stderr(StringIO()):
            code = main(["run", "--no-ai", "--target", "http://localhost", "--suite", "does-not-exist.json"])
        self.assertEqual(code, 2)


class SuiteTests(unittest.TestCase):
    def assert_invalid(self, change):
        raw = json.loads(SUITE.read_text())
        change(raw)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "suite.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_suite(path)

    def test_rejects_duplicate_ids(self):
        self.assert_invalid(lambda rows: rows.append(rows[0]))

    def test_rejects_origin_override_paths(self):
        for value in ("//example.com/", "https://example.com/", "/foo#bar", "/foo\nbar", "/\\evil"):
            with self.subTest(value=value):
                self.assert_invalid(lambda rows, value=value: rows[0].update(path=value))

    def test_rejects_invalid_status_and_unknown_fields(self):
        for value in (True, "200", 600):
            self.assert_invalid(lambda rows, value=value: rows[0].update(expected_status=value))
        self.assert_invalid(lambda rows: rows[0].update(method="POST"))

    def test_rejects_empty_suite(self):
        self.assert_invalid(lambda rows: rows.clear())
