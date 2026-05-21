def test_stripe_webhook_end_to_end(client, monkeypatch):
    # Mock stripe construct_event
    def _construct_event(payload, sig, secret):
        return {
            "id": "evt_e2e",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "sess_e2e",
                    "customer_details": {"email": "buyer@e2e.com"},
                    "metadata": {"project_id": "PROJE2E", "amount": "4999"},
                    "display_items": [],
                }
            },
        }

    monkeypatch.setattr("stripe.Webhook.construct_event", staticmethod(_construct_event))

    # Mock replicator to avoid filesystem ops
    called = {}

    class DummyReplicator:
        @staticmethod
        def create_company_bundle(project_id, customer_email=None):
            called["project_id"] = project_id
            return {"status": "success", "download_url": f"https://download/{project_id}.zip"}

    import backend.api.webhooks as wh

    monkeypatch.setattr(wh, "replicator_engine", DummyReplicator())

    # Ensure DB is fresh for this test to avoid processed event leakage
    import tempfile
    import os
    from backend.db import linear_engine

    tmpdir = tempfile.mkdtemp()
    os.environ["SWARM_PG_DIR"] = tmpdir
    fresh_db = linear_engine.LinearEngine()
    import backend.api.webhooks as wh

    monkeypatch.setattr(wh, "DB", fresh_db)

    headers = {"stripe-signature": "t=1,v1=signature"}
    r = client.post("/api/webhooks/stripe", data=b"{}", headers=headers)
    assert r.status_code == 200
    assert r.json().get("status") == "success"
    assert called.get("project_id") is not None
