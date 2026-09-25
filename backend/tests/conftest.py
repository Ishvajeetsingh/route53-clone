"""Isolated test database: file-backed SQLite in tmp dir, never the dev database."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models.dns  # noqa: F401  (register tables)
from app.database import Base, get_db
from app.main import app  # noqa: E402  (importing also exercises startup/seed path)


@pytest.fixture()
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def client(session_factory):
    def override():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session(session_factory):
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def auth_headers(client):
    res = client.post("/api/auth/login", json={"username": "tester", "password": "not-a-real-password"})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.fixture()
def zone(client, auth_headers):
    res = client.post(
        "/api/hosted-zones",
        json={"name": "example.com", "description": "test zone", "type": "Public"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    return res.json()
