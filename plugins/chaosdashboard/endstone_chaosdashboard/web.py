"""Web server thread. It never touches the game: it reads snapshots and queues actions."""

import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from endstone_chaosdashboard.page import PAGE

ACTION_TIMEOUT_SECONDS = 10
MAX_BODY_BYTES = 16384


class DashboardServer:
    def __init__(self, plugin, host: str, port: int, token: str) -> None:
        self.plugin = plugin
        self.token = token
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _json(self, status: int, data: dict) -> None:
                self._send(status, json.dumps(data).encode("utf-8"))

            def _allowed(self) -> bool:
                sent = self.headers.get("X-Token", "")
                if hmac.compare_digest(sent.encode(), owner.token.encode()):
                    return True
                self._json(401, {"error": "Falsches Passwort."})
                return False

            def do_GET(self) -> None:
                if self.path == "/":
                    self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
                elif self.path == "/api/state" and self._allowed():
                    self._json(200, owner.plugin.snapshot)
                elif self.path != "/api/state":
                    self._json(404, {"error": "Nicht gefunden."})

            def do_POST(self) -> None:
                if self.path != "/api/action" or not self._allowed():
                    return
                length = int(self.headers.get("Content-Length", 0))
                if length > MAX_BODY_BYTES:
                    self._json(413, {"error": "Anfrage zu groß."})
                    return
                done = {"event": threading.Event()}
                owner.plugin.jobs.put((json.loads(self.rfile.read(length)), done))
                if not done["event"].wait(ACTION_TIMEOUT_SECONDS):
                    self._json(504, {"error": "Der Server hat nicht rechtzeitig geantwortet."})
                elif "error" in done:
                    self._json(400, {"error": done["error"]})
                else:
                    self._json(200, {"result": done["result"]})

        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
