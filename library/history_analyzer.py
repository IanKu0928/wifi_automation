
import json
import math
from pathlib import Path
from statistics import median


class HistoryAnalyzer:

    COMPARE_FIELDS = (
        ("profile",),
        ("dut", "ip"),
        ("dut", "version"),
        ("wifi", "interface"),
        ("wifi", "ssid"),
        ("wifi", "bssid"),
        ("wifi", "frequency_ghz"),
    )

    METRICS = {
        "TC01": ["avg_latency_ms"],
        "TC04": ["signal_dbm"],
        "TC05": ["receiver_mbps"],
        "TC06": ["receiver_mbps"],
    }

    EXPECTED_IDS = {
        "TC01", "TC02", "TC03",
        "TC04", "TC05", "TC06"
    }

    def __init__(self, log_dir="logs", min_samples=3):
        self.log_dir = Path(log_dir)
        self.min_samples = min_samples

    @staticmethod
    def valid_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    @staticmethod
    def get_field(data, path):
        value = data

        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)

        return value

    def comparison_key(self, data):
        metadata = data.get("metadata") or {}

        values = tuple(
            self.get_field(metadata, path)
            for path in self.COMPARE_FIELDS
        )

        if any(
            value is None or value == ""
            for value in values
        ):
            return None

        return values

    def is_eligible(self, data):
        if data.get("overall_status") != "PASS":
            return False

        testcases = data.get("testcases") or []

        if len(testcases) != 6:
            return False

        ids = [
            tc.get("test_id")
            for tc in testcases
            if tc.get("status") == "PASS"
        ]

        return (
            len(ids) == len(self.EXPECTED_IDS)
            and set(ids) == self.EXPECTED_IDS
            and self.comparison_key(data) is not None
        )

    def load_groups(self):
        groups = {}

        for path in sorted(
            self.log_dir.glob("*/result.json")
        ):
            try:
                data = json.loads(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                continue

            if not self.is_eligible(data):
                continue

            key = self.comparison_key(data)

            # Store source path for later traceability.
            groups.setdefault(key, []).append({
                "path": str(path),
                "data": data
            })

        return groups

    def build_baselines(self):
        groups = self.load_groups()
        output = []

        for key, runs in groups.items():
            profile, dut_ip, firmware, interface, ssid, bssid, frequency = key

            baseline = {
                "profile": profile,
                "dut_ip": dut_ip,
                "firmware": firmware,
                "interface": interface,
                "ssid": ssid,
                "bssid": bssid,
                "frequency_ghz": frequency,
                "run_count": len(runs),
                "baseline_ready": (
                    len(runs) >= self.min_samples
                ),
                "metrics": {},
                "source_runs": [
                    item["data"].get("run_id")
                    for item in runs
                ]
            }

            for test_id, metric_names in self.METRICS.items():
                for metric_name in metric_names:

                    values = []

                    for item in runs:
                        testcases = {
                            tc.get("test_id"): tc
                            for tc in item["data"]["testcases"]
                        }

                        tc = testcases.get(test_id) or {}
                        value = (
                            tc.get("metrics") or {}
                        ).get(metric_name)

                        if self.valid_number(value):
                            values.append(value)

                    metric_key = (
                        f"{test_id}.{metric_name}"
                    )

                    baseline["metrics"][metric_key] = {
                        "samples": len(values),
                        "ready": (
                            len(values) >= self.min_samples
                        ),
                        "median": (
                            round(median(values), 3)
                            if values else None
                        ),
                        "minimum": (
                            round(min(values), 3)
                            if values else None
                        ),
                        "maximum": (
                            round(max(values), 3)
                            if values else None
                        )
                    }

            output.append(baseline)

        return output

