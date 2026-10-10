"""Isolated application checks using an in-memory MongoDB substitute."""
import importlib
import os
import secrets
import sys
from pathlib import Path
from unittest.mock import patch

import mongomock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["SECRET_KEY"] = secrets.token_hex(32)
os.environ["MONGO_DB"] = "future_store_tests"
with patch("pymongo.MongoClient", mongomock.MongoClient):
    app_module = importlib.import_module("app")


@pytest.fixture
def application(monkeypatch):
    import app_db
    client = mongomock.MongoClient()
    monkeypatch.setattr(app_db, "_client", client)
    app = app_module.create_app()
    app.config.update(TESTING=True, DEBUG=False)
    yield app
    client.close()


@pytest.fixture
def db(application):
    from app_db import get_db
    with application.app_context():
        database = get_db()
        database.products.insert_many([
            {"_id": 1, "name": "Demo Headphones", "description": "Wireless audio", "brand": "Demo", "category": "Electronics", "price": 80.0, "rating": 4.0, "stock": 20, "is_active": 1, "image": ""},
            {"_id": 2, "name": "Demo Speaker", "description": "Portable audio", "brand": "Demo", "category": "Electronics", "price": 90.0, "rating": 4.5, "stock": 10, "is_active": 1, "image": ""},
            {"_id": 3, "name": "Demo Book", "description": "Python guide", "brand": "Demo", "category": "Books", "price": 15.0, "rating": 4.8, "stock": 30, "is_active": 1, "image": ""},
            {"_id": 4, "name": "Inactive Item", "description": "Unavailable", "brand": "Demo", "category": "Electronics", "price": 81.0, "rating": 5.0, "stock": 0, "is_active": 0, "image": ""},
        ])
        database.counters.insert_one({"_id": "products", "seq": 4})
        yield database


@pytest.fixture
def client(application, db):
    return application.test_client()


@pytest.fixture
def registered_client(client):
    response = client.post("/auth/register", data={"name": "Demo User", "email": "user@example.test", "password": "sample-test-password", "confirm_password": "sample-test-password"})
    assert response.status_code == 302
    return client
