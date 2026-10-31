from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import main
from app.database import Base


def test_health(tmp_path, monkeypatch):
    test_engine = create_engine(f"sqlite:///{tmp_path / 'test.sqlite3'}")
    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setattr(
        main, "init_database", lambda: Base.metadata.create_all(test_engine)
    )
    with TestClient(main.app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
