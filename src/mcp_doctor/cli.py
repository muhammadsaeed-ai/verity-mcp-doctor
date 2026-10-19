"""Command-line interface for MCP-Doctor."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mcp_doctor import __version__
from mcp_doctor.diagnostics import check_file, list_servers, validate_file
from mcp_doctor.report import render_json, render_text


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not 0.1 <= number <= 120:
        raise argparse.ArgumentTypeError("must be between 0.1 and 120 seconds")
    return number


def _message_bytes(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if not 1024 <= number <= 10_485_760:
        raise argparse.ArgumentTypeError("must be between 1,024 and 10,485,760 bytes")
    return number


def _format_report(report, output_format: str) -> str:
    return render_json(report) if output_format == "json" else render_text(report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-doctor",
        description="Diagnose local Model Context Protocol (MCP) stdio servers with bounded, read-only probes.",
        epilog="Safety: validate and servers never execute configured commands. check starts the selected configured process but never invokes tools/call.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate config JSON and server-entry structure without running commands")
    validate.add_argument("config", help="Path to an MCP client JSON configuration file")
    validate.add_argument("--format", choices=("text", "json"), default="text")

    servers = sub.add_parser("servers", help="List configured local stdio servers without running them")
    servers.add_argument("config", help="Path to an MCP client JSON configuration file")
    servers.add_argument("--format", choices=("text", "json"), default="text")

    check = sub.add_parser("check", help="Start one configured server and run bounded MCP protocol checks")
    check.add_argument("config", help="Path to an MCP client JSON configuration file")
    check.add_argument("--server", help="Named server from mcpServers; required when multiple servers are configured")
    check.add_argument("--timeout", type=_positive_float, default=5.0, help="Per-request timeout in seconds (0.1–120; default: 5)")
    check.add_argument("--max-message-bytes", type=_message_bytes, default=1_048_576, help="Maximum JSON-RPC line size (default: 1048576)")
    check.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            report = validate_file(args.config)
            print(_format_report(report, args.format))
            return report.exit_code

        if args.command == "servers":
            report, servers = list_servers(args.config)
            if args.format == "json":
                print(json.dumps({"report": report.to_dict(), "servers": servers}, indent=2, sort_keys=True))
            else:
                print(f"MCP-Doctor · configured servers in {Path(args.config).name}")
                for server in servers:
                    print(f"  • {server['name']}  [{server['transport']}]  command={server['command']}")
                if not servers:
                    print("  No checkable local stdio servers found.")
                for finding in report.findings:
                    if finding.severity == "error":
                        print(f"  ✖ {finding.rule_id}: {finding.message}")
            return report.exit_code

        if args.command == "check":
            report = check_file(
                args.config,
                server_name=args.server,
                timeout=args.timeout,
                max_message_bytes=args.max_message_bytes,
            )
            print(_format_report(report, args.format))
            return report.exit_code
        parser.error("unknown command")
    except KeyboardInterrupt:
        print("MCP-Doctor interrupted.", file=sys.stderr)
        return 130
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
