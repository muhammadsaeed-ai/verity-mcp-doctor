# Contributing to MCP-Doctor

Thanks for helping make MCP troubleshooting clearer and safer. Focused bug reports, realistic synthetic test cases, rule improvements, documentation, and cross-platform fixes are welcome.

## Development setup

Requires Python 3.10 or newer.

```bash
git clone https://github.com/muhammadsaeed-ai/MCP-Doctor.git
cd MCP-Doctor
python -m venv .venv
# Activate the environment for your shell, then:
python -m pip install -e ".[dev]"
pytest
ruff check src tests
```

## Contribution checklist

- Add a deterministic test for behavior changes.
- Keep all subprocess invocation shell-free and all protocol waits bounded.
- Do not add real API keys, customer configuration files, production server output, or captured secrets to fixtures.
- Do not copy raw stdout/stderr into a report; tests should assert against sanitized evidence.
- Never invoke `tools/call` as part of the default diagnostic probe.
- Distinguish checks that are implemented from planned work.
- Preserve stable rule IDs once users may rely on them in automation.

## Protocol compatibility

When changing protocol handling, document the MCP spec revision and test both the modern discovery flow and legacy initialization fallback using the included synthetic fixture. Do not require live external servers for unit tests.

## Pull requests

Explain the scenario, the observed result, and the expected result. Include the test output and note any platform limitations. See [SECURITY.md](SECURITY.md) before reporting a vulnerability.
