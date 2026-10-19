# Configuration guide

MCP-Doctor reads JSON configuration files used by MCP client applications. It supports the common `mcpServers` object, a `servers` object, or a single server object containing `command`. It does not attempt to guess application-specific config locations: pass the file path explicitly.

## Example

```json
{
  "mcpServers": {
    "filesystem-local": {
      "command": "python",
      "args": ["-u", "/absolute/path/to/server.py"],
      "env": {
        "LOG_LEVEL": "warning",
        "SERVICE_TOKEN": "${SERVICE_TOKEN}"
      },
      "cwd": "/absolute/path/to/project"
    }
  }
}
```

The command must be a local executable. Arguments are passed as a list; MCP-Doctor does not concatenate the command and arguments into a shell string. Environment overrides are strings and are merged onto the current process environment.

## Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `command` | Yes | Executable name or path |
| `args` | No | Array of string arguments |
| `env` | No | Object of string environment overrides |
| `cwd` | No | Working directory for server launch |

Environment placeholders written as `${NAME}` are expanded from the current process environment. If a placeholder is unresolved, the report identifies the variable name, not its value.

## Commands that do and do not execute

```bash
mcp-doctor validate ./mcp.json   # reads JSON; does not execute commands
mcp-doctor servers ./mcp.json    # lists entries; does not execute commands
mcp-doctor check ./mcp.json      # starts one selected server; choose only trusted commands
```

When more than one checkable stdio server exists, select one explicitly:

```bash
mcp-doctor check ./mcp.json --server filesystem-local
```

## Current limitations

This release only probes local stdio servers. Configurations that specify a remote `url` are reported as unsupported rather than being treated as if they were checked. It does not interpret every vendor-specific configuration dialect, environment-file directive, or JSON-with-comments variant.
