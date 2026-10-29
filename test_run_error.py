import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import run_test


def main():

    with tempfile.TemporaryDirectory() as temp_dir:

        with patch(
            "run_test.TestLogger"
        ) as MockLogger, patch(
            "run_test.DUT"
        ) as MockDUT, patch(
            "run_test.IperfServer"
        ) as MockIperfServer, patch(
            "run_test.parse_args"
        ) as MockArgs:

            MockArgs.return_value.profile = "smoke"

            logger = MockLogger.return_value
            logger.run_id = "W8_ERROR_TEST"
            logger.run_dir = temp_dir

            dut = MockDUT.return_value
            dut.connect.side_effect = RuntimeError(
                "Mock DUT connection failure"
            )

            run_test.main()

            result_file = Path(temp_dir) / "result.json"

            assert result_file.exists(), (
                "result.json was not generated"
            )

            with result_file.open(encoding="utf-8") as f:
                data = json.load(f)

            assert data["overall_status"] == "ERROR"
            assert data["summary"]["total"] == 0
            assert "Mock DUT connection failure" in data["error"]

            MockIperfServer.return_value.stop.assert_called_once()
            dut.close.assert_called_once()

            print("[PASS] DUT connection error detected")
            print("[PASS] ERROR result.json generated")
            print("[PASS] Cleanup executed")


def test_cleanup_error():

    import tempfile
    import json
    from pathlib import Path
    from unittest.mock import patch, MagicMock

    with tempfile.TemporaryDirectory() as temp_dir:

        with patch("run_test.TestLogger") as MockLogger, \
             patch("run_test.DUT") as MockDUT, \
             patch("run_test.IperfServer") as MockIperfServer, \
             patch("run_test.parse_args") as MockArgs:

            MockArgs.return_value.profile = "smoke"

            logger = MockLogger.return_value
            logger.run_id = "W8_CLEANUP_TEST"
            logger.run_dir = temp_dir

            dut = MockDUT.return_value

            # Cause an execution error before TestRunner is created.
            dut.connect.side_effect = RuntimeError(
                "Mock connection failure"
            )

            # Simulate cleanup exceptions.
            dut.close.side_effect = RuntimeError(
                "Mock DUT cleanup failure"
            )

            MockIperfServer.return_value.stop.side_effect = RuntimeError(
                "Mock iperf3 cleanup failure"
            )

            run_test.main()

            result_file = Path(temp_dir) / "result.json"

            assert result_file.exists()

            data = json.loads(
                result_file.read_text(encoding="utf-8")
            )

            assert data["overall_status"] == "ERROR"
            assert "Mock connection failure" in data["error"]
            assert "Mock DUT cleanup failure" in data["error"]
            assert "Mock iperf3 cleanup failure" in data["error"]

            print("[PASS] Execution error preserved")
            print("[PASS] DUT cleanup error recorded")
            print("[PASS] iperf3 cleanup error recorded")
            print("[PASS] Cleanup ERROR JSON generated")

if __name__ == "__main__":
    main()
    test_cleanup_error()

