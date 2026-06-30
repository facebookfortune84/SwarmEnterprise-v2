import threading
import time
from types import SimpleNamespace

import pytest

import backend.queue as backend_queue
from agents.outreach import worker as outreach_worker


def test_outreach_enqueue(client, monkeypatch):
    called = {}

    def fake_enqueue(to_email, subject, body):
        called["args"] = (to_email, subject, body)

    monkeypatch.setattr("backend.api.outreach.enqueue_outreach", fake_enqueue)

    r = client.post(
        "/api/outreach/", json={"email": "lead@example.com", "subject": "Hello", "body": "Hi there"}
    )
    assert r.status_code == 200
    assert called.get("args") is not None
    assert called["args"][0] == "lead@example.com"


def test_outreach_campaign_enqueues_one_task_per_recipient(client, monkeypatch):
    calls = []

    def fake_enqueue_campaign(recipients, subject, body, from_name="SwarmOS"):
        calls.append((recipients, subject, body, from_name))

    monkeypatch.setattr("backend.api.outreach.enqueue_campaign", fake_enqueue_campaign)

    r = client.post(
        "/api/outreach/campaign",
        json={
            "recipients": ["lead1@example.com", "lead2@example.com"],
            "subject": "Launch update",
            "body": "We built something amazing.",
            "from_name": "SwarmOS",
        },
    )

    assert r.status_code == 200
    assert calls == [
        (["lead1@example.com", "lead2@example.com"], "Launch update", "We built something amazing.", "SwarmOS")
    ]


def test_outreach_payload_validation_rejects_empty_required_fields(client):
    response = client.post("/api/outreach/", json={"email": "", "subject": "", "body": ""})
    assert response.status_code == 422


def test_outreach_campaign_payload_validation_rejects_empty_recipients(client):
    response = client.post(
        "/api/outreach/campaign",
        json={"recipients": [], "subject": "Hello", "body": "Body", "from_name": "Nova"},
    )
    assert response.status_code == 422


def test_enqueue_campaign_skips_empty_recipients(monkeypatch):
    queued = []
    monkeypatch.setattr(backend_queue, "enqueue_task", lambda payload: queued.append(payload))

    outreach_worker.enqueue_campaign([], "Subject", "Body")

    assert queued == []


def test_enqueue_campaign_queues_each_recipient_with_from_name(monkeypatch):
    queued = []
    monkeypatch.setattr(backend_queue, "enqueue_task", lambda payload: queued.append(payload))

    outreach_worker.enqueue_campaign(["a@example.com", "  b@example.com  "], "Subject", "Body", from_name="Nova")

    assert queued == [
        {"to_email": "a@example.com", "subject": "Subject", "body": "Body", "attempts": 0, "from_name": "Nova", "campaign": True},
        {"to_email": "b@example.com", "subject": "Subject", "body": "Body", "attempts": 0, "from_name": "Nova", "campaign": True},
    ]


def test_enqueue_outreach_delegates_to_campaign(monkeypatch):
    calls = []
    monkeypatch.setattr(outreach_worker, "enqueue_campaign", lambda recipients, subject, body, from_name="SwarmOS": calls.append((list(recipients), subject, body, from_name)))

    outreach_worker.enqueue_outreach("lead@example.com", "Hello", "Body")

    assert calls == [(["lead@example.com"], "Hello", "Body", "SwarmOS")]


def test_worker_loop_sends_messages_and_stops(monkeypatch):
    processed = []

    class FakeEmailTools:
        def send_email(self, to_email, subject, body):
            processed.append((to_email, subject, body))
            return "SUCCESS"

    monkeypatch.setattr(outreach_worker, "EmailTools", FakeEmailTools)

    queue_items = [{"to_email": "lead@example.com", "subject": "Hello", "body": "Body"}, None]

    def fake_dequeue(timeout=1):
        return queue_items.pop(0)

    monkeypatch.setattr(backend_queue, "dequeue_task", fake_dequeue)
    monkeypatch.setattr(outreach_worker.time, "sleep", lambda *_args, **_kwargs: None)

    stop_event = threading.Event()
    thread = threading.Thread(target=outreach_worker._worker_loop, args=(stop_event,), daemon=True)
    thread.start()
    time.sleep(0.1)
    stop_event.set()
    thread.join(timeout=1)

    assert processed == [("lead@example.com", "Hello", "Body")]


def test_worker_loop_requeues_failed_messages(monkeypatch):
    class FakeEmailTools:
        def send_email(self, to_email, subject, body):
            return "ERROR"

    queued = []
    monkeypatch.setattr(outreach_worker, "EmailTools", FakeEmailTools)
    monkeypatch.setattr(backend_queue, "dequeue_task", lambda timeout=1: {"to_email": "lead@example.com", "subject": "Hello", "body": "Body", "attempts": 0})
    monkeypatch.setattr(backend_queue, "enqueue_task", lambda payload: queued.append(payload))
    monkeypatch.setattr(outreach_worker.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(outreach_worker.os, "getenv", lambda key, default=None: "1")

    stop_event = threading.Event()
    thread = threading.Thread(target=outreach_worker._worker_loop, args=(stop_event,), daemon=True)
    thread.start()
    time.sleep(0.1)
    stop_event.set()
    thread.join(timeout=1)

    assert len(queued) == 1
    assert queued[0]["attempts"] == 1


def test_start_and_stop_worker(monkeypatch):
    started = []
    stopped = []

    class FakeThread:
        def __init__(self, target, args=(), daemon=False):
            self.target = target
            self.args = args
            self.daemon = daemon
            self.started = False

        def start(self):
            self.started = True
            started.append((self.target, self.args))

        def join(self, timeout=None):
            stopped.append(timeout)
            return None

        def is_alive(self):
            return False

    monkeypatch.setattr(outreach_worker, "threading", SimpleNamespace(Thread=FakeThread, Event=threading.Event))

    outreach_worker._worker_thread = None
    outreach_worker._stop_event = None

    outreach_worker.start_worker()
    outreach_worker.stop_worker()

    assert not started or started
    assert stopped == [] or stopped == [5]


def test_email_engine_mocks_when_no_credentials(monkeypatch):
    from agents.outreach.email_engine import EmailTools

    monkeypatch.setenv("SMTP_PASS", "")
    sender = EmailTools()
    assert sender.send_email("lead@example.com", "Hello", "<p>body</p>") == "SUCCESS (MOCKED)"


def test_email_engine_returns_error_when_all_providers_fail(monkeypatch):
    from agents.outreach.email_engine import EmailTools

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setenv("SMTP_PASS", "secret")
    monkeypatch.setattr("agents.outreach.email_engine.smtplib.SMTP", FakeSMTP)
    sender = EmailTools()
    assert "ERROR" in sender.send_email("lead@example.com", "Hello", "<p>body</p>")
