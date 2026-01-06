from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "user-service"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_users():
    response = client.get("/users")
    assert response.status_code == 200
    assert "users" in response.json()
    assert len(response.json()["users"]) == 2

def test_get_user():
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Alice"
