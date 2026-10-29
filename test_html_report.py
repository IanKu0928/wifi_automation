import json
import tempfile
from pathlib import Path

from library.html_report import generate_html_report


def make_data(status):
    if status == "PASS":
        passed = 1
        failed = 0
        error = None
    elif status == "FAIL":
        passed = 0
        failed = 1
        error = None
    else:
        passed = 0
        failed = 0
        error = "Mock DUT connection failure"

    testcases = []

    if status != "ERROR":
        testcases.append({
            "test_id": "TC01",
            "name": "STA to DUT Connectivity",
            "status": status,
            "message": "Mock test result",
            "metrics": {
                "packet_loss_percent": 0 if passed else 100,
                "execution_duration_sec": 1.25
            }
        })

    return {
        "run_id": f"W8_HTML_{status}",
        "overall_status": status,
        "error": error,
        "metadata": {
            "profile": "smoke",
            "dut": {
                "ip": "192.168.1.1",
                "version": "Mock Firmware"
            },
            "wifi": {
                "ssid": "Mock WiFi",
                "bssid": "00:11:22:33:44:55",
                "frequency_ghz": 5.18
            }
        },
        "timing": {
            "start_time": "2026-10-29T16:00:00+08:00",
            "end_time": "2026-10-29T16:00:02+08:00",
            "duration_sec": 2.0
        },
        "summary": {
            "total": len(testcases),
            "pass": passed,
            "fail": failed
        },
        "testcases": testcases
    }


with tempfile.TemporaryDirectory() as temp_dir:

    for status in ["PASS", "FAIL", "ERROR"]:

        json_path = Path(temp_dir) / f"{status}.json"
        html_path = Path(temp_dir) / f"{status}.html"

        json_path.write_text(
            json.dumps(make_data(status), indent=4),
            encoding="utf-8"
        )

        generate_html_report(json_path, html_path)

        html = html_path.read_text(encoding="utf-8")

        assert f"W8_HTML_{status}" in html
        assert f'class="status {status.lower()}">{status}</span>' in html
        assert "Mock Firmware" in html

        if status == "ERROR":
            assert "Mock DUT connection failure" in html
            assert "No test cases were executed" in html
        else:
            assert "TC01" in html

        print(f"[PASS] {status} HTML report verified")

print("[PASS] All HTML report status tests")
