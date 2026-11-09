
import json
import tempfile
from contextlib import ExitStack
from library.logger import TestLogger
from pathlib import Path
from unittest.mock import patch

import run_test


def run_case(root):
    before = set(Path(root).glob("*/result.json"))

    # Simulate successful DUT connection,
    # followed by Ctrl+C during firmware retrieval.
    with patch.object(
        run_test.DUT,
        "connect",
        return_value=None
    ) as mock_connect, patch.object(
        run_test.DUT,
        "get_version",
        side_effect=KeyboardInterrupt()
    ) as mock_version, patch.object(
        run_test.DUT,
        "close",
        autospec=True
    ) as mock_dut_close, patch.object(
        run_test.IperfServer,
        "stop",
        autospec=True
    ) as mock_iperf_stop, patch(
        "sys.argv",
        ["run_test.py", "--profile", "smoke"]
    ):
        run_test.main()

    # Verify cleanup calls.
    mock_connect.assert_called_once()
    mock_version.assert_called_once()
    mock_dut_close.assert_called_once()
    mock_iperf_stop.assert_called_once()

    print("[PASS] DUT connection simulated")
    print("[PASS] Ctrl+C during firmware retrieval")
    print("[PASS] DUT close() called")
    print("[PASS] iperf3 stop() called")

    # Verify generated reports.
    after = set(Path(root).glob("*/result.json"))
    new_files = after - before

    assert len(new_files) == 1, (
        f"Expected one new result.json, got {len(new_files)}"
    )

    result_path = new_files.pop()
    run_dir = result_path.parent

    result = json.loads(
        result_path.read_text(encoding="utf-8")
    )

    analysis_path = run_dir / "analysis.json"
    html_path = run_dir / "report.html"

    assert result["overall_status"] == "ERROR"
    assert "KeyboardInterrupt" in result["error"]

    assert analysis_path.exists()
    assert html_path.exists()

    analysis = json.loads(
        analysis_path.read_text(encoding="utf-8")
    )

    assert analysis["test_status"] == "ERROR"

    print("[PASS] ERROR status preserved")
    print("[PASS] Interrupt reason preserved")
    print("[PASS] Analysis and HTML reports generated")
    print("[PASS] No real DUT connection attempted")
    print("Run ID:", result["run_id"])

    print()
    print("[PASS] W10-03-4 Interrupt Cleanup Regression")


def main():
    with tempfile.TemporaryDirectory(prefix="w10_interrupt_") as temp:
        with ExitStack() as stack:
            stack.enter_context(patch.object(run_test, "TestLogger", side_effect=lambda: TestLogger(temp)))
            stack.enter_context(patch.object(run_test, "generate_analysis_json", side_effect=lambda result_path, **kw: real_analysis(result_path=result_path, log_dir=temp, min_samples=3)))
            run_case(temp)


real_analysis = run_test.generate_analysis_json

if __name__ == "__main__":
    main()

