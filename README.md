# MCP-Doctor

<p align="center">
  <img src="assets/readme/progress-loop.gif" alt="Animated workflow indicator" width="420" />
</p>

<p align="center"><strong>A proposed diagnostic CLI for Model Context Protocol (MCP) server configurations and connection failures.</strong></p>
<p align="center">
  <a href="#what-it-is">Overview</a> · <a href="#visual-workflow">Workflow</a> · <a href="#diagnostic-scope">Diagnostic scope</a> · <a href="#roadmap">Roadmap</a>
</p>
<p align="center">
  <img alt="Stage: design proposal" src="https://img.shields.io/badge/stage-design%20proposal-7867FF?style=flat-square" />
  <img alt="Safety focus" src="https://img.shields.io/badge/design-safe%20diagnostics-0D9488?style=flat-square" />
  <img alt="Open source concept" src="https://img.shields.io/badge/project-open%20source%20concept-168AAD?style=flat-square" />
</p>

> **Project status: design-stage.** The repository currently contains a README concept only. The commands, protocol probes, and reports described below have not been implemented or released.

## What it is

MCP-Doctor is a proposed **Model Context Protocol (MCP) server troubleshooting tool**. Its goal is to help developers distinguish configuration problems, transport failures, protocol incompatibilities, and unexpected tool responses before debugging the application that consumes the server.

## Why it matters

An MCP client depends on several layers working together: configuration, process/transport startup, initialization, capability discovery, and valid responses. A useful doctor-style CLI should show which layer failed, capture the relevant evidence, and give a practical next check rather than merely reporting “connection failed.”

## Visual workflow

<p align="center"><img src="assets/readme/workflow.svg" alt="Proposed MCP-Doctor sequence: validate configuration, connect to the server, inspect protocol surface, and produce an evidence-based report." width="100%" /></p>

## Proposed architecture

<p align="center"><img src="assets/readme/architecture.svg" alt="Proposed MCP-Doctor architecture with input validation, transport probing, protocol checks, and structured diagnostic reporting." width="100%" /></p>

## Diagnostic scope

| Area | Planned check | Safety requirement |
|---|---|---|
| Configuration | Required fields, types, paths, and supported options | Never echo secret values into reports |
| Server startup | Process exit, stderr, and bounded startup timeout | Do not invoke untrusted commands without explicit user intent |
| Transport | Connection or stdio handshake issues for supported transports | Set timeouts; never hang indefinitely |
| Protocol handshake | Initialization response and capability shape | Validate schemas and handle malformed JSON-RPC gracefully |
| Tool discovery | Check the advertised tool list and response structure | Listing tools must not execute the tools |
| Active test calls | Optional, narrowly scoped probes if needed | Require explicit opt-in and explain potential side effects |
| Reporting | Stable finding IDs, observed evidence, and recommended next steps | Redact secrets and private paths where possible |

This table is a proposal. MCP transport support and checks must be defined against the protocol version and actual client/server behavior selected during implementation.

## Example of a future report

Illustrative only—not output from a working tool:

```text
[ERROR] MCP initialization did not complete before timeout
Rule: MCP_INITIALIZE_TIMEOUT
Evidence: transport=stdio; configured timeout=5s
Next step: Confirm the server command and arguments, then run it manually
in a trusted terminal to inspect startup output.
```

## Design principles

- **Read-only first:** configuration validation and capability listing should not execute tools.
- **Bounded diagnostics:** timeouts, output-size limits, and clear cancellation behavior.
- **Explainable findings:** every result includes a rule ID, evidence, and suggested next step.
- **Secret-aware output:** never print tokens, private URLs, or environment-variable values by default.
- **No hidden telemetry:** local diagnostics should not upload configs or responses.

## Roadmap

- [ ] Define supported MCP versions and transport scope.
- [ ] Add config parsing and schema validation with synthetic fixtures.
- [ ] Implement bounded initialization and tool-list checks.
- [ ] Create a test MCP server for deterministic pass/fail cases.
- [ ] Add human-readable and JSON report formats.
- [ ] Review every check for side effects and information disclosure.

## Contributing

Early contributions can improve the protocol test matrix, safe test-server fixtures, rule taxonomy, and examples of sanitized failure cases. Do not share API keys, production MCP configuration, or private server output in public issues.

## Search and GitHub topics

Suggested topics: `model-context-protocol`, `mcp`, `mcp-server`, `mcp-client`, `mcp-debugging`, `protocol-diagnostics`, `developer-tools`, `cli`, `ai-tools`, `open-source`.

These keywords describe intended project scope; no search-ranking outcome is guaranteed.
