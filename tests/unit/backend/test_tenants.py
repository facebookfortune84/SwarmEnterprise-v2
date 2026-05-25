def test_register_tenant(client):
    r = client.post("/api/tenants/register", json={"name": "Acme Corp", "slug": "acme-test"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "registered"
    assert data["tenant"]["slug"] == "acme-test"


def test_list_tenants(client):
    client.post("/api/tenants/register", json={"name": "Beta LLC", "slug": "beta-test"})
    r = client.get("/api/tenants")
    assert r.status_code == 200
    assert "tenants" in r.json()
