import json

from mcp_doctor.models import DiagnosticReport, Finding
from mcp_doctor.report import render_json, render_text, stable_summary


def test_json_report_schema_and_summary_are_stable() -> None:
    report = DiagnosticReport(tool="MCP-Doctor", tool_version="0.2.0", target="fixture")
    report.add(Finding("MCPD-TEST", "pass", "Healthy", "Test passed.", "Continue.", "test"))
    data = json.loads(render_json(report))

    assert data["schema_version"] == "1.0"
    assert data["status"] == "passed"
    assert data["summary"] == {"errors": 0, "warnings": 0, "passed": 1, "total_findings": 1}
    assert stable_summary(data)["target"] == "fixture"


def test_error_changes_exit_code_and_text_contains_actionable_next_step() -> None:
    report = DiagnosticReport(tool="MCP-Doctor", tool_version="0.2.0", target="fixture")
    report.add(Finding("MCPD-FAIL", "error", "Server failed", "No response.", "Inspect server startup.", "protocol"))

    assert report.exit_code == 1
    text = render_text(report)
    assert "MCPD-FAIL" in text
    assert "Inspect server startup." in text
