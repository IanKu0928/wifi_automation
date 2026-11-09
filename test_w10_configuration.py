"""Synthetic offline preflight/profile/installer regressions."""
import contextlib
import copy
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

import check_environment as checker
from library.config_loader import ConfigLoader
from library.config_validation import load_local_config, validate_credentials, validate_testbed

ROOT = Path(__file__).resolve().parent
SENTINEL = "SYNTHETIC_SECRET_DO_NOT_PRINT_9281"
CREDENTIALS = {"DUT_USERNAME": "mock_dut", "DUT_PASSWORD": SENTINEL,
               "STA_USERNAME": "mock_sta", "STA_PASSWORD": SENTINEL}
TESTBED = {"CONTROL_DATA_IP": "192.0.2.2", "DUT_IP": "192.0.2.1",
           "STA_MGMT_IP": "198.51.100.2", "DUT_WIFI_INTERFACE": "wlan0",
           "STA_WIFI_INTERFACE": "wlx001122334455", "DUT_WIFI_SSID": "Mock WiFi 網路",
           "DUT_WIFI_PASSWORD": SENTINEL}
PROFILE = {"profile_name": "smoke", "connectivity": {"ping_count": 5, "max_packet_loss_percent": 1.0},
           "wifi_signal": {"min_signal_dbm": -70},
           "throughput": {"duration_sec": 5, "upload_min_mbps": 30, "download_min_mbps": 30}}


