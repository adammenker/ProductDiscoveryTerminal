from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import *  # noqa: F403

INTEGRATION_ENV_KEYS = (
    "AMAZON_SP_API_ENABLED",
    "AMAZON_SP_API_ENV",
    "AMAZON_SP_API_ENVIRONMENT",
    "AMAZON_SP_API_ENDPOINT",
    "AMAZON_LWA_CLIENT_ID",
    "AMAZON_LWA_CLIENT_SECRET",
    "AMAZON_LWA_REFRESH_TOKEN",
    "AMAZON_REFRESH_TOKEN",
    "ETSY_API_ENABLED",
    "ETSY_API_KEYSTRING",
    "ETSY_SHARED_SECRET",
    "ALIBABA_API_ENABLED",
    "ALIBABA_APP_KEY",
    "ALIBABA_APP_SECRET",
    "ALIBABA_ACCESS_TOKEN",
)


@pytest.fixture(autouse=True)
def isolate_test_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    live_connectivity_test = os.getenv("AMAZON_SP_API_CONNECTIVITY_TEST") == "1"
    for key in INTEGRATION_ENV_KEYS:
        if not live_connectivity_test or not key.startswith("AMAZON_"):
            monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:  # type: ignore[no-untyped-def]
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.state.disable_discovery_recovery = True
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    app.state.disable_discovery_recovery = False
