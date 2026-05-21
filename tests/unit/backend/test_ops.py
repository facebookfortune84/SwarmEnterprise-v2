def test_ops_status(client):
    r = client.get("/api/ops/status")
    assert r.status_code == 200
    body = r.json()
    assert "domains" in body
    assert "ollama" in body


def test_heal_sync(client):
    r = client.post("/api/ops/heal-sync")
    assert r.status_code == 200
    assert "checks" in r.json()
