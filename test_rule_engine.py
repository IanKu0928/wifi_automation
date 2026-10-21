from library.rule_engine import RuleEngine


def test_rule_engine():

    tests = [
        # Throughput >= 30 Mbps
        ("Throughput Equal", 30.0, ">=", 30.0, True),
        ("Throughput Above", 30.01, ">=", 30.0, True),
        ("Throughput Below", 29.99, ">=", 30.0, False),

        # Packet Loss <= 1%
        ("Packet Loss Equal", 1.0, "<=", 1.0, True),
        ("Packet Loss Below", 0.99, "<=", 1.0, True),
        ("Packet Loss Above", 1.01, "<=", 1.0, False),

        # RSSI >= -70 dBm
        ("RSSI Equal", -70, ">=", -70, True),
        ("RSSI Stronger", -69, ">=", -70, True),
        ("RSSI Weaker", -71, ">=", -70, False),

        # SSID / BSSID
        ("SSID Match", "RTL867x-ADSL", "==", "RTL867x-ADSL", True),
        ("SSID Mismatch", "WrongSSID", "==", "RTL867x-ADSL", False),
        ("BSSID Match", "00:e0:4c:86:70:01", "==", "00:e0:4c:86:70:01", True),
        ("BSSID Mismatch", "00:e0:4c:86:70:02", "==", "00:e0:4c:86:70:01", False),

        # Other operators
        ("Greater Than PASS", 11, ">", 10, True),
        ("Greater Than Equal FAIL", 10, ">", 10, False),
        ("Less Than PASS", 9, "<", 10, True),
        ("Less Than Equal FAIL", 10, "<", 10, False),
        ("Not Equal PASS", "A", "!=", "B", True),
        ("Not Equal FAIL", "A", "!=", "A", False),
    ]

    failed = 0

    for name, actual, op, threshold, expected in tests:

        result = RuleEngine.evaluate(
            value=actual,
            operator_symbol=op,
            threshold=threshold
        )

        ok = (
            result["passed"] == expected
            and result["error"] is None
        )

        print(
            f"[{'PASS' if ok else 'FAIL'}] "
            f"{name}: actual={result['passed']}, "
            f"expected={expected}"
        )

        if not ok:
            failed += 1

    total = len(tests)

    print("--------------------------------")
    print(f"Total : {total}")
    print(f"Pass  : {total - failed}")
    print(f"Fail  : {failed}")

    if failed:
        raise SystemExit(1)

    print("[PASS] Rule Engine Boundary Test")


if __name__ == "__main__":
    test_rule_engine()
