"""Offline allocation and historical ordering regression; no hardware imports."""
import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from library.logger import TestLogger
from library.history_comparator import HistoryComparator

STAMP = "20261109_142504"


class RunHistoryTests(unittest.TestCase):
    def test_allocation(self):
        with tempfile.TemporaryDirectory() as temp, patch("library.logger.datetime") as clock:
            clock.now.return_value = datetime(2026, 11, 9, 14, 25, 4)
            first = TestLogger(temp)
            marker = Path(first.run_dir) / "marker"
            marker.write_text("preserve")
            self.assertEqual(first.run_id, STAMP)
            self.assertEqual(TestLogger(temp).run_id, STAMP + "_001")
            self.assertEqual(TestLogger(temp).run_id, STAMP + "_002")
            (Path(temp) / (STAMP + "_003")).write_text("existing file")
            with ThreadPoolExecutor(max_workers=12) as pool:
                ids = list(pool.map(lambda _: TestLogger(temp).run_id, range(40)))
            self.assertEqual(set(ids), {f"{STAMP}_{i:03d}" for i in range(4, 44)})
            self.assertEqual(marker.read_text(), "preserve")

    def test_creation_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            for error in (PermissionError("denied"), OSError("disk error")):
                with patch("library.logger.os.makedirs"), patch("library.logger.os.mkdir", side_effect=error) as mkdir:
                    with self.assertRaises(type(error)):
                        TestLogger(temp)
                    self.assertEqual(mkdir.call_count, 1)

    def test_parsing(self):
        for suffix, sequence in (("", 0), ("_001", 1), ("_002", 2), ("_1000", 1000)):
            path = Path(STAMP + suffix) / "result.json"
            self.assertEqual(HistoryComparator.run_order_key(path), (datetime(2026, 11, 9, 14, 25, 4), sequence))
            self.assertEqual(HistoryComparator.run_time(path), datetime(2026, 11, 9, 14, 25, 4))
        for name in (STAMP + "_000", STAMP + "_01", STAMP + "_0001", STAMP + "_001_extra", "20260230_142504", "2026119_142504", STAMP + "\n"):
            self.assertIsNone(HistoryComparator.run_order_key(Path(name) / "result.json"))
            self.assertIsNone(HistoryComparator.run_time(Path(name) / "result.json"))

    def test_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            metadata = {"profile": "smoke", "dut": {"ip": "192.0.2.1", "version": "MOCK"}, "wifi": {"interface": "wlan0", "ssid": "MOCK", "bssid": "00:11:22:33:44:55", "frequency_ghz": 5.18}}
            def make(name, value=100, status="PASS", incomplete=False, other=False):
                folder = root / name
                folder.mkdir()
                data = {"run_id": name, "metadata": copy.deepcopy(metadata), "overall_status": status, "testcases": [{"test_id": f"TC{i:02d}", "status": "PASS", "metrics": {"avg_latency_ms": value, "signal_dbm": -40, "receiver_mbps": value}} for i in range(1, 7)]}
                if incomplete:
                    data["testcases"].pop()
                if other:
                    data["metadata"]["profile"] = "performance"
                path = folder / "result.json"
                path.write_text(json.dumps(data))
                return path
            prior = ["20261109_142503", STAMP, STAMP + "_001"]
            for name, value in zip(prior, (10, 90, 20)):
                make(name, value)
            current = make(STAMP + "_002")
            make(STAMP + "_003", 9000)
            make("20261109_142505", 9000)
            make("20261108_142504", status="FAIL")
            make("20261108_142505", status="ERROR")
            make("20261108_142506", incomplete=True)
            make("20261108_142507", other=True)
            make("bad_run", 9000)
            comparison = HistoryComparator(root).compare(current)
            self.assertEqual(comparison["source_runs"], prior)
            self.assertEqual(comparison["historical_run_count"], 3)
            self.assertEqual(comparison["status"], "READY")
            metric = comparison["metrics"]["TC05.receiver_mbps"]
            self.assertEqual(metric["historical_samples"], 3)
            self.assertEqual(metric["historical_median"], 20)
            early = HistoryComparator(root).compare(root / STAMP / "result.json")
            self.assertEqual(early["historical_run_count"], 1)
            self.assertEqual(early["status"], "INSUFFICIENT_HISTORY")
            self.assertFalse(early["metrics"]["TC05.receiver_mbps"]["baseline_ready"])


if __name__ == "__main__":
    unittest.main()
