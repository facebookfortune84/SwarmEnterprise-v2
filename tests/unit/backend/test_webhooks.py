import stripe


def make_event(event_id="evt_test"):
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "sess_1",
                "customer_details": {"email": "buyer@example.com"},
                "metadata": {"project_id": "PROJ1"},
                "display_items": [],
            }
        },
    }


def test_stripe_webhook_idempotency(client, monkeypatch):
    # Patch stripe.Webhook.construct_event to return a deterministic event
    def _construct_event(payload, sig, secret):
        return make_event("evt_123")

    monkeypatch.setattr(stripe.Webhook, "construct_event", staticmethod(_construct_event))

    headers = {"stripe-signature": "t=1,v1=signature"}

    r1 = client.post("/api/webhooks/stripe", content=b"{}", headers=headers)
    assert r1.status_code == 200
    assert r1.json().get("status") == "success"

    # Replay same event - should be idempotent
    r2 = client.post("/api/webhooks/stripe", content=b"{}", headers=headers)
    assert r2.status_code == 200
    assert r2.json().get("note") == "already_processed"
