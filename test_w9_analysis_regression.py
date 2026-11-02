
import json
import tempfile
from pathlib import Path

from library.analysis_engine import AnalysisEngine
from library.history_comparator import HistoryComparator
from library.history_rules import HistoricalRules


engine = AnalysisEngine()
history_rules = HistoricalRules()


def tc(test_id, metrics, status="PASS"):
    return {
        "test_id": test_id,
        "name": test_id,
        "status": status,
        "message": "Regression test",
        "metrics": metrics
    }


def run_analysis(testcases, status="PASS", error=None):
    return engine.analyze({
        "run_id": "W9_REGRESSION",
        "overall_status": status,
        "error": error,
        "testcases": testcases
    })


def rule_ids(analysis):
    return {
        item["rule_id"]
        for item in analysis["findings"]
    }


def verify(name, condition):
    assert condition, f"[FAIL] {name}"
    print(f"[PASS] {name}")


# 01. Normal ping should not raise latency warnings.
result = run_analysis([
    tc("TC01", {
        "packet_loss_percent": 0,
        "max_latency_ms": 5,
        "mdev_latency_ms": 1
    })
])
verify(
    "Normal ping",
    not rule_ids(result) & {
        "PING_PACKET_LOSS",
        "PING_LATENCY_SPIKE",
        "PING_LATENCY_VARIATION"
    }
)


# 02. High latency spike.
result = run_analysis([
    tc("TC01", {
        "packet_loss_percent": 0,
        "max_latency_ms": 150,
        "mdev_latency_ms": 5
    })
])
verify(
    "High latency spike",
    "PING_LATENCY_SPIKE" in rule_ids(result)
)


# 03. Threshold boundary: exactly 100 ms
# should not trigger a rule using > 100.
result = run_analysis([
    tc("TC01", {
        "packet_loss_percent": 0,
        "max_latency_ms": 100,
        "mdev_latency_ms": 5
    })
])
verify(
    "Latency threshold boundary",
    "PING_LATENCY_SPIKE" not in rule_ids(result)
)


# 04. RSSI near threshold.
result = run_analysis([
    tc("TC04", {
        "signal_dbm": -67,
        "min_signal_dbm": -70
    })
])
verify(
    "RSSI near threshold",
    "RSSI_NEAR_THRESHOLD" in rule_ids(result)
)


# 05. Strong RSSI should not trigger RSSI warning.
result = run_analysis([
    tc("TC04", {
        "signal_dbm": -40,
        "min_signal_dbm": -70
    })
])
verify(
    "Normal RSSI",
    not rule_ids(result) & {
        "RSSI_NEAR_THRESHOLD",
        "RSSI_BELOW_THRESHOLD"
    }
)


# 06. Throughput below threshold.
result = run_analysis([
    tc("TC05", {
        "receiver_mbps": 15,
        "min_throughput_mbps": 30,
        "retransmits": 0
    }, status="FAIL")
], status="FAIL")
verify(
    "Throughput degradation against limit",
    "THROUGHPUT_BELOW_THRESHOLD" in rule_ids(result)
)


# 07. Unknown execution error.
result = run_analysis(
    [],
    status="ERROR",
    error="Unexpected internal exception"
)
verify(
    "Unknown error classification",
    "UNCLASSIFIED_EXECUTION_ERROR" in rule_ids(result)
)


# 08. Known execution error.
result = run_analysis(
    [],
    status="ERROR",
    error="DUT connection failed"
)
verify(
    "DUT error classification",
    "DUT_CONNECTION_ERROR" in rule_ids(result)
)


# 09. Strong RSSI with latency spike.
result = run_analysis([
    tc("TC01", {
        "packet_loss_percent": 0,
        "max_latency_ms": 200,
        "mdev_latency_ms": 10
    }),
    tc("TC04", {
        "signal_dbm": -40,
        "min_signal_dbm": -70
    })
])
verify(
    "Cross-test correlation positive",
    "STRONG_RSSI_HIGH_LATENCY" in rule_ids(result)
)


# 10. No false correlation under normal latency.
result = run_analysis([
    tc("TC01", {
        "packet_loss_percent": 0,
        "max_latency_ms": 5,
        "mdev_latency_ms": 1
    }),
    tc("TC04", {
        "signal_dbm": -40,
        "min_signal_dbm": -70
    })
])
verify(
    "Cross-test correlation negative",
    "STRONG_RSSI_HIGH_LATENCY" not in rule_ids(result)
)


# 11. Historical diagnostic rules.
comparison = {
    "run_id": "HISTORY_TEST",
    "status": "READY",
    "historical_run_count": 4,
    "minimum_samples": 3,
    "metrics": {
        "TC04.signal_dbm": {
            "current": -50,
            "historical_median": -44,
            "historical_min": -46,
            "historical_max": -43,
            "baseline_ready": True
        },
        "TC05.receiver_mbps": {
            "current": 60,
            "historical_median": 100,
            "historical_min": 95,
            "historical_max": 105,
            "baseline_ready": True
        }
    }
}

result = history_rules.analyze(comparison)
rules = rule_ids(result)

verify(
    "Historical diagnostic rules",
    {
        "RSSI_DEGRADATION",
        "THROUGHPUT_DEGRADATION"
    }.issubset(rules)
)


# 12. Historical comparator must exclude the current
# run and any future run, even if the conditions match.
with tempfile.TemporaryDirectory(prefix="w9_history_") as tmp:
    root = Path(tmp)

    metadata = {
        "profile": "smoke",
        "dut": {"ip": "192.168.1.1", "version": "TEST_FW"},
        "wifi": {
            "interface": "wlan0",
            "ssid": "TEST_SSID",
            "bssid": "00:11:22:33:44:55",
            "frequency_ghz": 5.18
        }
    }

    def make_run(run_id):
        folder = root / run_id
        folder.mkdir()

        cases = [
            tc("TC01", {"avg_latency_ms": 2}),
            tc("TC02", {"packet_loss_percent": 0}),
            tc("TC03", {}),
            tc("TC04", {"signal_dbm": -40}),
            tc("TC05", {"receiver_mbps": 100}),
            tc("TC06", {"receiver_mbps": 120})
        ]

        path = folder / "result.json"

        path.write_text(
            json.dumps({
                "run_id": run_id,
                "metadata": metadata,
                "overall_status": "PASS",
                "testcases": cases
            }),
            encoding="utf-8"
        )

        return path

    make_run("20261101_100000")
    make_run("20261101_110000")
    make_run("20261101_120000")

    current_path = make_run("20261102_100000")
    make_run("20261103_100000")

    comparator = HistoryComparator(
        log_dir=root,
        min_samples=3
    )

    result = comparator.compare(current_path)

    verify(
        "Historical self/future exclusion",
        result["status"] == "READY"
        and result["historical_run_count"] == 3
        and "20261102_100000" not in result["source_runs"]
        and "20261103_100000" not in result["source_runs"]
    )


print()
print("[PASS] W9-07-2 Analysis Regression")

