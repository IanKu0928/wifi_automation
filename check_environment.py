
#!/usr/bin/env python3

import importlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path


from library.config_loader import ConfigLoader
from library.config_validation import (
    load_local_config, validate_credentials, validate_testbed,
)

BASE_DIR = Path(__file__).resolve().parent

passed = 0
failed = 0
warnings = 0


def report(status, name, detail=""):
    global passed, failed, warnings

    if status == "PASS":
        passed += 1
    elif status == "FAIL":
        failed += 1
    else:
        warnings += 1

    message = f"[{status}] {name}"

    if detail:
        message += f": {detail}"

    print(message)


def check_os():
    path = Path("/etc/os-release")

    if not path.exists():
        report("FAIL", "Operating System", "os-release missing")
        return

    values = {}

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        report("FAIL", "Operating System", "Cannot read os-release")
        return

    for line in lines:
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')

    os_id = values.get("ID")
    version = values.get("VERSION_ID")

    if os_id == "ubuntu" and version == "24.04":
        report("PASS", "Operating System", "Ubuntu 24.04")
    else:
        report(
            "FAIL",
            "Operating System",
            f"Expected Ubuntu 24.04; found {os_id} {version}"
        )


def check_python():
    version = sys.version_info

    if version[:2] == (3, 12):
        report("PASS", "Python", sys.version.split()[0])
    else:
        report(
            "FAIL",
            "Python",
            f"Expected Python 3.12; found {version.major}.{version.minor}"
        )


def check_python_module(module_name):
    try:
        if module_name == "telnetlib":
            import warnings as warning_module

            with warning_module.catch_warnings():
                warning_module.simplefilter(
                    "ignore", DeprecationWarning
                )
                importlib.import_module(module_name)
        else:
            importlib.import_module(module_name)

        report("PASS", f"Python Module: {module_name}")

    except (ImportError, OSError):
        report(
            "FAIL",
            f"Python Module: {module_name}",
            "Cannot import required module"
        )


def check_commands():
    for command in ("iperf3", "ping", "ip", "ssh"):
        path = shutil.which(command)

        if path:
            report("PASS", f"Command: {command}", path)
        else:
            report("FAIL", f"Command: {command}", "Not found")


def check_credentials():
    path = BASE_DIR / "config" / "credentials.py"

    if not path.is_file():
        report(
            "FAIL",
            "Credentials",
            "config/credentials.py missing"
        )
        return

    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        report("FAIL", "Credentials Permissions", "Cannot inspect credentials file")
        return

    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        report(
            "FAIL",
            "Credentials Permissions",
            f"Permissions {mode:03o} allow group/other access"
        )
    elif not os.access(path, os.R_OK):
        report(
            "FAIL",
            "Credentials Permissions",
            "Current user cannot read credentials"
        )
    else:
        report(
            "PASS",
            "Credentials Permissions",
            f"Permissions {mode:03o}"
        )


def check_local_configuration():
    for filename, validator in (
        ("credentials.py", validate_credentials),
        ("testbed.py", validate_testbed),
    ):
        path = BASE_DIR / "config" / filename
        try:
            values = load_local_config(path)
            validator(values)
            report("PASS", f"Configuration: {filename}", "Required values validated (values hidden)")
            if filename == "testbed.py" and path.stat().st_mode & 0o077:
                report("WARNING", "Testbed Permissions", "Use chmod 600; testbed may contain a WiFi password")
        except (OSError, UnicodeError):
            report("FAIL", f"Configuration: {filename}", "Cannot inspect configuration")
        except ValueError as exc:
            report("FAIL", f"Configuration: {filename}", str(exc))


def check_profiles():
    profiles = {
        "smoke": "smoke.json",
        "default": "test_profile.json",
        "performance": "performance.json"
    }
    for profile_name, filename in profiles.items():
        try:
            ConfigLoader(BASE_DIR / "config" / filename).load()
            report("PASS", f"Test Profile: {profile_name}", filename)
        except (OSError, json.JSONDecodeError, UnicodeError):
            # Parsing/filesystem errors may include source content or paths.
            report("FAIL", f"Test Profile: {profile_name}",
                   "Cannot load profile; check file presence, JSON syntax and encoding")
        except ValueError as exc:
            # ConfigLoader validation messages contain field names, never values.
            report("FAIL", f"Test Profile: {profile_name}", str(exc))


def check_framework_files():
    required_files = [
        "run_test.py",
        "config/testbed.py",
        "config/credentials.example.py",
        "device/dut.py",
        "device/golden_sta.py",
        "library/config_loader.py",
        "library/config_validation.py",
        "config/testbed.example.py",
        "library/analysis_engine.py",
        "library/analysis_writer.py",
        "library/history_analyzer.py",
        "library/history_comparator.py",
        "library/history_rules.py",
        "library/html_report.py",
        "library/result_writer.py",
        "testcase/runner.py"
    ]

    missing = [
        filename for filename in required_files
        if not (BASE_DIR / filename).is_file()
    ]

    if missing:
        report(
            "FAIL",
            "Framework Files",
            ", ".join(missing)
        )
    else:
        report(
            "PASS",
            "Framework Files",
            f"{len(required_files)} required files found"
        )


def main():
    global passed, failed, warnings
    passed = failed = warnings = 0
    print("=" * 50)
    print(" WiFi Automation Framework")
    print(" Week 10 - Control PC Preflight Check")
    print("=" * 50)

    check_os()
    check_python()

    for module in ("paramiko", "telnetlib"):
        check_python_module(module)

    check_commands()
    check_credentials()
    check_local_configuration()
    check_profiles()
    check_framework_files()

    print()
    print("=" * 50)
    print(" Environment Check Summary")
    print("=" * 50)
    print(f"PASS    : {passed}")
    print(f"FAIL    : {failed}")
    print(f"WARNING : {warnings}")

    if failed:
        print("[FAIL] Local environment is not ready")
        return 1

    print("[PASS] Local preflight checks completed")
    print("[INFO] DUT/STA connectivity is not checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())