def write_config(path, values):
    path.write_text("\n".join(f"{key} = {value!r}" for key, value in values.items()))
    path.chmod(0o600)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="w10_config_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config"
        self.config.mkdir()
        write_config(self.config / "credentials.py", CREDENTIALS)
        write_config(self.config / "testbed.py", TESTBED)
        for filename in ("smoke.json", "test_profile.json", "performance.json"):
            (self.config / filename).write_text(json.dumps(PROFILE))
        for folder in ("library", "device", "testcase"):
            shutil.copytree(ROOT / folder, self.root / folder)
        for filename in ("run_test.py", "config/credentials.example.py", "config/testbed.example.py"):
            (self.root / filename).write_text("# Synthetic presence fixture\n")
        self.addCleanup(patch.stopall)
        patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")).start()
        patch("socket.create_connection", side_effect=AssertionError("Network forbidden")).start()

    def preflight(self):
        output = io.StringIO()
        os_release = unittest.mock.Mock()
        os_release.exists.return_value = True
        os_release.read_text.return_value = 'ID=ubuntu\nVERSION_ID="24.04"\n'
        version = namedtuple("Version", "major minor micro releaselevel serial")(3, 12, 3, "final", 0)
        with patch.object(checker, "BASE_DIR", self.root), \
             patch.object(checker, "Path", return_value=os_release), \
             patch.object(checker.sys, "version_info", version), \
             patch.object(checker.importlib, "import_module", return_value=None), \
             patch.object(checker.shutil, "which", side_effect=lambda cmd: "/mock/" + cmd), \
             contextlib.redirect_stdout(output):
            code = checker.main()
        self.assertNotIn(SENTINEL, output.getvalue())
        return code, output.getvalue()

    def test_valid_configuration_and_repeatable_summary(self):
        for _ in range(2):
            code, output = self.preflight()
            self.assertEqual(code, 0)
            self.assertIn("PASS    : 15", output)
            self.assertIn("FAIL    : 0", output)
            self.assertIn("WARNING : 0", output)

    def test_open_network_and_ssid_variants(self):
        for password in (None, "", "short", SENTINEL):
            for ssid in ("a", "Space and 'quotes'", "界" * 10, "x" * 32):
                with self.subTest(password_type=type(password).__name__, ssid_bytes=len(ssid.encode())):
                    values = dict(TESTBED, DUT_WIFI_PASSWORD=password, DUT_WIFI_SSID=ssid)
                    validate_testbed(values)
        validate_credentials(dict(CREDENTIALS, DUT_PASSWORD="", STA_PASSWORD=""))
        validate_testbed(dict(TESTBED, STA_MGMT_IP="2001:db8::2"))

    def test_missing_and_invalid_local_values(self):
        for baseline, validator in ((CREDENTIALS, validate_credentials), (TESTBED, validate_testbed)):
            for key in baseline:
                for mode in ("missing", "wrong_type"):
                    values = dict(baseline)
                    if mode == "missing":
                        values.pop(key)
                    else:
                        values[key] = []
                    with self.subTest(field=key, mode=mode), self.assertRaises(ValueError):
                        validator(values)
        for key, value in (("DUT_IP", "invalid"), ("DUT_IP", "2001:db8::1"),
                           ("DUT_IP", "192.0.2.999"), ("STA_MGMT_IP", "not-an-ip"),
                           ("STA_WIFI_INTERFACE", "wlan0;id"),
                           ("STA_WIFI_INTERFACE", "-wlan0"), ("DUT_WIFI_INTERFACE", "x" * 16),
                           ("DUT_WIFI_SSID", ""), ("DUT_WIFI_SSID", "界" * 11),
                           ("DUT_WIFI_SSID", "a\x00b"), ("DUT_WIFI_PASSWORD", 123)):
            with self.subTest(field=key), self.assertRaises(ValueError):
                validate_testbed(dict(TESTBED, **{key: value}))
        for field, value in (("DUT_USERNAME", ""), ("STA_USERNAME", "your_sta_username")):
            with self.assertRaises(ValueError):
                validate_credentials(dict(CREDENTIALS, **{field: value}))

    def test_missing_local_files(self):
        for filename in ("credentials.py", "testbed.py"):
            path = self.config / filename
            original = path.read_text()
            path.unlink()
            code, output = self.preflight()
            self.assertEqual(code, 1)
            self.assertIn(f"[FAIL] Configuration: {filename}", output)
            path.write_text(original)
            path.chmod(0o600)

    def test_config_syntax_execution_and_output_are_private(self):
        path = self.config / "credentials.py"
        for source in (f'BROKEN = "{SENTINEL}', f'print("{SENTINEL}")\nraise RuntimeError("{SENTINEL}")',
                       f'print("{SENTINEL}")\nraise SystemExit("{SENTINEL}")'):
            path.write_text(source)
            code, output = self.preflight()
            self.assertEqual(code, 1)
            self.assertNotIn("Traceback", output)
        path.write_bytes(b'\xff')
        self.assertEqual(self.preflight()[0], 1)

    def test_credential_permission_failure_and_testbed_warning(self):
        (self.config / "credentials.py").chmod(0o644)
        code, output = self.preflight()
        self.assertEqual(code, 1)
        self.assertIn("[FAIL] Credentials Permissions", output)
        (self.config / "credentials.py").chmod(0o600)
        (self.config / "testbed.py").chmod(0o644)
        code, output = self.preflight()
        self.assertEqual(code, 0)
        self.assertIn("[WARNING] Testbed Permissions", output)

    def test_profile_validation_ranges_types_and_structure(self):
        ConfigLoader("unused").validate(PROFILE)
        mutations = [("profile_name", None, None), ("profile_name", None, ""),
                     ("profile_name", None, 1), ("connectivity", None, []),
                     ("connectivity", "ping_count", True), ("connectivity", "ping_count", 0),
                     ("connectivity", "ping_count", 1.5), ("connectivity", "max_packet_loss_percent", -1),
                     ("connectivity", "max_packet_loss_percent", 101),
                     ("connectivity", "max_packet_loss_percent", "1"),
                     ("wifi_signal", "min_signal_dbm", -121), ("wifi_signal", "min_signal_dbm", 1),
                     ("throughput", "duration_sec", 0), ("throughput", "duration_sec", False),
                     ("throughput", "upload_min_mbps", -1), ("throughput", "download_min_mbps", float("inf")),
                     ("throughput", "download_min_mbps", float("nan")), ("throughput", "upload_min_mbps", True),
                     ("throughput", "upload_min_mbps", 10 ** 1000)]
        for section, field, value in mutations:
            data = copy.deepcopy(PROFILE)
            if field is None:
                data[section] = value
            else:
                data[section][field] = value
            with self.subTest(section=section, field=field), self.assertRaises(ValueError):
                ConfigLoader("unused").validate(data)
        for section, fields in ConfigLoader.REQUIRED_FIELDS.items():
            data = copy.deepcopy(PROFILE)
            data.pop(section)
            with self.assertRaises(ValueError):
                ConfigLoader("unused").validate(data)
            for field in fields:
                data = copy.deepcopy(PROFILE)
                data[section].pop(field)
                with self.assertRaises(ValueError):
                    ConfigLoader("unused").validate(data)
        for loss, signal in ((0, -120), (100, 0)):
            data = copy.deepcopy(PROFILE)
            data["connectivity"]["max_packet_loss_percent"] = loss
            data["wifi_signal"]["min_signal_dbm"] = signal
            data["throughput"]["upload_min_mbps"] = 0
            ConfigLoader("unused").validate(data)

    def test_preflight_rejects_bad_profiles_without_disclosing_content(self):
        path = self.config / "smoke.json"
        for source in ("[]", "{}", f'{{"{SENTINEL}"', json.dumps(dict(PROFILE, throughput=[]))):
            path.write_text(source)
            code, output = self.preflight()
            self.assertEqual(code, 1)
            self.assertIn("[FAIL] Test Profile: smoke", output)
        path.write_bytes(b"\xff")
        self.assertEqual(self.preflight()[0], 1)
        path.unlink()
        self.assertEqual(self.preflight()[0], 1)

    def test_missing_modules_commands_and_unsupported_platforms(self):
        output = io.StringIO()
        version = namedtuple("Version", "major minor micro releaselevel serial")(3, 13, 0, "final", 0)
        os_release = unittest.mock.Mock()
        os_release.exists.return_value = True
        os_release.read_text.return_value = 'ID=debian\nVERSION_ID="12"\n'
        with contextlib.redirect_stdout(output), patch.object(checker, "Path", return_value=os_release), \
             patch.object(checker.sys, "version_info", version), \
             patch.object(checker.importlib, "import_module", side_effect=ImportError(SENTINEL)), \
             patch.object(checker.shutil, "which", return_value=None):
            checker.passed = checker.failed = checker.warnings = 0
            checker.check_os()
            checker.check_python()
            checker.check_python_module("paramiko")
            checker.check_python_module("telnetlib")
            checker.check_commands()
        self.assertEqual(checker.failed, 8)
        self.assertNotIn(SENTINEL, output.getvalue())
        self.assertNotIn("[PASS]", output.getvalue())

    def test_examples_and_ignored_local_configuration(self):
        examples = [ROOT / "config" / name for name in ("credentials.example.py", "testbed.example.py")]
        for path in examples:
            values = load_local_config(path)
            self.assertIsInstance(values, dict)
        for field in ("DUT_PASSWORD", "STA_PASSWORD"):
            self.assertTrue(load_local_config(examples[0])[field].startswith("your_"))
        self.assertEqual(load_local_config(examples[1])["DUT_WIFI_PASSWORD"], "YOUR_WIFI_PASSWORD")
        result = subprocess.run(["git", "check-ignore", "config/credentials.py", "config/testbed.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout.splitlines()), 2)

    def test_installers_syntax_only(self):
        for script in ("install_control.sh", "install_sta.sh"):
            result = subprocess.run(["bash", "-n", str(ROOT / script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
