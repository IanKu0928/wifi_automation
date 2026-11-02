
import json
from pathlib import Path
from collections import Counter


LOG_DIR = Path("logs")

COMPARE_FIELDS = [
    ("profile",),
    ("dut", "ip"),
    ("dut", "version"),
    ("wifi", "interface"),
    ("wifi", "ssid"),
    ("wifi", "bssid"),
    ("wifi", "frequency_ghz"),
]


def get_field(metadata, path):
    value = metadata

    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)

    return value


def get_comparison_key(data):
    metadata = data.get("metadata") or {}

    values = tuple(
        get_field(metadata, path)
        for path in COMPARE_FIELDS
    )

    # Unknown metadata must not be treated
    # as proof of identical test conditions.
    if any(value is None or value == "" for value in values):
        return None

    return values


def main():
    files = sorted(LOG_DIR.glob("*/result.json"))

    groups = Counter()
    profiles = Counter()
    incomplete = 0
    invalid = 0
    skipped = Counter()

    for path in files:
        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            invalid += 1
            continue

        status = data.get("overall_status")

        if status != "PASS":
            skipped[status or "UNKNOWN"] += 1
            continue

        profile = (
            (data.get("metadata") or {}).get("profile")
        )

        key = get_comparison_key(data)

        if key is None:
            incomplete += 1
            continue

        testcases = data.get("testcases") or []

        # Require a complete six-case PASS run.
        expected_ids = {
            "TC01", "TC02", "TC03",
            "TC04", "TC05", "TC06"
        }

        ids = {
            tc.get("test_id")
            for tc in testcases
            if tc.get("status") == "PASS"
        }

        if len(testcases) != 6 or ids != expected_ids:
            incomplete += 1
            continue

        groups[key] += 1
        profiles[profile] += 1

    print("================================")
    print(" Week 9 Historical Inventory")
    print("================================")

    print("Total JSON:", len(files))
    print("Invalid JSON:", invalid)
    print("Skipped by status:", dict(skipped))
    print("Incomplete PASS runs:", incomplete)

    print()
    print("Comparable PASS groups:")

    if not groups:
        print("None")

    for key, count in groups.most_common():
        profile, dut_ip, firmware, interface, ssid, bssid, freq = key

        print("--------------------------------")
        print("Profile:", profile)
        print("DUT:", dut_ip)
        print("Firmware:", firmware)
        print("Interface:", interface)
        print("SSID:", ssid)
        print("BSSID:", bssid)
        print("Frequency:", freq, "GHz")
        print("Historical Runs:", count)
        print(
            "Baseline Ready:",
            "YES" if count >= 3 else "NO"
        )

    print("--------------------------------")
    print("Eligible profiles:", dict(profiles))
    print("Comparable groups:", len(groups))


if __name__ == "__main__":
    main()

