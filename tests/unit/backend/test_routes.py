def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ONLINE"
    assert response.json()["engine"] == "SwarmOS"


def test_build_trigger(client):
    payload = {"name": "Test App", "description": "A testing vibe", "stack": "FastAPI"}
    response = client.post("/api/build", json=payload)
    assert response.status_code == 200
    assert "project_id" in response.json()
