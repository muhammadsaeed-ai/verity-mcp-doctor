# Security Policy

## Scope and threat model

MCP-Doctor accepts configuration for local programs and can launch a configured executable when the user explicitly runs `mcp-doctor check`. Treat configuration files as executable trust decisions. Only check servers you trust.

- `validate` and `servers` parse configuration and do **not** start server commands.
- `check` starts only the selected local stdio process, with `shell=False`, bounded message sizes, per-request timeouts, and separate stdout/stderr handling.
- MCP-Doctor lists tool definitions but does not send `tools/call`.
- Remote URL / HTTP transport diagnostics are not included in this release.
- Stderr and malformed stdout content are not copied into reports by default. Selected fields are scrubbed and length-limited.

## Important limitations

Secret detection is best-effort. It is not a security boundary and cannot guarantee every secret is removed from a tool description, exception message, configuration value, or server-produced field. Review reports before sharing them. Do not commit production MCP configs, tokens, private URLs, or customer data.

A malicious or buggy server can still consume resources before its response timeout, and platform process termination behavior varies. Run diagnostics with normal least-privilege permissions. Do not run untrusted server commands.

## Reporting a vulnerability

Please avoid posting exploit details or live secrets in public issues. Contact the repository owner through their GitHub profile with a minimal, sanitized reproduction. Include the affected version and expected impact. Response time is not guaranteed for this early-stage project.
