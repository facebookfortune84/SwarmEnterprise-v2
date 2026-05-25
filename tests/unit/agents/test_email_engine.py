import smtplib


def test_email_mocked(monkeypatch):
    monkeypatch.delenv("SMTP_PASS", raising=False)
    from agents.outreach.email_engine import EmailTools

    et = EmailTools()
    res = et.send_email("a@b.com", "subject", "<p>hello</p>")
    assert res.startswith("SUCCESS")


def test_email_retry(monkeypatch):
    monkeypatch.setenv("SMTP_PASS", "secret")

    # Fake SMTP that always fails
    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def starttls(self):
            pass

        def login(self, user, pw):
            pass

        def send_message(self, msg):
            raise smtplib.SMTPException("send failed")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    import agents.outreach.email_engine as ee

    monkeypatch.setattr(ee.smtplib, "SMTP", FakeSMTP)

    et = ee.EmailTools()
    et.max_retries = 2
    res = et.send_email("a@b.com", "subject", "<p>retry</p>")
    assert res.startswith("ERROR")
