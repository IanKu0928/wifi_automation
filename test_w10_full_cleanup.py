
import json
import tempfile
from types import SimpleNamespace
from library.logger import TestLogger
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import run_test


RADIO = {
    "interface": "wlan0",
    "ssid": "MOCK_SSID",
    "bssid": "00:11:22:33:44:55",
    "frequency_ghz": 5.18
}


def run_case(name, interrupt_target, cleanup_fail=False):
    print("\n" + "=" * 55)
    print("CASE:", name)

    with tempfile.TemporaryDirectory(prefix="w10_cleanup_") as temp, ExitStack() as stack:
        stack.enter_context(patch.object(run_test, "TestLogger", side_effect=lambda: TestLogger(temp)))
        real_analysis = run_test.generate_analysis_json
        stack.enter_context(patch.object(run_test, "generate_analysis_json", side_effect=lambda result_path, **kw: real_analysis(result_path=result_path, log_dir=temp, min_samples=3)))
        def mock_method(cls, name, **kwargs):
            return stack.enter_context(
                patch.object(cls, name, **kwargs)
            )

        # All DUT operations are mocked.
        dut_connect = mock_method(run_test.DUT, "connect", side_effect=KeyboardInterrupt() if interrupt_target == "dut_connect" else None)
        mock_method(
            run_test.DUT,
            "get_version",
            side_effect=KeyboardInterrupt() if interrupt_target == "version" else None,
            return_value="MOCK_FW_1.0"
        )
        mock_method(
            run_test.DUT,
            "get_radio_info",
            return_value=RADIO
        )
        mock_method(
            run_test.DUT,
            "prepare_test_firewall",
            return_value=None
        )

        # All Golden STA operations are mocked.
        sta_connect = mock_method(
            run_test.GoldenSTA, "connect", return_value=None
        )
        mock_method(
            run_test.GoldenSTA,
            "set_wifi_bssid",
            **(
                {"side_effect": KeyboardInterrupt()}
                if interrupt_target == "sta_bssid"
                else {"return_value": {"exit_code": 0, "stderr": ""}}
            )
        )
        mock_method(
            run_test.GoldenSTA,
            "get_configured_bssid",
            return_value={"stdout": RADIO["bssid"]}
        )
        mock_method(
            run_test.GoldenSTA,
            "prepare_wifi",
            return_value="192.168.1.100"
        )
        mock_method(
            run_test.GoldenSTA,
            "verify_wifi_connection",
            return_value=True
        )
        mock_method(
            run_test.GoldenSTA,
            "get_route",
            return_value={
                "stdout": "dev " + run_test.STA_WIFI_INTERFACE
            }
        )
        mock_method(
            run_test.GoldenSTA,
            "ping",
            return_value={"exit_code": 0}
        )

        iperf_start = mock_method(
            run_test.IperfServer, "start", return_value=None
        )

        calls = []
        real_run_test = run_test.TestRunner.run_test

        def run_mock(runner, test):
            calls.append(test)
            completed = SimpleNamespace(
                test_id="TC01", name="Mock completed", status="PASS",
                passed=True, message="completed", metrics={}
            )
            behavior = (
                {"side_effect": KeyboardInterrupt()}
                if len(calls) == 2 else {"return_value": completed}
            )
            # Exercise the real runner while preventing actual testcase I/O.
            with patch.object(test, "run", **behavior):
                return real_run_test(runner, test)

        runner_test = mock_method(
            run_test.TestRunner,
            "run_test",
            autospec=True, side_effect=run_mock
        )

        # Mock all resource cleanup operations.
        def failure(resource):
            if cleanup_fail is True or cleanup_fail == resource:
                return {"side_effect": RuntimeError("Mock cleanup failure")}
            return {"return_value": None}

        iperf_stop = mock_method(
            run_test.IperfServer, "stop", **failure("iperf3")
        )
        sta_close = mock_method(
            run_test.GoldenSTA, "close", **failure("STA")
        )
        dut_close = mock_method(
            run_test.DUT, "close", **failure("DUT")
        )

        # Capture generated result.json path.
        real_writer = run_test.write_result_json
        writer = stack.enter_context(
            patch.object(
                run_test,
                "write_result_json",
                wraps=real_writer
            )
        )

        stack.enter_context(
            patch(
                "sys.argv",
                ["run_test.py", "--profile", "smoke"]
            )
        )

        run_test.main()

        # Verify execution reached the intended stage.
        dut_connect.assert_called_once()
        if interrupt_target in ("dut_connect", "version"):
            sta_connect.assert_not_called()
        else:
            sta_connect.assert_called_once()

        if interrupt_target != "testcase":
            iperf_start.assert_not_called()
            runner_test.assert_not_called()
        else:
            iperf_start.assert_called_once()
            assert runner_test.call_count == 2

        # All applicable cleanup methods must be called.
        iperf_stop.assert_called_once()
        if interrupt_target in ("dut_connect", "version"):
            sta_close.assert_not_called()
        else:
            sta_close.assert_called_once()
        dut_close.assert_called_once()

        writer.assert_called_once()
        result_path = Path(
            writer.call_args.kwargs["file_path"]
        )

        # Verify actual reports generated by the framework.
        run_dir = result_path.parent

        result = json.loads(
            result_path.read_text(encoding="utf-8")
        )

        analysis = json.loads(
            (run_dir / "analysis.json").read_text(encoding="utf-8")
        )

        assert (run_dir / "report.html").exists()
        assert result["overall_status"] == "ERROR"
        assert "KeyboardInterrupt" in result["error"]
        assert analysis["test_status"] == "ERROR"

        for resource in ("iperf3", "STA", "DUT"):
            expected = cleanup_fail is True or cleanup_fail == resource
            assert (resource + " cleanup:" in result["error"]) == expected
        assert result["summary"]["total"] == (1 if interrupt_target == "testcase" else 0)
        if interrupt_target == "testcase":
            assert result["testcases"][0]["message"] == "completed"

        print("[PASS] Interrupt detected")
        print("[PASS] Resource cleanup methods invoked")
        print("[PASS] Original interrupt reason preserved")
        print("[PASS] Cleanup errors handled as expected")
        print("[PASS] JSON and HTML reports generated")
        print("[PASS] All DUT / STA operations mocked")
        print("Run ID:", result["run_id"])


if __name__ == "__main__":
    for target in ("dut_connect", "version", "sta_bssid", "testcase"):
        run_case(target, target)
    for failure in ("iperf3", "STA", "DUT", True):
        run_case(f"testcase cleanup={failure}", "testcase", failure)
    print("[PASS] W10 Full Cleanup Regression (8 scenarios)")
