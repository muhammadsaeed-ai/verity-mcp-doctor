"""Orchestrate configuration validation and safe, read-only stdio probes."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from mcp_doctor import __version__
from mcp_doctor.config import load_config, validate_runtime_config
from mcp_doctor.models import DiagnosticReport, Finding
from mcp_doctor.stdio import probe_stdio


def _finding(rule: str, severity: str, title: str, message: str, next_step: str, area: str = "configuration", **evidence) -> Finding:
    return Finding(rule, severity, title, message, next_step, area, evidence)


def validate_file(path: str | Path) -> DiagnosticReport:
    """Validate the configuration JSON and known server-entry shapes only."""
    started = time.monotonic()
    loaded = load_config(path)
    report = DiagnosticReport(
        tool="MCP-Doctor",
        tool_version=__version__,
        target=Path(path).name or "configuration",
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    report.findings.extend(loaded.findings)
    report.duration_ms = int((time.monotonic() - started) * 1000)
    return report


def check_file(
    path: str | Path,
    server_name: str | None = None,
    timeout: float = 5.0,
    max_message_bytes: int = 1_048_576,
) -> DiagnosticReport:
    """Validate configuration, then explicitly launch one server and probe it."""
    started = time.monotonic()
    loaded = load_config(path)
    target = server_name or (next(iter(loaded.servers)) if len(loaded.servers) == 1 else "not selected")
    report = DiagnosticReport(
        tool="MCP-Doctor",
        tool_version=__version__,
        target=target,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    report.findings.extend(loaded.findings)

    if any(item.severity == "error" for item in loaded.findings):
        report.duration_ms = int((time.monotonic() - started) * 1000)
        return report

    if not loaded.servers:
        report.add(_finding(
            "MCPD-CFG-016", "error", "No checkable stdio server is configured",
            "The file did not contain a local stdio server that this release can probe.",
            "Use an MCP client config with command and optional args/env fields. URL-based remote transport is not implemented.",
        ))
        report.duration_ms = int((time.monotonic() - started) * 1000)
        return report

    if server_name is None:
        if len(loaded.servers) != 1:
            report.add(_finding(
                "MCPD-CFG-017", "error", "Server selection is required",
                f"The configuration contains {len(loaded.servers)} checkable servers; none was selected.",
                "Rerun with --server followed by one of the listed server names.",
                server_names=sorted(loaded.servers),
            ))
            report.duration_ms = int((time.monotonic() - started) * 1000)
            return report
        config = next(iter(loaded.servers.values()))
    else:
        config = loaded.servers.get(server_name)
        if config is None:
            report.add(_finding(
                "MCPD-CFG-018", "error", "Selected server was not found",
                f"The requested server {server_name!r} is not a valid local stdio entry in this configuration.",
                "Use the servers command to list valid names; no command has been started.",
                server_names=sorted(loaded.servers),
            ))
            report.duration_ms = int((time.monotonic() - started) * 1000)
            return report

    report.target = config.name
    runtime_config, findings = validate_runtime_config(config)
    report.findings.extend(findings)
    if any(item.severity == "error" for item in findings):
        report.duration_ms = int((time.monotonic() - started) * 1000)
        return report

    probe = probe_stdio(runtime_config, timeout=timeout, max_message_bytes=max_message_bytes)
    report.transport = "stdio"
    report.protocol_version = probe.protocol_version
    report.server_info = probe.server_info
    report.capabilities = probe.capabilities
    report.tools = probe.tools
    report.findings.extend(probe.findings)
    report.duration_ms = int((time.monotonic() - started) * 1000)
    return report


def list_servers(path: str | Path) -> tuple[DiagnosticReport, list[dict[str, str]]]:
    loaded = load_config(path)
    report = DiagnosticReport(
        tool="MCP-Doctor",
        tool_version=__version__,
        target=Path(path).name or "configuration",
        started_at=datetime.now(timezone.utc).isoformat(),
        findings=list(loaded.findings),
    )
    entries = [
        {"name": server.name, "transport": "stdio", "command": Path(server.command).name}
        for server in loaded.servers.values()
    ]
    report.duration_ms = 0
    return report, entries
