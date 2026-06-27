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

    # Mock CompanyGenerator to avoid DB/Agent issues in this test
    class MockGenerator:
        async def generate_company(self, request):
            pass

    monkeypatch.setattr("backend.services.company_generator.CompanyGenerator", MockGenerator)

    # Ensure DB is fresh for this test to avoid processed event leakage
    # Use in-memory SQLite with thread-safety for TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from backend.db.base import Base
    from backend.db.linear_engine import LinearEngine

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    fresh_db = LinearEngine(db=Session())

    monkeypatch.setattr(wh, "DB", fresh_db)

    headers = {"stripe-signature": "t=1,v1=signature"}
    r = client.post("/api/webhooks/stripe", data=b"{}", headers=headers)
    assert r.status_code == 200
    assert r.json().get("status") == "success"
    assert called.get("project_id") is not None
