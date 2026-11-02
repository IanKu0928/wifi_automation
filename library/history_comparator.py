
import json
from datetime import datetime
from pathlib import Path
from statistics import median

from library.history_analyzer import HistoryAnalyzer


class HistoryComparator:

    def __init__(self, log_dir="logs", min_samples=3):
        self.analyzer = HistoryAnalyzer(
            log_dir=log_dir,
            min_samples=min_samples
        )
        self.min_samples = min_samples

    @staticmethod
    def run_time(path):
        # Only accept the framework's timestamp-based run directory.
        try:
            return datetime.strptime(
                Path(path).parent.name,
                "%Y%m%d_%H%M%S"
            )
        except ValueError:
            return None

    def compare(self, current_path):
        current_path = Path(current_path).resolve()

        current = json.loads(
            current_path.read_text(encoding="utf-8")
        )

        result = {
            "run_id": current.get("run_id"),
            "status": "INSUFFICIENT_HISTORY",
            "historical_run_count": 0,
            "minimum_samples": self.min_samples,
            "metrics": {},
            "source_runs": []
        }

        current_time = self.run_time(current_path)
        current_key = self.analyzer.comparison_key(current)

        if current_time is None or current_key is None:
            result["reason"] = (
                "Current run has incomplete comparison "
                "metadata or an invalid timestamp."
            )
            return result

        if not self.analyzer.is_eligible(current):
            result["reason"] = (
                "Current run is not a complete PASS run."
            )
            return result

        groups = self.analyzer.load_groups()
        candidates = groups.get(current_key, [])

        historical = []

        for item in candidates:
            path = Path(item["path"]).resolve()
            timestamp = self.run_time(path)

            # Prevent self-comparison and future-data leakage.
            if path == current_path:
                continue

            if timestamp is None or timestamp >= current_time:
                continue

            historical.append(item)

        historical.sort(
            key=lambda item: self.run_time(item["path"])
        )

        result["historical_run_count"] = len(historical)
        result["source_runs"] = [
            item["data"].get("run_id")
            for item in historical
        ]

        for test_id, metric_names in self.analyzer.METRICS.items():
            for metric_name in metric_names:
                metric_key = f"{test_id}.{metric_name}"

                current_cases = {
                    tc.get("test_id"): tc
                    for tc in current["testcases"]
                }

                current_value = (
                    (current_cases.get(test_id) or {})
                    .get("metrics") or {}
                ).get(metric_name)

                values = []

                for item in historical:
                    cases = {
                        tc.get("test_id"): tc
                        for tc in item["data"]["testcases"]
                    }

                    value = (
                        (cases.get(test_id) or {})
                        .get("metrics") or {}
                    ).get(metric_name)

                    if self.analyzer.valid_number(value):
                        values.append(value)

                current_valid = self.analyzer.valid_number(
                    current_value
                )

                ready = (
                    len(values) >= self.min_samples
                    and current_valid
                )

                result["metrics"][metric_key] = {
                    "current": (
                        current_value if current_valid else None
                    ),
                    "historical_samples": len(values),
                    "baseline_ready": ready,
                    "historical_median": (
                        round(median(values), 3)
                        if values else None
                    ),
                    "historical_min": (
                        round(min(values), 3)
                        if values else None
                    ),
                    "historical_max": (
                        round(max(values), 3)
                        if values else None
                    )
                }

        if (
            len(historical) >= self.min_samples
            and result["metrics"]
            and all(
                item["baseline_ready"]
                for item in result["metrics"].values()
            )
        ):
            result["status"] = "READY"
            result["reason"] = (
                "Comparable prior runs are available."
            )
        else:
            result["reason"] = (
                "Not enough comparable prior runs "
                "or valid metric samples."
            )

        return result

