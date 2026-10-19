"""Parse common MCP client JSON configuration without executing configured commands."""
from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp_doctor.models import Finding
from mcp_doctor.redact import scrub

_ENV_TOKEN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass
class ServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    source_path: str = ""

    def expanded(self, environ: dict[str, str] | None = None) -> tuple["ServerConfig", list[str]]:
        values = os.environ if environ is None else environ
        missing: list[str] = []

        def replace(value: str) -> str:
            def repl(match: re.Match[str]) -> str:
                key = match.group(1)
                if key not in values:
                    missing.append(key)
                    return match.group(0)
                return values[key]
            return _ENV_TOKEN.sub(repl, value)

        return ServerConfig(
            name=self.name,
            command=replace(self.command),
            args=[replace(arg) for arg in self.args],
            env={key: replace(value) for key, value in self.env.items()},
            cwd=replace(self.cwd) if self.cwd else None,
            source_path=self.source_path,
        ), sorted(set(missing))


@dataclass
class ConfigLoad:
    path: Path
    servers: dict[str, ServerConfig] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)


def _finding(rule: str, severity: str, title: str, message: str, next_step: str, **evidence: Any) -> Finding:
    return Finding(rule, severity, title, message, next_step, "configuration", evidence)


def load_config(path: str | Path) -> ConfigLoad:
    config_path = Path(path).expanduser()
    result = ConfigLoad(path=config_path)
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        result.findings.append(_finding(
            "MCPD-CFG-001", "error", "Configuration file not found",
            f"No configuration file named {config_path.name!r} exists.",
            "Check the path and try again.",
        ))
        return result
    except OSError as exc:
        result.findings.append(_finding(
            "MCPD-CFG-002", "error", "Configuration file cannot be read",
            f"The file could not be read ({type(exc).__name__}).",
            "Check the file permissions and encoding.",
        ))
        return result

    try:
        root = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        result.findings.append(_finding(
            "MCPD-CFG-003", "error", "Invalid JSON",
            f"The configuration is not valid JSON (line {exc.lineno}, column {exc.colno}).",
            "Fix the JSON syntax, then rerun validation.",
            line=exc.lineno, column=exc.colno,
        ))
        return result

    if not isinstance(root, dict):
        result.findings.append(_finding(
            "MCPD-CFG-004", "error", "Configuration root must be an object",
            "Expected a JSON object at the top level.",
            'Use a top-level object containing an "mcpServers" object.',
        ))
        return result

    servers_value = root.get("mcpServers")
    if servers_value is None and isinstance(root.get("servers"), dict):
        servers_value = root["servers"]
    if servers_value is None and "command" in root:
        servers_value = {"default": root}
    if not isinstance(servers_value, dict) or not servers_value:
        result.findings.append(_finding(
            "MCPD-CFG-005", "error", "No MCP servers found",
            'No server entries were found. Expected an "mcpServers" object with named server definitions.',
            "Select an MCP client config containing server definitions, or provide one server object with a command.",
        ))
        return result

    for name, entry in servers_value.items():
        if not isinstance(name, str) or not name.strip():
            result.findings.append(_finding(
                "MCPD-CFG-006", "error", "Invalid server name",
                "Server names must be non-empty strings.", "Give the server a short descriptive name.",
            ))
            continue
        if not isinstance(entry, dict):
            result.findings.append(_finding(
                "MCPD-CFG-007", "error", "Server entry must be an object",
                f"Server {scrub(name)} is not a JSON object.",
                "Define the server using command, args, and optional env fields.",
            ))
            continue

        if entry.get("url"):
            result.findings.append(_finding(
                "MCPD-CFG-HTTP-001", "error", "Remote URL transport is not implemented",
                f"Server {scrub(name)} uses a URL-based configuration. This release checks local stdio servers only.",
                "Use a local stdio server definition with command and args, or wait for remote HTTP transport support.",
                server=name, transport="url",
            ))
            continue

        command = entry.get("command")
        args = entry.get("args", [])
        env = entry.get("env", {})
        cwd = entry.get("cwd")

        invalid = False
        if not isinstance(command, str) or not command.strip():
            result.findings.append(_finding(
                "MCPD-CFG-008", "error", "Missing server command",
                f"Server {scrub(name)} must define a non-empty command.",
                "Add the executable name or absolute path in the server's command field.",
                server=name,
            ))
            invalid = True
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            result.findings.append(_finding(
                "MCPD-CFG-009", "error", "Invalid command arguments",
                f"Server {scrub(name)} args must be a list of strings.",
                'For example: "args": ["server.py", "--stdio"].', server=name,
            ))
            invalid = True
        if not isinstance(env, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()):
            result.findings.append(_finding(
                "MCPD-CFG-010", "error", "Invalid environment overrides",
                f"Server {scrub(name)} env must be an object containing string values.",
                "Use environment-variable names as keys and strings as values. Values are not printed by MCP-Doctor.",
                server=name,
            ))
            invalid = True
        if cwd is not None and not isinstance(cwd, str):
            result.findings.append(_finding(
                "MCPD-CFG-011", "error", "Invalid working directory",
                f"Server {scrub(name)} cwd must be a string when supplied.",
                "Set cwd to a directory path or remove the field.", server=name,
            ))
            invalid = True
        if invalid:
            continue

        result.servers[name] = ServerConfig(
            name=name,
            command=command,
            args=list(args),
            env=dict(env),
            cwd=cwd,
            source_path=str(config_path.resolve()),
        )

    if result.servers:
        result.findings.append(_finding(
            "MCPD-CFG-VALID", "pass", "Configuration structure is valid",
            f"Validated {len(result.servers)} stdio server definition(s); no configured command was executed.",
            "Run check for a selected server to perform a live protocol probe.",
            server_count=len(result.servers),
        ))
    return result


