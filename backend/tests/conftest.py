"""Shared test fixtures."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.database.database import Base, create_db_engine
from backend.app.database import models  # noqa: F401 - registers model metadata
from backend.app.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Provide isolated local paths for each test."""

    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        data_path=tmp_path / "data",
        models_path=tmp_path / "models",
        storage_path=tmp_path / "storage",
        chroma_path=tmp_path / "chroma",
    )


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    """Create a test client and exercise the application lifespan."""

    test_engine = create_db_engine(test_settings.database_url)
    Base.metadata.create_all(test_engine)
    test_engine.dispose()

    with TestClient(create_app(test_settings)) as test_client:
        yield test_client
