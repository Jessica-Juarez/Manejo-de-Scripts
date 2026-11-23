import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit


BASE_DIR = Path(__file__).resolve().parent
PUBLIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}
MAX_BODY_BYTES = 16_384
MAX_TITLE_LENGTH = 120


class TaskServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.tasks = []
        self.next_task_id = 1
        self.data_lock = Lock()
        self.started_at = time.monotonic()
        self.requests_total = 0
        self.requests_by_route = {}
        self.responses_by_status = {}
        self.response_time_total_ms = 0.0
        self.completed_requests = 0

    def start_request(self, route):
        with self.data_lock:
            self.requests_total += 1
            self.requests_by_route[route] = self.requests_by_route.get(route, 0) + 1

    def record_response(self, status, elapsed_ms):
        with self.data_lock:
            key = str(status)
            self.responses_by_status[key] = self.responses_by_status.get(key, 0) + 1
            self.response_time_total_ms += elapsed_ms
            self.completed_requests += 1


class TaskHandler(BaseHTTPRequestHandler):
    server: TaskServer
    protocol_version = "HTTP/1.0"

    def do_GET(self):
        self._dispatch(self._get)

    def do_POST(self):
        self._dispatch(self._post)

    def do_DELETE(self):
        self._dispatch(self._delete)

    def _dispatch(self, handler):
        path = urlsplit(self.path).path
        route = "/api/tasks/{id}" if re.fullmatch(r"/api/tasks/\d+", path) else path
        self._response_status = 500
        started = time.monotonic()
        self.server.start_request(route)
        try:
            handler(path)
        finally:
            elapsed_ms = (time.monotonic() - started) * 1000
            self.server.record_response(self._response_status, elapsed_ms)

    def _get(self, path):
        if path in PUBLIC_FILES:
            filename, content_type = PUBLIC_FILES[path]
            body = (BASE_DIR / "public" / filename).read_bytes()
            self._send(body, 200, content_type)
            return

        if path == "/healthz":
            self._send_json({"status": "ok"})
            return

        if path == "/metrics":
            with self.server.data_lock:
                metrics = {
                    "uptime_seconds": round(time.monotonic() - self.server.started_at, 2),
                    "requests_total": self.server.requests_total,
                    "requests_by_route": dict(self.server.requests_by_route),
                    "responses_by_status": dict(self.server.responses_by_status),
                    "average_response_time_ms": round(
                        self.server.response_time_total_ms / self.server.completed_requests, 2
                    )
                    if self.server.completed_requests
                    else 0,
                    "tasks_total": len(self.server.tasks),
                }
            self._send_json(metrics)
            return

        if path == "/api/tasks":
            with self.server.data_lock:
                tasks = [dict(task) for task in self.server.tasks]
            self._send_json({"tasks": tasks})
            return

        self._send_json({"error": "No encontrado"}, 404)

    def _post(self, path):
        if path != "/api/tasks":
            self._send_json({"error": "No encontrado"}, 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json({"error": "Content-Length inválido"}, 400)
            return

        if content_length < 0:
            self._send_json({"error": "Content-Length inválido"}, 400)
            return
        if content_length > MAX_BODY_BYTES:
            self._send_json({"error": "La solicitud es demasiado grande"}, 413)
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json({"error": "JSON inválido"}, 400)
            return

        title = payload.get("title") if isinstance(payload, dict) else None
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > MAX_TITLE_LENGTH:
            self._send_json({"error": "El título debe tener entre 1 y 120 caracteres"}, 400)
            return

        with self.server.data_lock:
            task = {"id": self.server.next_task_id, "title": title.strip()}
            self.server.next_task_id += 1
            self.server.tasks.append(task)
        self._send_json({"task": task}, 201)

    def _delete(self, path):
        match = re.fullmatch(r"/api/tasks/([1-9]\d*)", path)
        if not match:
            self._send_json({"error": "No encontrado"}, 404)
            return

        try:
            task_id = int(match.group(1))
        except ValueError:
            self._send_json({"error": "No encontrado"}, 404)
            return

        with self.server.data_lock:
            for index, task in enumerate(self.server.tasks):
                if task["id"] == task_id:
                    del self.server.tasks[index]
                    self._send(b"", 204, "application/json; charset=utf-8")
                    return

        self._send_json({"error": "Tarea no encontrada"}, 404)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(body, status, "application/json; charset=utf-8")

    def _send(self, body, status, content_type):
        self._response_status = status
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if body:
            self.wfile.write(body)


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT debe estar entre 1 y 65535")

    server = TaskServer((host, port), TaskHandler)
    print("Tareas claras disponible en http://%s:%s" % (host, port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando servidor...", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
