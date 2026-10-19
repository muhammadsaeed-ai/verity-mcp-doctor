"""Bounded subprocess and JSON-RPC helpers for local MCP stdio servers.

Only the explicit `check` command calls this module. Config validation never
starts a configured executable. stdout is treated strictly as the MCP wire;
stderr is drained separately and is never copied into report evidence.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from mcp_doctor.config import ServerConfig
from mcp_doctor.models import Finding
from mcp_doctor.redact import scrub

LATEST_PROTOCOL = "2026-07-28"
LEGACY_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
CLIENT_INFO = {"name": "MCP-Doctor", "version": "0.2.0"}
_META_VERSION = "io.modelcontextprotocol/protocolVersion"
_META_CLIENT = "io.modelcontextprotocol/clientInfo"
_META_CAPABILITIES = "io.modelcontextprotocol/clientCapabilities"
_META_SERVER = "io.modelcontextprotocol/serverInfo"
_END = object()\n_OVERSIZE = object()


@dataclass
class ProbeResult:
    protocol_version: str | None = None
    server_info: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    tools: list[dict[str, Any]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    stderr_bytes: int = 0
    duration_ms: int = 0


def _finding(rule: str, severity: str, title: str, message: str, next_step: str, **evidence: Any) -> Finding:
    return Finding(rule, severity, title, message, next_step, "protocol", evidence)


class StdioProcess:
    """Run a configured stdio server and read lines without blocking past timeout."""

    def __init__(self, config: ServerConfig, max_message_bytes: int = 1_048_576):
        self.config = config
        self.max_message_bytes = max_message_bytes
        env = os.environ.copy()
        env.update(config.env)
        cwd = config.cwd or None
        self.process = subprocess.Popen(
            [config.command, *config.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=cwd,
            env=env,
            shell=False,
        )
        self.stdout_queue: queue.Queue[Any] = queue.Queue(maxsize=64)
        self.stderr_bytes = 0
        self._stderr_lock = threading.Lock()
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()
        self._request_id = 0
        self.unmatched_messages = 0

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        try:
            while True:
                line = self.process.stdout.readline(self.max_message_bytes + 2)
                if not line:
                    break
                if len(line.encode("utf-8", errors="replace")) > self.max_message_bytes:
                    self.stdout_queue.put(_OVERSIZE)
                    return
                self.stdout_queue.put(line)
        except (OSError, ValueError):
            pass
        finally:
            self.stdout_queue.put(_END)

    def _read_stderr(self) -> None:
        assert self.process.stderr is not None
        try:
            while True:
                chunk = self.process.stderr.read(4096)
                if not chunk:
                    break
                with self._stderr_lock:
                    self.stderr_bytes += len(chunk.encode("utf-8", errors="replace"))
        except (OSError, ValueError):
            return

    def send(self, message: dict[str, Any]) -> None:
        if self.process.poll() is not None:
            raise BrokenPipeError("MCP server process exited")
        assert self.process.stdin is not None
        encoded = json.dumps(message, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > self.max_message_bytes:
            raise ValueError("outbound message exceeds configured byte limit")
        self.process.stdin.write(encoded + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
        self._request_id += 1
        request_id = self._request_id
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"timed out waiting for response to {method}")
            try:
                entry = self.stdout_queue.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError(f"timed out waiting for response to {method}") from exc
            if entry is _END:
                raise EOFError("server closed stdout before replying")
            if entry is _OVERSIZE:
                raise OverflowError("server stdout message exceeds configured byte limit")
            if len(entry.encode("utf-8", errors="replace")) > self.max_message_bytes:
                raise OverflowError("server stdout message exceeds configured byte limit")
            try:
                message_obj = json.loads(entry)
            except json.JSONDecodeError as exc:
                raise ValueError(f"server stdout contained non-JSON text (line length {len(entry)})") from exc
            if not isinstance(message_obj, dict) or message_obj.get("jsonrpc") != "2.0":
                raise ValueError("server stdout contained an invalid JSON-RPC envelope")
            if message_obj.get("id") != request_id:
                # Notifications and server-initiated requests are out of scope for
                # a read-only doctor probe. Ignore them, but bound the counter.
                self.unmatched_messages += 1
                if self.unmatched_messages > 100:
                    raise ValueError("too many unrelated messages arrived during the diagnostic probe")
                continue
            if "error" in message_obj:
                error = message_obj["error"]
                if not isinstance(error, dict):
                    raise ValueError("server returned a malformed JSON-RPC error object")
                raise RpcError(error)
            result = message_obj.get("result")
            if not isinstance(result, dict):
                raise ValueError("server response did not contain an object result")
            return result

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
            except (OSError, ValueError):
                pass
            self.process.terminate()
            try:
                self.process.wait(timeout=0.7)
            except subprocess.TimeoutExpired:
                self.process.kill()
                try:
                    self.process.wait(timeout=0.7)
                except subprocess.TimeoutExpired:
                    pass
        self._stdout_thread.join(timeout=0.2)
        self._stderr_thread.join(timeout=0.2)


class RpcError(Exception):
    def __init__(self, error: dict[str, Any]):
        self.error = error
        self.code = error.get("code")
        self.message = scrub(str(error.get("message", "Unknown JSON-RPC error")), 240)
        super().__init__(f"JSON-RPC error {self.code}: {self.message}")


def _safe_server_info(value: Any) -> dict[str, Any]:
    """Keep only standard, bounded identity fields from an untrusted server."""
    if not isinstance(value, dict):
        return {}
    safe: dict[str, Any] = {}
    for key in ("name", "version", "title", "websiteUrl"):
        field = value.get(key)
        if isinstance(field, str):
            safe[key] = scrub(field, 120)
    return safe


def _safe_capabilities(value: Any) -> dict[str, Any]:
    """Report only which capability groups are advertised, not arbitrary payloads."""
    if not isinstance(value, dict):
        return {}
    return {scrub(str(key), 80): {"advertised": True} for key in list(value.keys())[:30]}


def _modern_meta(version: str) -> dict[str, Any]:
    return {
        _META_VERSION: version,
        _META_CLIENT: CLIENT_INFO,
        _META_CAPABILITIES: {},
    }


def _validate_tools(result: dict[str, Any]) -> tuple[list[dict[str, Any]], list[Finding]]:
    findings: list[Finding] = []
    if result.get("resultType", "complete") != "complete":
        return [], [_finding(
            "MCPD-PROTO-012", "error", "Tool listing did not complete",
            "The server returned a non-complete result for tools/list.",
            "Inspect the server implementation and any protocol extension requiring additional client input.",
        )]
    raw_tools = result.get("tools")
    if not isinstance(raw_tools, list):
        return [], [_finding(
            "MCPD-PROTO-013", "error", "Invalid tools/list result",
            "The response is missing a tools array.",
            "Check that the server implements tools/list according to its advertised protocol version.",
        )]
    tools: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, tool in enumerate(raw_tools):
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str) or not tool["name"].strip():
            findings.append(_finding(
                "MCPD-PROTO-014", "error", "Malformed tool entry",
                f"tools/list entry {index} does not contain a non-empty string name.",
                "Fix the server's tools/list schema and return valid tool definitions.",
                entry_index=index,
            ))
            continue
        name = tool["name"]
        if name in seen:
            findings.append(_finding(
                "MCPD-PROTO-015", "warning", "Duplicate tool name",
                f"The server advertised the tool name {scrub(name, 100)!r} more than once.",
                "Give each advertised tool a unique name.",
                tool_name=scrub(name, 100),
            ))
        seen.add(name)
        schema = tool.get("inputSchema")
        if schema is not None and (not isinstance(schema, dict) or schema.get("type", "object") != "object"):
            findings.append(_finding(
                "MCPD-PROTO-016", "warning", "Unusual tool input schema",
                f"Tool {scrub(name, 100)!r} has an inputSchema that is not a JSON Schema object.",
                "Return an object-shaped JSON Schema for tool input. This check does not validate every JSON Schema keyword.",
                tool_name=scrub(name, 100),
            ))
        # Report only descriptive metadata; never call tools/call.
        tools.append({
            "name": scrub(name, 100),
            "title": scrub(str(tool.get("title", "")), 120),
            "description": scrub(str(tool.get("description", "")), 300),
            "has_input_schema": isinstance(schema, dict),
        })
    findings.append(_finding(
        "MCPD-PROTO-TOOLS", "pass", "Tool discovery succeeded",
        f"The server advertised {len(raw_tools)} tool definition(s); no tool was executed.",
        "Review tool names and schemas in the report. MCP-Doctor intentionally does not call tools/call.",
        tool_count=len(raw_tools),
    ))
    if not findings:
        findings.append(_finding("MCPD-PROTO-TOOLS", "pass", "Tool discovery succeeded",
                                 f"The server advertised {len(tools)} tool definition(s).",
                                 "Review the returned tool list before using this server.", tool_count=len(tools)))
    return tools, findings


def probe_stdio(config: ServerConfig, timeout: float = 5.0, max_message_bytes: int = 1_048_576) -> ProbeResult:
    """Run a read-only MCP handshake/discovery and tools/list probe over stdio."""
    started = time.monotonic()
    report = ProbeResult()
    session: StdioProcess | None = None
    try:
        session = StdioProcess(config, max_message_bytes=max_message_bytes)
        report.findings.append(_finding(
            "MCPD-PROC-001", "pass", "Server process started",
            "The configured process started successfully with shell execution disabled.",
            "Continue with the MCP protocol probe.", command=PathName(config.command),
        ))

        modern_version: str | None = None
        discovery: dict[str, Any] | None = None
        try:
            discovery = session.request("server/discover", {"_meta": _modern_meta(LATEST_PROTOCOL)}, timeout)
            supported = discovery.get("supportedVersions")
            if isinstance(supported, list) and LATEST_PROTOCOL in supported:
                modern_version = LATEST_PROTOCOL
                report.protocol_version = LATEST_PROTOCOL
                report.capabilities = _safe_capabilities(discovery.get("capabilities", {}))
                meta = discovery.get("_meta", {})
                server_meta = meta.get(_META_SERVER, {}) if isinstance(meta, dict) else {}
                report.server_info = _safe_server_info(server_meta)
                report.findings.append(_finding(
                    "MCPD-PROTO-001", "pass", "Modern MCP discovery succeeded",
                    "server/discover returned a valid capability and version document.",
                    "Proceed to a read-only tools/list check.", protocol_version=LATEST_PROTOCOL,
                ))
            elif isinstance(supported, list) and any(v in LEGACY_PROTOCOLS for v in supported):
                report.findings.append(_finding(
                    "MCPD-PROTO-002", "info", "Server advertises a legacy protocol version",
                    "Discovery indicates that the server does not advertise this release's modern protocol version.",
                    "MCP-Doctor will try the legacy initialize handshake.", supported_versions=supported,
                ))
            else:
                report.findings.append(_finding(
                    "MCPD-PROTO-003", "warning", "Unrecognized discovery response",
                    "The server responded to server/discover, but its supportedVersions field did not contain a known compatible version.",
                    "Review the server's protocol implementation and supported versions.",
                ))
        except RpcError as exc:
            if exc.code != -32601 and "method not found" not in exc.message.lower():
                report.findings.append(_finding(
                    "MCPD-PROTO-004", "info", "Modern discovery was rejected",
                    f"server/discover returned a JSON-RPC error ({exc.code}); trying legacy compatibility.",
                    "The following legacy handshake will determine whether this is an older server.",
                    rpc_code=exc.code,
                ))
        except TimeoutError:
            report.findings.append(_finding(
                "MCPD-PROTO-005", "warning", "Modern discovery timed out",
                f"No response to server/discover arrived within {timeout:g} second(s).",
                "MCP-Doctor will try the legacy handshake; also check server startup and stdout discipline.",
                timeout_seconds=timeout,
            ))

        if modern_version is not None:
            result = session.request("tools/list", {"_meta": _modern_meta(modern_version)}, timeout)
            report.tools, tool_findings = _validate_tools(result)
            report.findings.extend(tool_findings)
        else:
            init_result: dict[str, Any] | None = None
            last_error: Exception | None = None
            for version in LEGACY_PROTOCOLS:
                try:
                    init_result = session.request("initialize", {
                        "protocolVersion": version,
                        "capabilities": {},
                        "clientInfo": CLIENT_INFO,
                    }, timeout)
                    negotiated = init_result.get("protocolVersion")
                    if not isinstance(negotiated, str):
                        raise ValueError("initialize response has no protocolVersion string")
                    report.protocol_version = negotiated
                    report.server_info = _safe_server_info(init_result.get("serverInfo", {}))
                    report.capabilities = _safe_capabilities(init_result.get("capabilities", {}))
                    break
                except RpcError as exc:
                    last_error = exc
                    continue
                except (TimeoutError, EOFError, ValueError, BrokenPipeError) as exc:
                    last_error = exc
                    break

            if init_result is None:
                raise RuntimeError(f"neither modern discovery nor legacy initialization succeeded ({type(last_error).__name__ if last_error else 'no compatible response'})")
            if report.protocol_version not in LEGACY_PROTOCOLS:
                report.findings.append(_finding(
                    "MCPD-PROTO-006", "warning", "Server negotiated an unrecognized legacy version",
                    "The initialize response selected a version outside MCP-Doctor's known legacy compatibility set.",
                    "Verify version compatibility against the MCP specification.", protocol_version=report.protocol_version,
                ))
            else:
                report.findings.append(_finding(
                    "MCPD-PROTO-007", "pass", "Legacy MCP initialization succeeded",
                    "The server completed the initialize handshake.",
                    "The probe will list tools without invoking them.", protocol_version=report.protocol_version,
                ))
            session.notify("notifications/initialized")
            result = session.request("tools/list", None, timeout)
            report.tools, tool_findings = _validate_tools(result)
            report.findings.extend(tool_findings)

    except subprocess.TimeoutExpired:
        report.findings.append(_finding(
            "MCPD-PROC-002", "error", "Server shutdown timed out",
            "The server did not stop within the cleanup deadline.",
            "Check for child processes and lifecycle bugs in the server.",
        ))
    except FileNotFoundError:
        report.findings.append(_finding(
            "MCPD-PROC-003", "error", "Server executable not found",
            "The configured executable could not be started.",
            "Check the executable path and ensure the runtime is installed.",
        ))
    except PermissionError:
        report.findings.append(_finding(
            "MCPD-PROC-004", "error", "Server executable is not permitted",
            "The operating system denied permission to start the configured executable.",
            "Check file permissions, execution policy, and security software.",
        ))
    except TimeoutError as exc:
        report.findings.append(_finding(
            "MCPD-PROTO-008", "error", "MCP response timed out",
            scrub(str(exc), 240),
            "Check that the server writes newline-delimited JSON-RPC to stdout and increase --timeout only if startup legitimately takes longer.",
            timeout_seconds=timeout,
        ))
    except OverflowError:
        report.findings.append(_finding(
            "MCPD-PROTO-009", "error", "Protocol message exceeded size limit",
            f"The server emitted a stdout message larger than {max_message_bytes} bytes.",
            "Fix the server's stdout protocol output or use an appropriate bounded size limit.",
            limit_bytes=max_message_bytes,
        ))
    except EOFError:
        report.findings.append(_finding(
            "MCPD-PROTO-010", "error", "Server exited before responding",
            "The server closed stdout before sending the requested response.",
            "Launch the configured command manually in a trusted terminal and inspect startup diagnostics on stderr.",
        ))
    except (ValueError, BrokenPipeError) as exc:
        report.findings.append(_finding(
            "MCPD-PROTO-011", "error", "Invalid stdio protocol response",
            scrub(str(exc), 240),
            "The server must emit one valid JSON-RPC message per line on stdout; send logs to stderr.",
        ))
    except RpcError as exc:
        report.findings.append(_finding(
            "MCPD-PROTO-018", "error", "MCP request failed",
            f"The server returned JSON-RPC error {exc.code}: {scrub(exc.message, 220)}",
            "Check protocol compatibility and the server's implementation of the requested method.",
            rpc_code=exc.code,
        ))
    except RuntimeError as exc:
        report.findings.append(_finding(
            "MCPD-PROTO-019", "error", "MCP protocol handshake failed",
            scrub(str(exc), 240),
            "Verify that the selected process is an MCP server using stdio transport.",
        ))
    except OSError as exc:
        report.findings.append(_finding(
            "MCPD-PROC-005", "error", "Could not start the server process",
            f"The operating system returned {type(exc).__name__}.",
            "Review the command path, working directory, and permission settings.",
        ))
    finally:
        if session is not None:
            session.close()
            report.stderr_bytes = session.stderr_bytes
        report.duration_ms = int((time.monotonic() - started) * 1000)
    if report.stderr_bytes > 0:
        report.findings.append(_finding(
            "MCPD-PROC-STDERR", "info", "Server wrote startup or runtime diagnostics to stderr",
            f"The server wrote {report.stderr_bytes} byte(s) to stderr. Stderr output is normal and was not included in the report.",
            "Inspect stderr locally if the server failed; review it for secrets before sharing.",
            stderr_bytes=report.stderr_bytes,
        ))
    return report


def PathName(path: str) -> str:
    """Return only the executable basename for the human-facing report."""
    return path.replace("\\", "/").rsplit("/", 1)[-1][:100]
