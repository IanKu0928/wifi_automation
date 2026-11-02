
import json
from pathlib import Path
from html import escape


def html_text(value):
    if value is None:
        return "-"
    return escape(str(value), quote=True)

def format_metric(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.2f}"
    return html_text(value)

def status_class(status):
    if status == "PASS":
        return "pass"
    if status == "FAIL":
        return "fail"
    return "error"


def generate_html_report(json_path, html_path=None):
    json_path = Path(json_path)

    if html_path is None:
        html_path = json_path.with_name("report.html")
    else:
        html_path = Path(html_path)

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata") or {}
    timing = data.get("timing") or {}
    summary = data.get("summary") or {}
    testcases = data.get("testcases") or []

    dut = metadata.get("dut") or {}
    wifi = metadata.get("wifi") or {}
    sta = metadata.get("sta") or {}
    control = metadata.get("control") or {}

    status = data.get("overall_status", "ERROR")
    status_css = status_class(status)

    info = [
        ("Run ID", data.get("run_id")),
        ("Test Profile", metadata.get("profile")),
        ("DUT IP", dut.get("ip")),
        ("Firmware Version", dut.get("version")),
        ("WiFi Interface", wifi.get("interface")),
        ("SSID", wifi.get("ssid")),
        ("BSSID", wifi.get("bssid")),
        ("Frequency (GHz)", wifi.get("frequency_ghz")),
        ("STA Management IP", sta.get("management_ip")),
        ("STA WiFi IP", sta.get("wifi_ip")),
        ("Control Data IP", control.get("data_ip")),
        ("Start Time", timing.get("start_time")),
        ("End Time", timing.get("end_time")),
        ("Duration (sec)", timing.get("duration_sec")),
    ]

    info_rows = "\n".join(
        "<tr><th>{}</th><td>{}</td></tr>".format(
            html_text(key),
            html_text(value)
        )
        for key, value in info
    )

    testcase_rows = []

    for tc in testcases:
        tc_status = tc.get("status", "ERROR")
        metrics = tc.get("metrics") or {}

        metrics_html = "<br>".join(
            "{}: {}".format(
                html_text(key),
                html_text(value)
            )
            for key, value in metrics.items()
        )

        if not metrics_html:
            metrics_html = "-"

        testcase_rows.append(
            "<tr>"
            "<td>{}</td>"
            "<td>{}</td>"
            '<td><span class="status {}">{}</span></td>'
            "<td>{}</td>"
            "<td>{}</td>"
            "</tr>".format(
                html_text(tc.get("test_id")),
                html_text(tc.get("name")),
                status_class(tc_status),
                html_text(tc_status),
                html_text(tc.get("message")),
                metrics_html
            )
        )

    if not testcase_rows:
        testcase_rows.append(
            '<tr><td colspan="5">'
            'No test cases were executed.'
            '</td></tr>'
        )

    error = data.get("error")
    error_section = ""

    if error:
        error_section = (
            '<section class="error-box">'
            '<h2>Execution Error</h2>'
            '<pre>{}</pre>'
            '</section>'
        ).format(html_text(error))

    # --------------------------------
    # Week 9: Analysis Report Section
    # --------------------------------

    analysis_section = ""
    comparison_section = ""

    analysis_path = json_path.with_name("analysis.json")

    if analysis_path.exists():
        with analysis_path.open("r", encoding="utf-8") as f:
            analysis_data = json.load(f)

        findings = analysis_data.get("findings") or []
        analysis_summary = analysis_data.get("summary") or {}
        historical = (
            analysis_data.get("historical_comparison") or {}
        )

        # Confirm the analysis belongs to this test run.
        if analysis_data.get("run_id") != data.get("run_id"):
            raise ValueError(
                "Analysis JSON Run ID does not match Result JSON"
            )

        def render_list(items):
            if not items:
                return "<p>-</p>"

            return "<ul>{}</ul>".format(
                "".join(
                    "<li>{}</li>".format(html_text(item))
                    for item in items
                )
            )

        finding_rows = []

        for finding in findings:
            severity = finding.get("severity", "INFO")
            source = finding.get("source", "unknown")
            test_ids = finding.get("test_ids") or []

            detail = (
                "<strong>Evidence:</strong> {}"
                "<br><strong>Possible Causes:</strong> {}"
                "<br><strong>Recommendations:</strong> {}"
            ).format(
                html_text(finding.get("evidence")),
                render_list(finding.get("possible_causes")),
                render_list(finding.get("recommendations"))
            )

            finding_rows.append(
                "<tr>"
                "<td>{}</td>"
                "<td>{}</td>"
                '<td class="analysis-rule">{}</td>'
                "<td>{}</td>"
                "<td>{}</td>"
                "</tr>".format(
                    html_text(severity),
                    html_text(source),
                    html_text(finding.get("rule_id")),
                    html_text(
                        ", ".join(test_ids) if test_ids else "-"
                    ),
                    "<strong>{}</strong><br>{}".format(
                        html_text(finding.get("title")),
                        detail
                    )
                )
            )

        if not finding_rows:
            finding_rows.append(
                '<tr><td colspan="5">'
                'No analysis findings available.'
                '</td></tr>'
            )

        analysis_section = """
        <section>
          <h2>Automated Analysis &amp; Recommendations</h2>
          <p>
            Rule-based analysis only. Findings are diagnostic
            observations and do not change the original
            test PASS / FAIL / ERROR status.
          </p>
          <p>
            <strong>Total Findings:</strong> {total}
            &nbsp; | &nbsp;
            <strong>Critical:</strong> {critical}
            &nbsp; | &nbsp;
            <strong>Warning:</strong> {warning}
            &nbsp; | &nbsp;
            <strong>Info:</strong> {info}
          </p>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Source</th>
                  <th>Rule ID</th>
                  <th>Test Cases</th>
                  <th>Analysis Details</th>
                </tr>
              </thead>
              <tbody>{rows}</tbody>
            </table>
          </div>
        </section>
        """.format(
            total=html_text(
                analysis_summary.get("total_findings", 0)
            ),
            critical=html_text(
                analysis_summary.get("critical", 0)
            ),
            warning=html_text(
                analysis_summary.get("warning", 0)
            ),
            info=html_text(
                analysis_summary.get("info", 0)
            ),
            rows="\n".join(finding_rows)
        )

        # --------------------------------
        # Historical Comparison Table
        # --------------------------------

        comparison_rows = []

        for name, metric in (
            historical.get("metrics") or {}
        ).items():
            comparison_rows.append(
                "<tr>"
                "<td>{}</td>"
                "<td>{}</td>"
                "<td>{}</td>"
                "<td>{}</td>"
                "<td>{}</td>"
                "</tr>".format(
                    html_text(name),
                    format_metric(metric.get("current")),
                    format_metric(metric.get("historical_median")),
                    html_text(metric.get("historical_samples")),
                    html_text(
                        "YES" if metric.get("baseline_ready")
                        else "NO"
                    )
                )
            )

        if not comparison_rows:
            comparison_rows.append(
                '<tr><td colspan="5">'
                'No comparable metrics available.'
                '</td></tr>'
            )

        comparison_section = """
        <section>
          <h2>Historical Comparison</h2>
          <p>
            <strong>Status:</strong> {status}
            &nbsp; | &nbsp;
            <strong>Prior Runs:</strong> {count}
          </p>
          <p>{reason}</p>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Current</th>
                  <th>Historical Median</th>
                  <th>Samples</th>
                  <th>Baseline Ready</th>
                </tr>
              </thead>
              <tbody>{rows}</tbody>
            </table>
          </div>
          <p>
            Historical comparisons are only indicative
            when sufficient comparable samples exist.
          </p>
        </section>
        """.format(
            status=html_text(historical.get("status")),
            count=html_text(
                historical.get("historical_run_count")
            ),
            reason=html_text(historical.get("reason")),
            rows="\n".join(comparison_rows)
        )

    else:
        analysis_section = """
        <section>
          <h2>Automated Analysis</h2>
          <p>
            Analysis data is not available for this run.
          </p>
        </section>
        """

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WiFi Automation Test Report</title>
<style>
* {{ box-sizing: border-box; }}

