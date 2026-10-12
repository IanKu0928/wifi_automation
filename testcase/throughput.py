from testcase.base_test import TestResult
from library.iperf_parser import parse_iperf3_json


class ThroughputTest:

    def __init__(
        self,
        sta,
        server_ip,
        test_id="TC05",
        name="WiFi TCP Throughput Validation",
        duration=10,
        min_throughput_mbps=30.0,
        reverse=False
    ):
        self.sta = sta
        self.server_ip = server_ip
        self.test_id = test_id
        self.name = name
        self.duration = duration
        self.min_throughput_mbps = (
            min_throughput_mbps
        )
        self.reverse = reverse

    def run(self):

        print(
            f"[TEST] {self.test_id} - "
            f"{self.name}"
        )

        result = self.sta.run_iperf3(
            server_ip=self.server_ip,
            duration=self.duration,
            reverse=self.reverse
        )

        metrics = parse_iperf3_json(
            result["stdout"]
        )

        receiver_mbps = metrics[
            "receiver_mbps"
        ]

        if receiver_mbps is None:

            return TestResult(
                test_id=self.test_id,
                name=self.name,
                passed=False,
                message="Failed to parse iperf3 result",
                metrics=metrics
            )

        passed = (
            receiver_mbps
            >= self.min_throughput_mbps
        )

        if passed:

            message = (
                f"Throughput "
                f"{receiver_mbps:.1f} Mbps "
                f">= "
                f"{self.min_throughput_mbps:.1f} Mbps"
            )

        else:

            message = (
                f"Throughput "
                f"{receiver_mbps:.1f} Mbps "
                f"< "
                f"{self.min_throughput_mbps:.1f} Mbps"
            )

        metrics[
            "min_throughput_mbps"
        ] = self.min_throughput_mbps

        return TestResult(
            test_id=self.test_id,
            name=self.name,
            passed=passed,
            message=message,
            metrics=metrics
        )
