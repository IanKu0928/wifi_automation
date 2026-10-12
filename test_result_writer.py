from testcase.base_test import TestResult
from library.result_writer import write_result_json


results = [
    TestResult(
        test_id="TC01",
        name="STA to DUT Connectivity",
        passed=True,
        message="Packet loss 0.0% <= 1.0%",
        metrics={
            "packet_loss_percent": 0.0,
            "avg_latency_ms": 1.957,
            "max_latency_ms": 2.686,
        }
    ),

    TestResult(
        test_id="TC02",
        name="STA to Control Connectivity",
        passed=True,
        message="Packet loss 0.0% <= 1.0%",
        metrics={
            "packet_loss_percent": 0.0,
            "avg_latency_ms": 2.004,
            "max_latency_ms": 2.571,
        }
    ),
]


write_result_json(
    file_path="/tmp/result.json",
    run_id="TEST_RUN",
    results=results
)

print("Result JSON created:")
print("/tmp/result.json")
