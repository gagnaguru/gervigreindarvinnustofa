"""Minimal SSE bridge for the workshop dashboard.

Serves dashboard.html on /, streams SSE on /events, accepts JSON POSTs on /event
which it broadcasts to every connected /events client. Stdlib only.
"""
from __future__ import annotations

import http.server
import queue
import socketserver
import threading
from pathlib import Path

PORT = 8765
ROOT = Path(__file__).parent
CLIENTS: list[queue.Queue] = []
LOCK = threading.Lock()


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a, **kw):
        pass

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            q: queue.Queue = queue.Queue()
            with LOCK:
                CLIENTS.append(q)
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    try:
                        msg = q.get(timeout=15)
                        self.wfile.write(f"data: {msg}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                with LOCK:
                    if q in CLIENTS:
                        CLIENTS.remove(q)
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            # Catch-all: any non-/events GET serves the dashboard so the
            # browser lands on the UI no matter which URL it opened.
            self._send_file("dashboard.html", "text/html")

    def do_POST(self):
        if self.path != "/event":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        with LOCK:
            for q in list(CLIENTS):
                q.put(body)
        self.send_response(204)
        self.end_headers()

    def _send_file(self, name: str, ctype: str):
        try:
            data = (ROOT / name).read_bytes()
        except FileNotFoundError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ReusableServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with ReusableServer(("127.0.0.1", PORT), Handler) as s:
        print(f"Dashboard: http://127.0.0.1:{PORT}/")
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            print("stopping…")
