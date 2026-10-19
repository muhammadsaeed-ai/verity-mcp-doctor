# Diagnostic rule catalogue

Findings use stable rule IDs, a severity (`error`, `warning`, `info`, or `pass`), a short title, observed evidence when safe to include, and a next step. The report schema is versioned separately from individual rule IDs.

## Configuration and process

| Rule | Meaning |
| --- | --- |
| `MCPD-CFG-001`–`005` | File read, JSON syntax, root shape, or no server definitions |
| `MCPD-CFG-006`–`011` | Invalid server entry, command, args, env, or working directory |
| `MCPD-CFG-012` | Unresolved environment placeholders |
| `MCPD-CFG-013`–`015` | Executable or working-directory resolution failed |
| `MCPD-CFG-016`–`018` | No checkable server, selection required, or selected name not found |
| `MCPD-CFG-HTTP-001` | Remote URL transport is outside this release's scope |
| `MCPD-PROC-001` | Server process started |
| `MCPD-PROC-003`–`005` | Process start, permission, or operating-system failure |
| `MCPD-PROC-STDERR` | Server emitted stderr; this alone is not a failure |

## Protocol and tool catalogue

| Rule | Meaning |
| --- | --- |
| `MCPD-PROTO-001` | Modern discovery succeeded |
| `MCPD-PROTO-002`–`005` | Legacy/unknown discovery compatibility conditions |
| `MCPD-PROTO-006`–`007` | Legacy version warning or successful initialization |
| `MCPD-PROTO-008`–`011` | Timeout, message-size, early-exit, or JSON-RPC envelope failure |
| `MCPD-PROTO-012`–`016` | tools/list result, entry name, duplicates, or schema warning |
| `MCPD-PROTO-018`–`019` | JSON-RPC request error or protocol handshake failure |

The catalogue summarizes the current implementation. Exact text and evidence fields are intended to remain useful for operators, not as a substitute for a full schema validator or security audit.
