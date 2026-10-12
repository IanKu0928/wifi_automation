from testcase.base_test import TestResult
from library.ping_parser import parse_ping_output


class ConnectivityTest:

    def __init__(
        self,
        sta,
        destination,
        test_id,
        name,
        ping_count=10,
        max_packet_loss_percent=1.0
    ):
        self.sta = sta
        self.destination = destination
        self.test_id = test_id
        self.name = name
        self.ping_count = ping_count
        self.max_packet_loss_percent = (
            max_packet_loss_percent
        )

    def run(self):

        print(
            f"[TEST] {self.test_id} - "
            f"{self.name}"
        )

        result = self.sta.ping(
            self.destination,
            count=self.ping_count
        )

        metrics = parse_ping_output(
            result["stdout"]
        )

        packet_loss = metrics[
            "packet_loss_percent"
        ]

        if packet_loss is None:
            return TestResult(
                test_id=self.test_id,
                name=self.name,
                passed=False,
                message="Failed to parse ping result",
                metrics=metrics
            )

        passed = (
            packet_loss
            <= self.max_packet_loss_percent
        )

        if passed:
            message = (
                f"Packet loss {packet_loss}% "
                f"<= {self.max_packet_loss_percent}%"
            )
        else:
            message = (
                f"Packet loss {packet_loss}% "
                f"> {self.max_packet_loss_percent}%"
            )

        return TestResult(
            test_id=self.test_id,
            name=self.name,
            passed=passed,
            message=message,
            metrics=metrics
        )
