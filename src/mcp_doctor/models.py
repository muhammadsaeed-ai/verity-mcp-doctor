"""Stable data models for machine-readable diagnostic reports."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["error", "warning", "info", "pass"]

@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    title: str
    message: str
    next_step: str
    area: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class DiagnosticReport:
    tool: str
    tool_version: str
    target: str
    transport: str = "stdio"
    protocol_version: str | None = None
    server_info: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    tools: list[dict[str, Any]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    started_at: str | None = None
    duration_ms: int | None = None

    @property
    def errors(self) -> int:
        return sum(item.severity == "error" for item in self.findings)

    @property
    def warnings(self) -> int:
        return sum(item.severity == "warning" for item in self.findings)

    @property
    def passed(self) -> int:
        return sum(item.severity == "pass" for item in self.findings)

    @property
    def status(self) -> str:
        if self.errors:
            return "failed"
        if self.warnings:
            return "passed_with_warnings"
        return "passed"

    @property
    def exit_code(self) -> int:
        return 1 if self.errors else 0

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "tool": self.tool,
            "tool_version": self.tool_version,
            "target": self.target,
            "transport": self.transport,
            "status": self.status,
            "summary": {"errors": self.errors, "warnings": self.warnings, "passed": self.passed, "total_findings": len(self.findings)},
            "protocol": {"version": self.protocol_version, "server_info": self.server_info, "capabilities": self.capabilities},
            "tools": self.tools,
            "timing": {"started_at": self.started_at, "duration_ms": self.duration_ms},
            "findings": [finding.to_dict() for finding in self.findings],
        }
