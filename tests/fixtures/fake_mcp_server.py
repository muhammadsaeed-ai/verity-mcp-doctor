"""Tiny deterministic MCP test server; never executes tools/call."""
import json
import os
import sys

MODE = os.environ.get("FAKE_MCP_MODE", "modern")


def reply(message_id, result=None, error=None):
    packet = {"jsonrpc": "2.0", "id": message_id}
    packet["error" if error is not None else "result"] = error if error is not None else result
    sys.stdout.write(json.dumps(packet, separators=(",", ":")) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        continue
    method = message.get("method")
    message_id = message.get("id")
    if method == "server/discover":
        if MODE == "legacy":
            reply(message_id, error={"code": -32601, "message": "Method not found"})
        else:
            reply(message_id, {
                "resultType": "complete",
                "supportedVersions": ["2026-07-28"],
                "capabilities": {"tools": {}},
                "_meta": {"io.modelcontextprotocol/serverInfo": {"name": "fixture-server", "version": "1.0.0"}}
            })
    elif method == "initialize":
        reply(message_id, {
            "protocolVersion": message.get("params", {}).get("protocolVersion", "2025-11-25"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "fixture-server", "version": "1.0.0"}
        })
    elif method == "tools/list":
        result = {"tools": [
            {"name": "echo", "description": "Test fixture tool", "inputSchema": {"type": "object", "properties": {}}}
        ]}
        if MODE != "legacy":
            result["resultType"] = "complete"
        reply(message_id, result)
    else:
        if message_id is not None:
            reply(message_id, error={"code": -32601, "message": "Method not found"})
