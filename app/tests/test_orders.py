import fakeredis
import pytest
from fastapi.testclient import TestClient

from orders import api, worker


@pytest.fixture()
def fake():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture()
def client(fake):
    api.app.dependency_overrides[api.get_redis] = lambda: fake
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def test_healthz(client):
    assert client.get("/healthz").json()["status"] == "ok"


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_order_lifecycle(client, fake):
    resp = client.post("/orders", json={"sku": "SKU-00042", "qty": 2})
    assert resp.status_code == 201
    order_id = resp.json()["id"]
    assert client.get(f"/orders/{order_id}").json()["status"] == "pending"

    catalog = worker.load_catalog(100)
    _, queued_id = fake.brpop("orders:queue", timeout=1)
    assert worker.process(fake, catalog, queued_id) == "processed"
    assert client.get(f"/orders/{order_id}").json()["status"] == "processed"


def test_unknown_sku_rejected(client, fake):
    order_id = client.post("/orders", json={"sku": "NOPE", "qty": 1}).json()["id"]
    assert worker.process(fake, worker.load_catalog(10), order_id) == "rejected"


def test_validation(client):
    assert client.post("/orders", json={"sku": "SKU-1", "qty": 0}).status_code == 422


def test_missing_order(client):
    assert client.get("/orders/doesnotexist").status_code == 404
