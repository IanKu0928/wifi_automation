import json


def write_result_json(
    file_path,
    run_id,
    results
):
    total = len(results)
    passed = sum(
        1 for result in results
        if result.passed
    )
    failed = total - passed

    overall_status = (
        "PASS"
        if failed == 0
        else "FAIL"
    )

    data = {
        "run_id": run_id,
        "overall_status": overall_status,
        "summary": {
            "total": total,
            "pass": passed,
            "fail": failed,
        },
        "testcases": []
    }

    for result in results:

        testcase = {
            "test_id": result.test_id,
            "name": result.name,
            "status": result.status,
            "message": result.message,
            "metrics": result.metrics,
        }

        data["testcases"].append(
            testcase
        )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )

    return data
