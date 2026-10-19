"""Human-readable and JSON report renderers."""
from __future__ import annotations

import json
from typing import Any

from mcp_doctor.models import DiagnosticReport


def render_json(report: DiagnosticReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False)


def render_text(report: DiagnosticReport) -> str:
    line = "━" * 70
    parts = [
        line,
        f"MCP-DOCTOR  v{report.tool_version}",
        f"Target   : {report.target}",
        f"Transport: {report.transport}",
        f"Status   : {report.status.upper().replace('_', ' ')}",
        line,
    ]
    if report.protocol_version:
        parts.append(f"Protocol : {report.protocol_version}")
    if report.server_info:
        name = report.server_info.get("name", "unknown")
        version = report.server_info.get("version", "unknown")
        parts.append(f"Server   : {name} ({version})")
    if report.tools:
        parts.append(f"Tools    : {len(report.tools)} advertised")
        for tool in report.tools[:12]:
            description = str(tool.get("description", "")).replace("\n", " ").strip()
            tail = f" — {description[:90]}" if description else ""
            parts.append(f"  • {tool.get('name', '<unnamed>')}{tail}")
        if len(report.tools) > 12:
            parts.append(f"  … and {len(report.tools) - 12} more")
    parts.append(line)
    for finding in report.findings:
        marker = {"error": "✖", "warning": "!", "info": "i", "pass": "✓"}.get(finding.severity, "·")
        parts.append(f"{marker} [{finding.severity.upper():7}] {finding.rule_id} · {finding.title}")
        parts.append(f"  {finding.message}")
        if finding.evidence:
            safe_evidence = ", ".join(f"{key}={value}" for key, value in finding.evidence.items())
            parts.append(f"  Evidence: {safe_evidence}")
        parts.append(f"  Next: {finding.next_step}")
    parts.extend([
        line,
        f"Summary: {report.errors} error(s), {report.warnings} warning(s), {report.passed} passed check(s)",
    ])
    if report.duration_ms is not None:
        parts.append(f"Duration: {report.duration_ms} ms")
    parts.append(line)
    return "\n".join(parts)


def stable_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Small helper for tests and automation consumers."""
    return {
        "status": data.get("status"),
        "summary": data.get("summary", {}),
        "target": data.get("target"),
    }
