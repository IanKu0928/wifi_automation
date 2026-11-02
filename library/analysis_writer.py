
import json
from collections import Counter
from pathlib import Path

from library.analysis_engine import AnalysisEngine
from library.history_comparator import HistoryComparator
from library.history_rules import HistoricalRules


def generate_analysis_json(
    result_path,
    analysis_path=None,
    log_dir="logs",
    min_samples=3
):
    result_path = Path(result_path)

    if analysis_path is None:
        analysis_path = result_path.with_name("analysis.json")
    else:
        analysis_path = Path(analysis_path)

    # Load the original test result.
    with result_path.open("r", encoding="utf-8") as f:
        result_data = json.load(f)

    # 1. Current run diagnosis.
    current_analysis = AnalysisEngine().analyze(result_data)

    # 2. Historical comparison.
    comparison = HistoryComparator(
        log_dir=log_dir,
        min_samples=min_samples
    ).compare(result_path)

    # 3. Historical diagnostic rules.
    historical_analysis = HistoricalRules().analyze(comparison)

    # Combine findings without modifying test status.
    findings = []

    for finding in current_analysis["findings"]:
        entry = dict(finding)
        entry["source"] = "current_run"
        findings.append(entry)

    for finding in historical_analysis["findings"]:
        entry = dict(finding)
        entry["source"] = "historical"
        findings.append(entry)

    severity_counts = Counter(
        finding["severity"] for finding in findings
    )

    analysis = {
        "analysis_version": "W9-05-v1",
        "run_id": result_data.get("run_id"),
        "test_status": result_data.get("overall_status"),
        "summary": {
            "total_findings": len(findings),
            "critical": severity_counts["CRITICAL"],
            "warning": severity_counts["WARNING"],
            "info": severity_counts["INFO"]
        },
        "current_analysis": current_analysis,
        "historical_comparison": comparison,
        "historical_analysis": historical_analysis,
        "findings": findings
    }

    analysis_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with analysis_path.open("w", encoding="utf-8") as f:
        json.dump(
            analysis,
            f,
            indent=4,
            ensure_ascii=False,
            allow_nan=False
        )

    return analysis_path