body {{
    margin: 0;
    background: #f3f5f9;
    color: #243247;
    font-family: Arial, Helvetica, sans-serif;
    line-height: 1.5;
}}

.container {{
    max-width: 1180px;
    margin: 35px auto;
    padding: 0 20px;
}}

header {{
    background: #17345b;
    color: white;
    border-radius: 12px;
    padding: 28px;
}}

header h1 {{
    margin: 0 0 8px;
    font-size: 26px;
}}

header p {{ margin: 0; color: #dce6f4; }}

section {{
    background: white;
    padding: 24px;
    margin-top: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}}

h2 {{ margin-top: 0; font-size: 20px; }}

.summary {{
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
}}

.summary-card {{
    flex: 1 1 140px;
    background: #f3f5f9;
    padding: 18px;
    border-radius: 9px;
}}

.summary-card .number {{
    display: block;
    font-size: 28px;
    font-weight: bold;
}}

.status {{
    display: inline-block;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: bold;
}}

.pass {{ background: #e1f5e8; color: #18703c; }}
.fail {{ background: #fde8e8; color: #ad2525; }}
.error {{ background: #fff0d9; color: #915500; }}

.table-wrap {{ overflow-x: auto; }}
.analysis-rule {{
    min-width: 180px;
    overflow-wrap: normal;
    word-break: normal;
}}

table {{
    border-collapse: collapse;
    width: 100%;
}}

th, td {{
    padding: 11px 13px;
    border-bottom: 1px solid #e6eaf0;
    text-align: left;
    vertical-align: top;
    overflow-wrap: anywhere;
}}

th {{ background: #f4f6fa; }}

.info-table th {{ width: 220px; }}

.error-box {{
    border-left: 5px solid #d47c12;
}}

pre {{
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}}

footer {{
    text-align: center;
    color: #68788d;
    padding: 25px 0;
    font-size: 13px;
}}

@media (max-width: 600px) {{
    .container {{ padding: 0 10px; margin: 12px auto; }}
    section {{ padding: 14px; }}
    header {{ padding: 18px; }}
}}
</style>
</head>
<body>
<div class="container">

<header>
<h1>WiFi Automation Test Report</h1>
<p>Run ID: {run_id}</p>
</header>

<section>
<h2>Test Summary</h2>
<div class="summary">
    <div class="summary-card">
        Overall Status<br>
        <span class="status {status_css}">{status}</span>
    </div>
    <div class="summary-card">
        Total<span class="number">{total}</span>
    </div>
    <div class="summary-card">
        Pass<span class="number">{passed}</span>
    </div>
    <div class="summary-card">
        Fail<span class="number">{failed}</span>
    </div>
</div>
</section>

{error_section}

<section>
<h2>Test Environment &amp; Timing</h2>
<div class="table-wrap">
<table class="info-table">{info_rows}</table>
</div>
</section>

<section>
<h2>Test Case Results</h2>
<div class="table-wrap">
<table>
<thead>
<tr>
<th>ID</th><th>Test Name</th><th>Status</th>
<th>Message</th><th>Metrics</th>
</tr>
</thead>
<tbody>
{testcase_rows}
</tbody>
</table>
</div>
</section>

{analysis_section}

{comparison_section}
<footer>Generated by WiFi Automation Framework</footer>

</div>
</body>
</html>
""".format(
        run_id=html_text(data.get("run_id")),
        status=html_text(status),
        status_css=status_css,
        total=html_text(summary.get("total", 0)),
        passed=html_text(summary.get("pass", 0)),
        failed=html_text(summary.get("fail", 0)),
        error_section=error_section,
        info_rows=info_rows,
        testcase_rows="\n".join(testcase_rows),
        analysis_section=analysis_section,
        comparison_section=comparison_section
    )

    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")

    return html_path

