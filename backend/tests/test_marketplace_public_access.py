from fastapi.testclient import TestClient

from apps.api.main import app
from db.session import get_db


class _ListingQuery:
    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return []


class _FakeDB:
    def query(self, *args, **kwargs):
        return _ListingQuery()


def _fake_db():
    yield _FakeDB()


def test_public_marketplace_listings_do_not_require_auth():
    app.dependency_overrides[get_db] = _fake_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/listings")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []
