"""Loopback-only fixture service with two deliberate input-validation defects."""

import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve a tiny catalog API; missing items and negative quantities are buggy."""
        parsed = urlsplit(self.path)
        if parsed.path == "/health":
            status, body = 200, {"status": "ok"}
        elif parsed.path == "/items/1":
            status, body = 200, {"id": 1, "name": "Notebook", "price": 5}
        elif parsed.path.startswith("/items/"):
            # Intentional defect: the contract requires HTTP 404 for missing items.
            status, body = 200, {"error": "Item not found"}
        elif parsed.path == "/quote":
            try:
                quantity = int(parse_qs(parsed.query).get("quantity", ["1"])[0])
                # Intentional defect: negative quantities must be rejected with 400.
                status, body = 200, {"quantity": quantity, "total": quantity * 5}
            except ValueError:
                status, body = 400, {"error": "Quantity must be an integer"}
        else:
            status, body = 404, {"error": "Not found"}
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        """Keep request noise out of the CLI demo."""


@contextmanager
def demo_service():
    """Allocate an available loopback port and always release the server."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
