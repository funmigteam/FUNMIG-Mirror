import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from budget_download import BudgetReached, Downloader, Meter, RegistryBudgetReached


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = {"interface": None, "payload_limit_bytes": 100_000_000,
                       "minimum_free_bytes": 0, "budgets_bytes": {"test": 100_000_000}}
        self.meter = Meter(self.config, self.root / "state")
        self.data = b"test-resumable-content" * 150000
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                range_header = self.headers.get("Range")
                outer.requests.append(range_header)
                offset = int(range_header.split("=")[1].split("-")[0]) if range_header else 0
                ignore_range = self.path == "/ignore"
                if ignore_range:
                    offset = 0
                self.send_response(206 if offset else 200)
                self.send_header("Content-Length", str(len(outer.data) - offset))
                self.send_header("ETag", '"v1"')
                if offset:
                    self.send_header("Content-Range", f"bytes {offset}-{len(outer.data)-1}/{len(outer.data)}")
                self.end_headers()
                if self.path == "/drop" and len(outer.requests) == 1:
                    self.wfile.write(outer.data[:1200000])
                    self.wfile.flush()
                    self.close_connection = True
                else:
                    self.wfile.write(outer.data[offset:])

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.meter.db.close()
        self.temp.cleanup()

    def fetch(self, path):
        target = self.root / "artifact"
        Downloader(self.meter, sleeper=lambda _: None).fetch(
            f"http://127.0.0.1:{self.server.server_port}/{path}", target, "test",
            hashlib.sha256(self.data).hexdigest(), size=len(self.data))
        self.assertEqual(target.read_bytes(), self.data)

    def test_disconnect_resumes_and_charges_retries(self):
        self.fetch("drop")
        self.assertGreaterEqual(len(self.requests), 2)
        self.assertEqual(self.requests[1], "bytes=1200000-")
        self.assertGreater(self.meter.get("payload_bytes"), len(self.data))

    def test_ignored_range_restarts_without_appending(self):
        (self.root / "artifact.part").write_bytes(self.data[:100])
        self.fetch("ignore")
        self.assertEqual(self.requests, ["bytes=100-"])

    def test_existing_verified_file_needs_no_network(self):
        (self.root / "artifact").write_bytes(self.data)
        self.fetch("ok")
        self.assertEqual(self.requests, [])
        self.assertEqual(self.meter.get("payload_bytes"), 0)

    def test_allowance_persists_across_restart(self):
        self.meter.reserve(1234, "test")
        second = Meter(self.config, self.root / "state")
        self.assertEqual(second.get("payload_bytes"), 1234)
        second.db.close()

    def test_campaign_ceiling_stops_before_request(self):
        self.config["payload_limit_bytes"] = 100
        with self.assertRaises(BudgetReached):
            self.fetch("ok")
        self.assertEqual(self.requests, [])

    def test_registry_ceiling_keeps_partial_file(self):
        self.config["budgets_bytes"]["test"] = 1_200_000
        with self.assertRaises(RegistryBudgetReached):
            self.fetch("ok")
        self.assertFalse((self.root / "artifact").exists())
        self.assertTrue((self.root / "artifact.part").exists())
        self.assertLessEqual(self.meter.get("test"), 1_200_000)


if __name__ == "__main__":
    unittest.main()
