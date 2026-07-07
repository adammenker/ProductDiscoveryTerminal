from __future__ import annotations

import hashlib
import json

from app.schemas.plugin import RawObservationDTO


def observation_content_hash(dto: RawObservationDTO) -> str:
    payload = {
        "source": dto.source,
        "source_plugin": dto.source_plugin,
        "entity_type": dto.entity_type,
        "external_id": dto.external_id,
        "title": dto.title,
        "url": dto.url,
        "raw_text": dto.raw_text,
        "metrics": dto.metrics,
        "metadata": dto.metadata,
        "media_urls": dto.media_urls,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