def validate_runtime_config(config: ServerConfig, environ: dict[str, str] | None = None) -> tuple[ServerConfig, list[Finding]]:
    findings: list[Finding] = []
    expanded, missing_env = config.expanded(environ)
    if missing_env:
        findings.append(_finding(
            "MCPD-CFG-012", "warning", "Environment placeholders are unresolved",
            "One or more environment placeholders refer to variables that are not set in the current environment.",
            "Set the missing variables in the terminal before running MCP-Doctor. Variable names are shown; values are never printed.",
            server=config.name, variable_names=missing_env,
        ))

    command = expanded.command
    candidate = Path(command).expanduser()
    executable: str | None
    if candidate.is_absolute() or candidate.parent != Path("."):
        executable = str(candidate.resolve()) if candidate.is_file() else None
    else:
        executable = shutil.which(command)

    if executable is None:
        findings.append(_finding(
            "MCPD-CFG-013", "error", "Server executable was not found",
            f"Command {scrub(command, 120)!r} could not be resolved on PATH or as a file path.",
            "Install the runtime, use an absolute executable path, or fix the command value in the MCP client config.",
            server=config.name,
        ))
    elif not os.path.isfile(executable):
        findings.append(_finding(
            "MCPD-CFG-014", "error", "Server command is not a file",
            "The resolved command does not point to a file.",
            "Check the executable path.", server=config.name,
        ))
    else:
        expanded.command = executable
        findings.append(_finding(
            "MCPD-CFG-EXEC", "pass", "Server executable resolved",
            "The configured executable resolves to a local file.",
            "Continue to the bounded stdio protocol probe.",
            server=config.name,
        ))

    if expanded.cwd:
        workdir = Path(expanded.cwd).expanduser()
        if not workdir.is_absolute():
            workdir = Path(config.source_path).parent / workdir
        if not workdir.is_dir():
            findings.append(_finding(
                "MCPD-CFG-015", "error", "Working directory does not exist",
                "The configured working directory is not an existing directory.",
                "Fix cwd or remove it to use the current working directory.",
                server=config.name,
            ))
        else:
            expanded.cwd = str(workdir.resolve())
    return expanded, findings
