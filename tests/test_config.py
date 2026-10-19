import json
from pathlib import Path

from mcp_doctor.config import load_config, validate_runtime_config


def test_valid_config_is_read_without_running_command(tmp_path: Path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({
        "mcpServers": {
            "demo": {
                "command": "not-a-real-command-that-should-not-run",
                "args": ["server.py"],
                "env": {"MODE": "test"}
            }
        }
    }), encoding="utf-8")

    loaded = load_config(config)

    assert loaded.valid
    assert list(loaded.servers) == ["demo"]
    assert any(item.rule_id == "MCPD-CFG-VALID" for item in loaded.findings)


def test_invalid_json_is_reported_without_echoing_file_contents(tmp_path: Path) -> None:
    config = tmp_path / "broken.json"
    config.write_text('{"mcpServers": {"x": ', encoding="utf-8")

    loaded = load_config(config)

    assert not loaded.valid
    finding = next(item for item in loaded.findings if item.rule_id == "MCPD-CFG-003")
    assert "line 1" in finding.message
    assert "mcpServers" not in finding.message


def test_rejects_invalid_args_and_env_shapes(tmp_path: Path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({
        "mcpServers": {"bad": {"command": "python", "args": "--server", "env": {"KEY": 1}}}
    }), encoding="utf-8")

    loaded = load_config(config)

    assert not loaded.valid
    assert "bad" not in loaded.servers
    rule_ids = {item.rule_id for item in loaded.findings}
    assert "MCPD-CFG-009" in rule_ids
    assert "MCPD-CFG-010" in rule_ids


def test_environment_expansion_reports_missing_variable_names(tmp_path: Path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({
        "mcpServers": {"demo": {"command": "python", "args": ["${MCP_DOCTOR_TEST_MISSING}"]}}
    }), encoding="utf-8")
    loaded = load_config(config)
    server = loaded.servers["demo"]
    expanded, missing = server.expanded(environ={})

    assert missing == ["MCP_DOCTOR_TEST_MISSING"]
    assert expanded.args == ["${MCP_DOCTOR_TEST_MISSING}"]


def test_runtime_validator_does_not_print_env_values() -> None:
    from mcp_doctor.config import ServerConfig

    config = ServerConfig(name="demo", command="mcp-doctor-does-not-exist", env={"API_KEY": "fixture-private-value"})
    _, findings = validate_runtime_config(config, environ={})
    rendered = " ".join(item.message for item in findings)
    assert "fixture-private-value" not in rendered
