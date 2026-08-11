from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Trust-Aware Personalized AI News Intelligence System API"}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    # Note: the worker and database status might be different in a test environment
    # but we expect the endpoint to return without error

if __name__ == "__main__":
    test_root()
    print("Root test passed")
    test_health()
    print("Health test passed")