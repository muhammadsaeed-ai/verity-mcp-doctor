# Architecture and design boundaries

![MCP-Doctor implementation architecture](../assets/readme/architecture.svg)

MCP-Doctor is a local command-line diagnostic utility. The package is split into five main responsibilities:

1. **Configuration** — parse JSON and validate known stdio server entry shapes. This path has no process-launch capability.
2. **Runtime config validation** — resolve environment placeholders, command names, and optional working directories.
3. **Stdio RPC session** — launch one selected process with `shell=False`, read newline-delimited JSON-RPC off stdout, drain stderr separately, cap message length, and use request deadlines.
4. **Protocol strategy** — try modern `server/discover` with the `2026-07-28` protocol revision, then use a known older `initialize` sequence when modern discovery is unavailable.
5. **Diagnostic findings** — normalize checks into rule IDs, severity, evidence, and next-step guidance for text and JSON renderers.

## Data flow

![MCP-Doctor workflow](../assets/readme/workflow.svg)

## Deliberately excluded

- Calling advertised tools or executing active probes.
- Remote HTTP / Streamable HTTP and SSE transports.
- Telemetry, hosted report uploads, or config auto-discovery.
- Arbitrary shell-string execution.
- Guaranteeing secret removal or synthesizing an exact bug reproduction.

See [CONFIGURATION.md](CONFIGURATION.md), [DIAGNOSTIC-RULES.md](DIAGNOSTIC-RULES.md), and [SECURITY.md](../SECURITY.md).
