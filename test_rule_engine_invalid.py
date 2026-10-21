from library.rule_engine import RuleEngine


def main():

    tests = [
        # name, actual, operator, threshold, expected_error

        ("Missing Actual", None, ">=", 30, True),
        ("Missing Threshold", 65, ">=", None, True),

        ("Actual NaN", float("nan"), ">=", 30, True),
        ("Threshold NaN", 65, ">=", float("nan"), True),

        ("Actual Infinity", float("inf"), ">=", 30, True),
        ("Actual -Infinity", float("-inf"), ">=", 30, True),
        ("Threshold Infinity", 65, ">=", float("inf"), True),

        ("Invalid Operator", 65, "invalid", 30, True),

        ("String vs Number", "65", ">=", 30, True),
        ("Number vs String", 65, ">=", "30", True),

        ("Boolean Actual", True, ">=", 30, True),
        ("Boolean Threshold", 65, ">=", False, True),

        # Valid comparison, but condition is not satisfied
        ("Normal FAIL", 20, ">=", 30, False),
    ]

    failed = 0

    for name, actual, op, threshold, expected_error in tests:

        result = RuleEngine.evaluate(
            value=actual,
            operator_symbol=op,
            threshold=threshold
        )

        error_detected = result["error"] is not None

        ok = (
            result["passed"] is False
            and error_detected == expected_error
        )

        if not ok:
            failed += 1

        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}: "
            f"passed={result['passed']}, "
            f"error={result['error']}"
        )

    total = len(tests)

    print("--------------------------------")
    print(f"Total : {total}")
    print(f"Pass  : {total - failed}")
    print(f"Fail  : {failed}")

    if failed:
        raise SystemExit(1)

    print("[PASS] Rule Engine Invalid Data Test")


if __name__ == "__main__":
    main()
