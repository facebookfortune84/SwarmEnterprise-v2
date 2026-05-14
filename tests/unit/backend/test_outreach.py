def test_outreach_enqueue(client, monkeypatch):
    # Replace the enqueue function to validate it's called
    called = {}
    def fake_enqueue(to_email, subject, body):
        called['args'] = (to_email, subject, body)

    monkeypatch.setattr('backend.api.outreach.enqueue_outreach', fake_enqueue)

    r = client.post('/api/outreach/', json={"email": "lead@example.com", "subject": "Hello", "body": "Hi there"})
    assert r.status_code == 200
    assert called.get('args') is not None
    assert called['args'][0] == 'lead@example.com'
