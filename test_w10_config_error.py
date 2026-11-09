"""Early configuration/report failures with all network/process access forbidden."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import run_test
from library.config_loader import ConfigLoader
from library.logger import TestLogger
from test_w10_configuration import PROFILE

SECRETS = ("SYNTHETIC_DUT_SECRET_1101", "SYNTHETIC_STA_SECRET_2202", "SYNTHETIC_WIFI_SECRET_3303")


class ConfigErrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="w10_config_error_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = self.root / "profile.json"
        self.addCleanup(patch.stopall)
        self.output = io.StringIO()
        patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")).start()
        patch("socket.create_connection", side_effect=AssertionError("Network forbidden")).start()
        patch("subprocess.Popen", side_effect=AssertionError("Process execution forbidden")).start()
        patch.object(run_test, "DUT_PASSWORD", SECRETS[0]).start()
        patch.object(run_test, "STA_PASSWORD", SECRETS[1]).start()
        patch.object(run_test, "DUT_WIFI_PASSWORD", SECRETS[2]).start()
        patch.object(run_test, "parse_args", return_value=SimpleNamespace(profile="smoke")).start()
        patch.object(run_test, "ConfigLoader", side_effect=lambda path: ConfigLoader(self.profile)).start()
        patch.object(run_test, "TestLogger", side_effect=lambda: TestLogger(self.root / "runs")).start()
        self.dut = patch.object(run_test, "DUT").start()
        self.sta = patch.object(run_test, "GoldenSTA").start()
        self.iperf = patch.object(run_test, "IperfServer").start()
        real_analysis = run_test.generate_analysis_json
        self.analysis = patch.object(run_test, "generate_analysis_json", side_effect=lambda result_path, **kw: real_analysis(result_path, log_dir=self.root / "runs")).start()
        self.html = patch.object(run_test, "generate_html_report", wraps=run_test.generate_html_report).start()

    def execute(self):
        with contextlib.redirect_stdout(self.output):
            code = run_test.main()
        combined = self.output.getvalue()
        for path in (self.root / "runs").rglob("*"):
            if path.is_file():
                combined += path.read_text()
        for secret in SECRETS:
            self.assertNotIn(secret, combined)
        self.assertNotIn("Traceback", combined)
        return code

    def verify_error_reports(self, expected_type):
        self.assertEqual(self.execute(), 1)
        paths = list((self.root / "runs").glob("*/result.json"))
        self.assertEqual(len(paths), 1)
        result = json.loads(paths[0].read_text())
        self.assertEqual(result["overall_status"], "ERROR")
        self.assertEqual(result["summary"]["total"], 0)
        self.assertIn(expected_type + ":", result["error"])
        analysis = json.loads(paths[0].with_name("analysis.json").read_text())
        self.assertEqual(analysis["test_status"], "ERROR")
        self.assertIn('<span class="status error">ERROR</span>', paths[0].with_name("report.html").read_text())
        self.sta.assert_not_called()
        return result

    def test_missing_profile(self):
        self.verify_error_reports("FileNotFoundError")
        self.dut.assert_not_called()
        self.iperf.assert_not_called()

    def test_malformed_profile(self):
        self.profile.write_text('{"broken":')
        self.verify_error_reports("JSONDecodeError")
        self.dut.assert_not_called()
        self.iperf.assert_not_called()

    def test_invalid_profile_fields(self):
        self.profile.write_text(json.dumps(dict(PROFILE, throughput=[])))
        self.verify_error_reports("ValueError")
        self.dut.assert_not_called()
        self.iperf.assert_not_called()

    def test_missing_profile_name(self):
        data = dict(PROFILE)
        data.pop("profile_name")
        self.profile.write_text(json.dumps(data))
        self.verify_error_reports("ValueError")
        self.dut.assert_not_called()

    def test_iperf_constructor_failure(self):
        self.profile.write_text(json.dumps(PROFILE))
        self.iperf.side_effect = RuntimeError("mock resource init " + " ".join(SECRETS))
        result = self.verify_error_reports("RuntimeError")
        self.assertIn("mock resource init", result["error"])
        self.assertIn("[REDACTED]", result["error"])
        self.dut.assert_not_called()

    def test_dut_constructor_failure_cleans_initialized_resource(self):
        self.profile.write_text(json.dumps(PROFILE))
        self.dut.side_effect = RuntimeError("mock DUT init")
        self.verify_error_reports("RuntimeError")
        self.iperf.return_value.stop.assert_called_once()

    def test_result_write_failure_is_explicit(self):
        with patch.object(run_test, "write_result_json", side_effect=OSError("mock disk failure " + SECRETS[0])):
            self.assertEqual(self.execute(), 1)
        self.analysis.assert_not_called()
        self.html.assert_not_called()
        self.assertIn("Result JSON Generation Failed: OSError: mock disk failure", self.output.getvalue())
        self.assertNotIn("Result JSON:", self.output.getvalue())

    def test_analysis_failure_still_attempts_html(self):
        self.analysis.side_effect = RuntimeError("mock analysis " + SECRETS[1])
        self.assertEqual(self.execute(), 1)
        self.html.assert_called_once()
        self.assertIn("Analysis JSON Generation Failed:", self.output.getvalue())
        self.assertNotIn("Analysis JSON:", self.output.getvalue())
        self.assertTrue(list((self.root / "runs").glob("*/report.html")))

    def test_html_failure_does_not_claim_html_success(self):
        self.html.side_effect = RuntimeError("mock HTML " + SECRETS[2])
        self.assertEqual(self.execute(), 1)
        self.assertIn("HTML Report Generation Failed:", self.output.getvalue())
        self.assertNotIn("HTML Report:", self.output.getvalue())
        self.assertTrue(list((self.root / "runs").glob("*/result.json")))
        self.assertTrue(list((self.root / "runs").glob("*/analysis.json")))


if __name__ == "__main__":
    unittest.main()
