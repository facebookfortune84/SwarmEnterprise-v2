import smtplib


def test_email_fallback(monkeypatch):
    # Configure primary and fallback providers
    monkeypatch.setenv("SMTP_SERVER", "primary.smtp.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "user1")
    monkeypatch.setenv("SMTP_PASS", "pass1")
    monkeypatch.setenv("SMTP_FALLBACKS", "fallback.smtp.test:587:fbuser:fbpass")

    calls = []

    class FakeSMTP:
        def __init__(self, server, port, timeout=30):
            self.server = server
            self.port = port
            calls.append(("init", server))

        def starttls(self):
            pass

        def login(self, user, pw):
            pass

        def send_message(self, msg):
            # Primary fails, fallback succeeds
            if "primary.smtp.test" in self.server:
                raise smtplib.SMTPException("primary failed")
            calls.append(("sent", self.server))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    import agents.outreach.email_engine as ee

    monkeypatch.setattr(ee.smtplib, "SMTP", FakeSMTP)

    et = ee.EmailTools()
    res = et.send_email("a@b.com", "s", "<p>b</p>")
    assert res == "SUCCESS"
    assert ("sent", "fallback.smtp.test") in calls
