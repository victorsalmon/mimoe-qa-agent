"""Exercise local HTTP failures and validate the mimOE request contract."""

import json
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch

from mimoe_qa.config import Settings, local_url
from mimoe_qa.http_client import MAX_RESPONSE_BYTES, RequestError, Response, request
from mimoe_qa.inference import MimOEClient


@contextmanager
def fixture_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/ok")
                self.end_headers()
                return
            self.send_response(404 if self.path == "/missing" else 200)
            self.end_headers()
            self.wfile.write(b"x" * (MAX_RESPONSE_BYTES + 1) if self.path == "/large" else b'{"ok":true}')

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.captured = (self.path, self.headers["Authorization"], body)
            self.send_response(200)
            self.end_headers()
            payload = {"choices": [{"message": {"content": "Observed defect"}, "finish_reason": "stop"}]}
            self.wfile.write(json.dumps(payload).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class BoundaryTests(unittest.TestCase):
    def test_local_url_policy(self):
        for url in ("http://localhost:8083", "http://10.10.10.175:8083", "http://127.0.0.1", "http://[::1]:8083"):
            self.assertEqual(local_url(url), url)
        bad_urls = (
            "https://example.com", "http://8.8.8.8", "file:///tmp/x", "http://localhost:bad",
            "http://u:p@localhost", "http://0.0.0.0", "http://169.254.169.254", "http://localhost?q=x",
        )
        for url in bad_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                local_url(url)

    def test_invalid_environment_timeout(self):
        for value in ("nan", "inf", "0", "-1", "abc", "301"):
            with patch.dict("os.environ", {"MIMOE_TIMEOUT": value}), self.assertRaises(ValueError):
                Settings.from_environment()

    def test_http_errors_are_assertable_and_redirects_are_not_followed(self):
        with fixture_server() as (_, base):
            self.assertEqual(request(base + "/missing").status, 404)
            self.assertEqual(request(base + "/redirect").status, 302)

    def test_response_size_is_bounded(self):
        with fixture_server() as (_, base), self.assertRaisesRegex(RequestError, "64 KiB"):
            request(base + "/large")

    def test_transport_error_does_not_leak_exception_secrets(self):
        with patch("mimoe_qa.http_client.build_opener") as opener:
            opener.return_value.open.side_effect = OSError("secret-token")
            with self.assertRaises(RequestError) as raised:
                request("http://localhost")
        self.assertNotIn("secret-token", str(raised.exception))

    def test_real_http_inference_contract(self):
        with fixture_server() as (server, base):
            client = MimOEClient(Settings(base + "/mimik-ai/openai/v1", "smollm-360m", "test-key"))
            self.assertEqual(client.complete("Analyze this"), "Observed defect")
            route, auth, body = server.captured
        self.assertEqual(route, "/mimik-ai/openai/v1/chat/completions")
        self.assertEqual(auth, "Bearer test-key")
        self.assertEqual(body["model"], "smollm-360m")
        self.assertFalse(body["stream"])
        self.assertEqual(body["messages"][-1]["content"], "Analyze this")
        self.assertLessEqual(body["max_tokens"], 256)

    def test_malformed_completions_are_rejected(self):
        client = MimOEClient(Settings("http://localhost", "model", "test-key"))
        for raw in ({}, {"choices": []}, {"choices": [{"message": {"content": ""}}]}, None):
            with (
                patch("mimoe_qa.inference.request", return_value=Response(200, json.dumps(raw))),
                self.assertRaises(RequestError),
            ):
                client.complete("Hello")

    def test_model_http_error_has_no_raw_body(self):
        client = MimOEClient(Settings("http://localhost", "model", "test-key"))
        with (
            patch("mimoe_qa.inference.request", return_value=Response(401, "secret-token")),
            self.assertRaisesRegex(RequestError, "HTTP 401") as raised,
        ):
            client.complete("Hello")
        self.assertNotIn("secret-token", str(raised.exception))

    def test_token_limit_is_visible(self):
        client = MimOEClient(Settings("http://localhost", "model", "test-key"))
        raw = {"choices": [{"message": {"content": "Partial"}, "finish_reason": "length"}]}
        with patch("mimoe_qa.inference.request", return_value=Response(200, json.dumps(raw))):
            self.assertIn("may be incomplete", client.complete("Hello"))

    def test_model_discovery_validates_shape(self):
        client = MimOEClient(Settings("http://localhost", "model", "test-key"))
        with patch("mimoe_qa.inference.request", return_value=Response(200, '{"data":[{"id":"model"}]}')):
            self.assertEqual(client.models(), ["model"])
        with (
            patch("mimoe_qa.inference.request", return_value=Response(200, '{"data":[null]}')),
            self.assertRaises(RequestError),
        ):
            client.models()
