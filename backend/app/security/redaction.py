from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

REDACTED = "<redacted>"

SENSITIVE_KEY_PARTS = (
    "token",
    "secret",
    "password",
    "refresh_token",
    "access_token",
    "client_secret",
    "authorization",
    "x-amz-access-token",
)

TOKEN_PATTERNS = (
    re.compile(r"Atz[ar]\|[A-Za-z0-9_.\-=|]+"),
    re.compile(r"amzn1\.oa2-cs\.[A-Za-z0-9_.\-]+"),
)

KEY_VALUE_PATTERN = re.compile(
    r"(?i)\b(token|secret|password|refresh_token|access_token|client_secret|authorization|x-amz-access-token)"
    r"([\"'\s:=]+)"
    r"([^,\s\"'}]+)"
)


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if _is_sensitive_key(key_text):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").lower()
    return any(part.replace("-", "_") in normalized for part in SENSITIVE_KEY_PARTS)


def _redact_string(value: str) -> str:
    redacted = KEY_VALUE_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", value)
    for pattern in TOKEN_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return redacted


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_sensitive(record.msg)
        if record.args:
            record.args = redact_sensitive(record.args)
        return True

