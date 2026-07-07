from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


def json_type():
    return JSON().with_variant(JSONB, "postgresql")

