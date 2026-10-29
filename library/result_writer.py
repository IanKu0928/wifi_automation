import json


def write_result_json(
    file_path,
    run_id,
    results,
    metadata=None,
    timing=None,
    error=None
):

    total = len(results)

    passed = sum(
        1 for result in results
        if result.passed
    )

    failed = total - passed

    if total == 0 and error is None:
        error = "No test cases were executed"

    if error is not None:
        overall_status = "ERROR"
    elif total == 0:
        overall_status = "ERROR"
    elif failed > 0:
        overall_status = "FAIL"
    else:
        overall_status = "PASS"

    data = {
        "run_id": run_id,
        "metadata": metadata if metadata is not None else {},
        "timing": timing if timing is not None else {},
        "overall_status": overall_status,
        "error": error,
        "summary": {
            "total": total,
            "pass": passed,
            "fail": failed
        },
        "testcases": []
    }

    for result in results:

        testcase = {
            "test_id": result.test_id,
            "name": result.name,
            "status": result.status,
            "message": result.message,
            "metrics": result.metrics
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
            indent=4,
            ensure_ascii=False
        )

    return data
