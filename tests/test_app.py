import json
import threading
import unittest
from http.client import HTTPConnection

from app import TaskHandler, TaskServer


class TaskAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = TaskServer(("127.0.0.1", 0), TaskHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        with self.server.data_lock:
            self.server.tasks.clear()
            self.server.next_task_id = 1

    def request(self, method, path, payload=None):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=2)
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        result = response.read()
        status = response.status
        connection.close()
        return status, result

    def test_health_and_web_page_are_available(self):
        status, body = self.request("GET", "/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})

        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Tareas claras", body)

    def test_create_list_and_delete_task(self):
        status, body = self.request("POST", "/api/tasks", {"title": "  Entregar proyecto  "})
        self.assertEqual(status, 201)
        task = json.loads(body)["task"]
        self.assertEqual(task["title"], "Entregar proyecto")

        status, body = self.request("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["tasks"], [task])

        status, _ = self.request("DELETE", "/api/tasks/%s" % task["id"])
        self.assertEqual(status, 204)
        status, body = self.request("GET", "/api/tasks")
        self.assertEqual(json.loads(body)["tasks"], [])

    def test_invalid_task_is_rejected(self):
        for payload in ({}, {"title": "   "}, {"title": "x" * 121}):
            with self.subTest(payload=payload):
                status, _ = self.request("POST", "/api/tasks", payload)
                self.assertEqual(status, 400)

    def test_metrics_include_request_counts_and_latency(self):
        self.request("GET", "/healthz")
        status, body = self.request("GET", "/metrics")
        metrics = json.loads(body)

        self.assertEqual(status, 200)
        self.assertGreaterEqual(metrics["requests_total"], 2)
        self.assertGreaterEqual(metrics["requests_by_route"]["/healthz"], 1)
        self.assertIn("200", metrics["responses_by_status"])
        self.assertGreaterEqual(metrics["average_response_time_ms"], 0)
        self.assertEqual(metrics["tasks_total"], 0)


if __name__ == "__main__":
    unittest.main()
