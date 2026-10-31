import pytest
from fastapi.testclient import TestClient
from google import genai
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database, main
from app.search import provider


@pytest.fixture(autouse=True)
def test_database(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.sqlite3'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    monkeypatch.setattr(provider, "SEARCH_PROVIDER", "mock")

    def forbid_ai(*args, **kwargs):
        raise AssertionError("Tests must not create a live AI client")

    monkeypatch.setattr(genai, "Client", forbid_ai)
    database.init_database()
    try:
        yield session_factory
    finally:
        engine.dispose()


@pytest.fixture
def client(test_database):
    with TestClient(main.app) as test_client:
        yield test_client
