import json
import sys
from pathlib import Path

from mcp_doctor.diagnostics import check_file


FIXTURE_SERVER = Path(__file__).parent / "fixtures" / "fake_mcp_server.py"


def make_config(tmp_path: Path, mode: str) -> Path:
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({
        "mcpServers": {
            "fixture": {
                "command": sys.executable,
                "args": ["-u", str(FIXTURE_SERVER)],
                "env": {"FAKE_MCP_MODE": mode}
            }
        }
    }), encoding="utf-8")
    return config


def test_modern_discovery_and_tools_list(tmp_path: Path) -> None:
    report = check_file(make_config(tmp_path, "modern"), server_name="fixture", timeout=1.5)

    assert report.exit_code == 0, [f.to_dict() for f in report.findings]
    assert report.protocol_version == "2026-07-28"
    assert report.server_info["name"] == "fixture-server"
    assert [tool["name"] for tool in report.tools] == ["echo"]
    assert any(item.rule_id == "MCPD-PROTO-001" for item in report.findings)
    assert not any(item.rule_id == "MCPD-PROTO-018" for item in report.findings)


def test_legacy_initialize_fallback(tmp_path: Path) -> None:
    report = check_file(make_config(tmp_path, "legacy"), server_name="fixture", timeout=1.5)

    assert report.exit_code == 0, [f.to_dict() for f in report.findings]
    assert report.protocol_version in {"2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"}
    assert report.server_info["name"] == "fixture-server"
    assert [tool["name"] for tool in report.tools] == ["echo"]


def test_multiple_servers_require_explicit_selection(tmp_path: Path) -> None:
    config = make_config(tmp_path, "modern")
    obj = json.loads(config.read_text(encoding="utf-8"))
    obj["mcpServers"]["second"] = dict(obj["mcpServers"]["fixture"])
    config.write_text(json.dumps(obj), encoding="utf-8")

    report = check_file(config, timeout=1)

    assert report.exit_code == 1
    assert any(item.rule_id == "MCPD-CFG-017" for item in report.findings)


def test_unknown_server_does_not_execute_any_command(tmp_path: Path) -> None:
    report = check_file(make_config(tmp_path, "modern"), server_name="missing", timeout=1)

    assert report.exit_code == 1
    assert any(item.rule_id == "MCPD-CFG-018" for item in report.findings)
