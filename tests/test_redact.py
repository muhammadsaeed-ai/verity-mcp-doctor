"""Regression tests for redaction of credential-like diagnostic text."""

from mcp_doctor.redact import scrub


def test_scrub_masks_generic_token_and_jwt_assignments() -> None:
    raw = "token=opaque-token-value id_token:private-id api_token=opaque-api jwt=compact-jwt"
    result = scrub(raw)
    for secret in ("opaque-token-value", "private-id", "opaque-api", "compact-jwt"):
        assert secret not in result
    assert result.count("<redacted>") == 4


def test_scrub_preserves_unrelated_metadata() -> None:
    assert scrub("region=eu-west name=worker") == "region=eu-west name=worker"
