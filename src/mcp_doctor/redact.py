"""Best-effort secret scrubbing for diagnostic evidence and error messages."""
from __future__ import annotations

import re

_REDACTED = "<redacted>"
_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|authorization|bearer|private[_-]?key)\b\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)(\bBearer\s+)([A-Za-z0-9._~+/=-]{8,})"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
)

def scrub(value: str, limit: int = 500) -> str:
    """Scrub recognizable secret patterns and cap text before adding to reports."""
    result = _PATTERNS[0].sub(lambda m: m.group(1) + _REDACTED, value)
    result = _PATTERNS[1].sub(lambda m: m.group(1) + _REDACTED, result)
    for pattern in _PATTERNS[2:]:
        result = pattern.sub(_REDACTED, result)
    # Remove ANSI terminal control sequences and control characters from
    # untrusted server-provided strings before they reach the console.
    result = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result)
    result = re.sub(r"[\x00-\x1f\x7f]", " ", result)
    return result if len(result) <= limit else result[:limit] + "…"
