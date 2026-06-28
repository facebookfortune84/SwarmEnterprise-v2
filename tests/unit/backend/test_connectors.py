import importlib


def test_hubspot_connector(monkeypatch):
    """HubSpot connector creates contacts via POST.

    The connector reads API_KEY at module-import time into a module-level
    constant.  monkeypatch.setenv alone is insufficient — we must also patch
    the module-level ``API_KEY`` attribute directly.
    """
    calls = {}

    def fake_post(url, json=None, headers=None, params=None, timeout=10):
        calls["url"] = url
        calls["json"] = json

        class R:
            def raise_for_status(self):
                return None

            def json(self):
                return {"id": "hs_1"}

        return R()

    hs = importlib.import_module("backend.connectors.hubspot")
    # Patch the already-evaluated module-level constant, not just the env var
    monkeypatch.setattr(hs, "API_KEY", "testkey")
    monkeypatch.setattr(hs.requests, "post", fake_post)
    res = hs.create_contact("a@b.com", {"company": "TestCo"})
    assert res and res.get("id") == "hs_1"
    assert "crm/v3/objects/contacts" in calls["url"]


def test_close_connector(monkeypatch):
    """Close CRM connector creates leads via POST.

    Same module-level constant issue as HubSpot — patch ``API_KEY`` directly.
    """

    def fake_post(url, json=None, headers=None, timeout=10):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                return {"id": "close_1"}

        return R()

    close = importlib.import_module("backend.connectors.close")
    monkeypatch.setattr(close, "API_KEY", "testkey")
    monkeypatch.setattr(close.requests, "post", fake_post)
    res = close.create_lead("a@b.com", {"name": "A"})
    assert res and res.get("id") == "close_1"


def test_sheets_connector(monkeypatch):
    """Sheets connector pushes rows via POST.

    SHEETS_ENDPOINT is also captured at module-import time.  Additionally,
    sheets.py does ``import requests`` *inside* push_row(), so we must patch
    the ``requests`` module that sheets will import — i.e. patch it via the
    module's namespace after the lazy import resolves, or patch
    ``requests.post`` globally before the call.  The simplest correct approach
    is to patch ``SHEETS_ENDPOINT`` on the module AND stub ``requests.post``
    on the globally-imported requests object.
    """

    def fake_post(url, json=None, timeout=10):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                return {"ok": True}

        return R()

    sheets = importlib.import_module("backend.connectors.sheets")
    # Patch the already-evaluated module-level constant
    monkeypatch.setattr(sheets, "SHEETS_ENDPOINT", "http://sheets.example.com/append")
    # sheets.py does `import requests` inside push_row — patch the top-level module
    import requests as _requests

    monkeypatch.setattr(_requests, "post", fake_post)
    res = sheets.push_row({"email": "a@b.com"})
    assert res and res.get("ok")
