from unittest.mock import patch


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ONLINE"
    assert response.json()["engine"] == "SwarmOS"


def test_build_trigger(client):
    """Trigger a build without executing the full crewai/LLM production cycle.

    The background task calls swarm_factory.run_production_cycle which invokes
    crewai agents that access ``BuildRequest.__fields__`` (Pydantic V2 deprecated
    attribute).  We mock the production cycle so the test exercises the HTTP
    layer only and emits no deprecation warnings.
    """
    payload = {"name": "Test App", "description": "A testing vibe", "stack": "FastAPI"}
    with patch(
        "backend.api.routes._safe_run_production_cycle",
        return_value={"status": "success", "tickets_generated": 0, "tickets_enqueued": 0},
    ):
        response = client.post("/api/build", json=payload)
    assert response.status_code == 200
    assert "project_id" in response.json()
