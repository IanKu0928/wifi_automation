"""Offline validation for trusted, local Python configuration files."""
import contextlib
import io
import ipaddress
import re
import runpy
from pathlib import Path


def load_local_config(path):
    # Local configuration is executable Python: only use files you trust.
    # Suppress config-file output and never include exception text/source lines.
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return runpy.run_path(str(Path(path)))
    except (Exception, SystemExit):
        raise ValueError("Cannot load local configuration; check file presence, syntax and readability") from None


def validate_credentials(values):
    for field in ("DUT_USERNAME", "DUT_PASSWORD", "STA_USERNAME", "STA_PASSWORD"):
        value = values.get(field)
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string")
        if field.endswith("USERNAME") and not value.strip():
            raise ValueError(f"{field} must be non-empty")
        if value in ("your_dut_username", "your_dut_password", "your_sta_username", "your_sta_password"):
            raise ValueError(f"{field} still contains an example placeholder")


def validate_testbed(values):
    for field in ("CONTROL_DATA_IP", "DUT_IP", "STA_MGMT_IP"):
        value = values.get(field)
        try:
            if not isinstance(value, str):
                raise ValueError()
            # Only the WiFi data path/firewall commands require IPv4.
            if field == "STA_MGMT_IP":
                ipaddress.ip_address(value)
            else:
                ipaddress.IPv4Address(value)
        except ValueError:
            family = "an IP" if field == "STA_MGMT_IP" else "an IPv4"
            raise ValueError(f"{field} must be {family} address") from None

    for field in ("DUT_WIFI_INTERFACE", "STA_WIFI_INTERFACE"):
        value = values.get(field)
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[A-Za-z0-9_.:@-]{1,15}", value) is None
            or value in (".", "..")
            or value.startswith("-")
        ):
            raise ValueError(f"{field} must be a shell-safe interface name of 1 to 15 characters")

    ssid = values.get("DUT_WIFI_SSID")
    if not isinstance(ssid, str) or not 1 <= len(ssid.encode("utf-8")) <= 32 or "\x00" in ssid:
        raise ValueError("DUT_WIFI_SSID must be a string of 1 to 32 UTF-8 bytes without NUL")
    if "DUT_WIFI_PASSWORD" not in values or (
        values["DUT_WIFI_PASSWORD"] is not None
        and not isinstance(values["DUT_WIFI_PASSWORD"], str)
    ):
        raise ValueError("DUT_WIFI_PASSWORD must be a string or None (empty string/None allows open networks)")
    if values["DUT_WIFI_PASSWORD"] == "YOUR_WIFI_PASSWORD":
        raise ValueError("DUT_WIFI_PASSWORD still contains an example placeholder")
