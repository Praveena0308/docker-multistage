from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

def test_root():
    r = client.get("/")
    assert r.status_code == 200

def test_create_and_get_item():
    r = client.post("/items/test1", json={"name": "test", "value": "hello"})
    assert r.status_code == 200
    r = client.get("/items/test1")
    assert r.status_code == 200
    assert r.json()["data"]["value"] == "hello"

def test_item_not_found():
    r = client.get("/items/nonexistent")
    assert r.status_code == 404