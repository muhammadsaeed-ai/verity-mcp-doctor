# Changelog

## 0.2.0 — 2026-10-19

- Turned the original concept into a functioning Python CLI for local stdio MCP server diagnostics.
- Added no-execution configuration validation and server listing.
- Added modern `server/discover` support for MCP protocol version `2026-07-28` plus fallback to known legacy `initialize` protocol revisions.
- Added bounded request timeouts, JSON-RPC envelope checks, tool-list validation, stable diagnostic rule IDs, and JSON/text reports.
- Added secret-conscious diagnostic output, example configuration, synthetic protocol fixtures, multi-version CI, and explanatory README diagrams.
- Remote URL / Streamable HTTP probing and active tool calls remain intentionally unimplemented.

## 0.1.0

- Design-stage README and visual proposal only; no diagnostic implementation was present.
