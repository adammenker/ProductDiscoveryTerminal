from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_runtime_security(settings: Any) -> None:
    if str(settings.app_env).lower() != "production":
        return

    if not settings.allow_public_unauthenticated:
        raise RuntimeError(
            "APP_ENV=production requires deployment-layer authentication or an explicit "
            "ALLOW_PUBLIC_UNAUTHENTICATED=true acknowledgement for this private internal tool."
        )

    public_url = str(settings.public_app_url or "").strip()
    if not public_url:
        logger.warning("APP_ENV=production is set without PUBLIC_APP_URL; HTTPS cannot be verified.")
    elif not public_url.startswith("https://"):
        logger.warning("APP_ENV=production should use an HTTPS PUBLIC_APP_URL.")

