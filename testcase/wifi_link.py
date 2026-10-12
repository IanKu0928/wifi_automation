import re

from testcase.base_test import TestResult


class WiFiLinkTest:

    def __init__(
        self,
        sta,
        expected_ssid,
        expected_bssid,
        test_id="TC03",
        name="WiFi Target Radio Validation"
    ):
        self.sta = sta
        self.expected_ssid = expected_ssid
        self.expected_bssid = expected_bssid.lower()
        self.test_id = test_id
        self.name = name

    def run(self):

        print(
            f"[TEST] {self.test_id} - "
            f"{self.name}"
        )

        result = self.sta.get_wifi_status()
        output = result["stdout"]

        ssid_match = re.search(
            r"SSID:\s*(.+)",
            output
        )

        bssid_match = re.search(
            r"Connected to\s+([0-9A-Fa-f:]{17})",
            output
        )

        actual_ssid = (
            ssid_match.group(1).strip()
            if ssid_match else None
        )

        actual_bssid = (
            bssid_match.group(1).lower()
            if bssid_match else None
        )

        metrics = {
            "expected_ssid": self.expected_ssid,
            "actual_ssid": actual_ssid,
            "expected_bssid": self.expected_bssid,
            "actual_bssid": actual_bssid,
        }

        if actual_ssid is None or actual_bssid is None:
            return TestResult(
                test_id=self.test_id,
                name=self.name,
                passed=False,
                message="STA is not connected to WiFi",
                metrics=metrics
            )

        passed = (
            actual_ssid == self.expected_ssid
            and actual_bssid == self.expected_bssid
        )

        if passed:
            message = (
                "STA connected to expected "
                "SSID/BSSID"
            )
        else:
            message = (
                "STA connected to unexpected "
                "SSID/BSSID"
            )

        return TestResult(
            test_id=self.test_id,
            name=self.name,
            passed=passed,
            message=message,
            metrics=metrics
        )
