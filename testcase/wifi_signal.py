import re

from testcase.base_test import TestResult
from library.rule_engine import RuleEngine


class WiFiSignalTest:

    def __init__(
        self,
        sta,
        test_id="TC04",
        name="WiFi Signal Validation",
        min_signal_dbm=-70
    ):
        self.sta = sta
        self.test_id = test_id
        self.name = name
        self.min_signal_dbm = min_signal_dbm

    def run(self):

        print(
            f"[TEST] {self.test_id} - "
            f"{self.name}"
        )

        result = self.sta.get_wifi_status()
        output = result["stdout"]

        signal_match = re.search(
            r"signal:\s*(-?\d+)\s*dBm",
            output
        )

        if not signal_match:
            return TestResult(
                test_id=self.test_id,
                name=self.name,
                passed=False,
                message="Failed to read WiFi signal",
                metrics={
                    "signal_dbm": None,
                    "min_signal_dbm": self.min_signal_dbm
                }
            )

        signal_dbm = int(
            signal_match.group(1)
        )

        rule = RuleEngine.evaluate(
            value=signal_dbm,
            operator_symbol=">=",
            threshold=self.min_signal_dbm
        )

        passed = rule["passed"]

        metrics = {
            "signal_dbm": signal_dbm,
            "min_signal_dbm": self.min_signal_dbm
        }

        if passed:
            message = (
                f"Signal {signal_dbm} dBm "
                f">= {self.min_signal_dbm} dBm"
            )
        else:
            message = (
                f"Signal {signal_dbm} dBm "
                f"< {self.min_signal_dbm} dBm"
            )

        return TestResult(
            test_id=self.test_id,
            name=self.name,
            passed=passed,
            message=message,
            metrics=metrics
        )
