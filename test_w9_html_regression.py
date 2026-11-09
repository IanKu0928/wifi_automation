
import copy
import json
import tempfile
from pathlib import Path

from library.html_report import generate_html_report


# Synthetic fixture: keep regression independent of production logs.
source_result = {
    "run_id": "20261109_142504_001",
    "overall_status": "PASS",
    "summary": {"total": 6, "pass": 6, "fail": 0},
    "testcases": [
        {"test_id": f"TC{i:02d}", "name": "Synthetic case",
         "status": "PASS", "message": "Synthetic result", "metrics": {}}
        for i in range(1, 7)
    ]
}
source_analysis = {
    "run_id": source_result["run_id"],
    "findings": [{"rule_id": "THROUGHPUT_DEGRADATION",
                  "severity": "WARNING", "test_ids": ["TC05"],
                  "title": "Synthetic throughput degradation"}],
    "historical_comparison": {
        "status": "READY", "historical_run_count": 3,
        "metrics": {"TC05.receiver_mbps": {
            "current": 100, "historical_median": 179.12,
            "historical_samples": 3, "baseline_ready": True
        }}
    }
}


def save_json(path, data):
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


with tempfile.TemporaryDirectory(prefix="w9_html_") as temp:
    root = Path(temp)

    # Case 1: PASS with analysis
    case_dir = root / "pass"
    case_dir.mkdir()

    save_json(case_dir / "result.json", source_result)
    save_json(case_dir / "analysis.json", source_analysis)

    html_path = generate_html_report(
        case_dir / "result.json"
    )
    html = html_path.read_text(encoding="utf-8")

    assert "Automated Analysis &amp; Recommendations" in html
    assert "Historical Comparison" in html
    assert "THROUGHPUT_DEGRADATION" in html
    assert "179.12" in html
    print("[PASS] PASS report with analysis")

    # Case 2: FAIL without analysis
    case_dir = root / "fail"
    case_dir.mkdir()

    data = copy.deepcopy(source_result)
    data["overall_status"] = "FAIL"
    data["summary"] = {
        "total": 6, "pass": 5, "fail": 1
    }
    data["testcases"][0]["status"] = "FAIL"
    data["testcases"][0]["message"] = (
        "Packet loss exceeded threshold"
    )

    save_json(case_dir / "result.json", data)

    html = generate_html_report(
        case_dir / "result.json"
    ).read_text(encoding="utf-8")

    assert '<span class="status fail">FAIL</span>' in html
    assert "Analysis data is not available" in html
    print("[PASS] FAIL report without analysis")

    # Case 3: ERROR without testcases
    case_dir = root / "error"
    case_dir.mkdir()

    data = copy.deepcopy(source_result)
    data["overall_status"] = "ERROR"
    data["error"] = "Mock DUT connection failure"
    data["testcases"] = []
    data["summary"] = {
        "total": 0, "pass": 0, "fail": 0
    }

    save_json(case_dir / "result.json", data)

    html = generate_html_report(
        case_dir / "result.json"
    ).read_text(encoding="utf-8")

    assert '<span class="status error">ERROR</span>' in html
    assert "Mock DUT connection failure" in html
    assert "No test cases were executed" in html
    print("[PASS] ERROR report without testcases")

    # Case 4: Analysis Run ID mismatch
    case_dir = root / "mismatch"
    case_dir.mkdir()

    save_json(case_dir / "result.json", source_result)

    bad_analysis = copy.deepcopy(source_analysis)
    bad_analysis["run_id"] = "WRONG_RUN_ID"
    save_json(case_dir / "analysis.json", bad_analysis)

    try:
        generate_html_report(case_dir / "result.json")
    except ValueError as exc:
        assert "Run ID" in str(exc)
        print("[PASS] Analysis Run ID mismatch rejected")
    else:
        raise AssertionError(
            "Mismatched analysis should be rejected"
        )

    # Case 5: HTML escaping
    case_dir = root / "escaping"
    case_dir.mkdir()

    data = copy.deepcopy(source_result)
    data["testcases"][0]["message"] = "<script>alert(1)</script>"

    save_json(case_dir / "result.json", data)

    html = generate_html_report(
        case_dir / "result.json"
    ).read_text(encoding="utf-8")

    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    print("[PASS] HTML output escaping")

print()
print("[PASS] W9-07-1 HTML Regression")

