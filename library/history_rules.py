
import math


class HistoricalRules:

    def __init__(self):
        self.throughput_change_ratio = 0.20
        self.rssi_degradation_db = 5.0
        self.latency_regression_ratio = 2.0
        self.latency_increase_ms = 10.0
        self.instability_ratio = 0.30

    @staticmethod
    def valid(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    def analyze(self, comparison):
        findings = []

        def add(rule_id, severity, test_ids, title,
                evidence, causes, recommendations):
            findings.append({
                "rule_id": rule_id,
                "severity": severity,
                "test_ids": test_ids,
                "title": title,
                "evidence": evidence,
                "possible_causes": causes,
                "recommendations": recommendations
            })

        metrics = comparison.get("metrics") or {}

        if comparison.get("status") != "READY":
            add(
                "INSUFFICIENT_HISTORY", "INFO", [],
                "Insufficient comparable historical data.",
                f"Historical runs = "
                f"{comparison.get('historical_run_count', 0)}; "
                f"minimum = {comparison.get('minimum_samples', 3)}; "
                f"reason = {comparison.get('reason', 'Unknown')}",
                ["Not enough prior tests under matching conditions."],
                [
                    "Collect more runs using the same test profile.",
                    "Keep DUT firmware and WiFi settings consistent.",
                    "Recalculate historical baselines after collecting data."
                ]
            )

        for metric_key, item in metrics.items():
            if not item.get("baseline_ready"):
                continue

            current = item.get("current")
            baseline = item.get("historical_median")
            minimum = item.get("historical_min")
            maximum = item.get("historical_max")

            if not (
                self.valid(current)
                and self.valid(baseline)
            ):
                continue

            test_id = metric_key.split(".", 1)[0]

            # Throughput regression / improvement
            if metric_key in (
                "TC05.receiver_mbps",
                "TC06.receiver_mbps"
            ) and baseline > 0:

                change = (current - baseline) / baseline * 100

                if change <= -self.throughput_change_ratio * 100:
                    add(
                        "THROUGHPUT_DEGRADATION",
                        "WARNING", [test_id],
                        "TCP throughput decreased compared with historical baseline.",
                        f"Current = {current:.2f} Mbps; "
                        f"baseline = {baseline:.2f} Mbps; "
                        f"change = {change:.1f}%",
                        [
                            "Possible RF or network condition changes",
                            "Increased retransmissions or congestion",
                            "Device processing or driver differences"
                        ],
                        [
                            "Repeat the throughput test.",
                            "Compare RSSI and TCP retransmission metrics.",
                            "Verify test conditions remain consistent."
                        ]
                    )

                elif change >= self.throughput_change_ratio * 100:
                    add(
                        "THROUGHPUT_IMPROVEMENT",
                        "INFO", [test_id],
                        "TCP throughput improved compared with historical baseline.",
                        f"Current = {current:.2f} Mbps; "
                        f"baseline = {baseline:.2f} Mbps; "
                        f"change = +{change:.1f}%",
                        [
                            "Potential improvement in network conditions",
                            "Reduced contention or device load"
                        ],
                        [
                            "Repeat testing to confirm the improvement.",
                            "Check whether the test environment changed."
                        ]
                    )

                if (
                    self.valid(minimum)
                    and self.valid(maximum)
                    and (maximum - minimum) / baseline
                    >= self.instability_ratio
                ):
                    add(
                        "PERFORMANCE_INSTABILITY",
                        "WARNING", [test_id],
                        "Historical TCP throughput shows substantial variation.",
                        f"Historical min = {minimum:.2f} Mbps; "
                        f"max = {maximum:.2f} Mbps; "
                        f"median = {baseline:.2f} Mbps",
                        [
                            "Historical test conditions may vary",
                            "Possible intermittent performance variation"
                        ],
                        [
                            "Collect more runs under controlled conditions.",
                            "Compare wireless and system statistics.",
                            "Review outliers before relying on this baseline."
                        ]
                    )

            # RSSI degradation
            if metric_key == "TC04.signal_dbm":
                drop_db = baseline - current

                if drop_db >= self.rssi_degradation_db:
                    add(
                        "RSSI_DEGRADATION",
                        "WARNING", [test_id],
                        "WiFi signal strength decreased compared with historical baseline.",
                        f"Current = {current:.1f} dBm; "
                        f"baseline = {baseline:.1f} dBm; "
                        f"drop = {drop_db:.1f} dB",
                        [
                            "Antenna or RF environment changes",
                            "Different device placement",
                            "Possible signal attenuation"
                        ],
                        [
                            "Check DUT and STA antenna connections.",
                            "Verify test distance and positioning.",
                            "Repeat RSSI measurements under consistent conditions."
                        ]
                    )

            # Latency regression
            if metric_key == "TC01.avg_latency_ms":
                increase = current - baseline

                if (
                    baseline > 0
                    and current >= baseline * self.latency_regression_ratio
                    and increase >= self.latency_increase_ms
                ):
                    add(
                        "LATENCY_REGRESSION",
                        "WARNING", [test_id],
                        "Average network latency increased compared with historical baseline.",
                        f"Current = {current:.3f} ms; "
                        f"baseline = {baseline:.3f} ms; "
                        f"increase = {increase:.3f} ms",
                        [
                            "Possible network congestion or buffering",
                            "Wireless contention",
                            "DUT or STA processing delays"
                        ],
                        [
                            "Repeat ping tests with additional samples.",
                            "Check CPU load and background traffic.",
                            "Correlate with RSSI and retransmissions."
                        ]
                    )

        return {
            "run_id": comparison.get("run_id"),
            "comparison_status": comparison.get("status"),
            "analysis_version": "W9-04-3-v1",
            "findings_count": len(findings),
            "findings": findings
        }

