def test_hubspot_connector(monkeypatch):
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

    monkeypatch.setenv("HUBSPOT_API_KEY", "testkey")
    import importlib

    hs = importlib.import_module("backend.connectors.hubspot")
    monkeypatch.setattr(hs.requests, "post", fake_post)
    res = hs.create_contact("a@b.com", {"company": "TestCo"})
    assert res and res.get("id") == "hs_1"
    assert "crm/v3/objects/contacts" in calls["url"]


def test_close_connector(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=10):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                return {"id": "close_1"}

        return R()

    monkeypatch.setenv("CLOSE_API_KEY", "testkey")
    import importlib

    close = importlib.import_module("backend.connectors.close")
    monkeypatch.setattr(close.requests, "post", fake_post)
    res = close.create_lead("a@b.com", {"name": "A"})
    assert res and res.get("id") == "close_1"


def test_sheets_connector(monkeypatch):
    def fake_post(url, json=None, timeout=10):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                return {"ok": True}

        return R()

    import importlib

    monkeypatch.setenv("SHEETS_ENDPOINT", "http://sheets.example.com/append")
    sheets = importlib.import_module("backend.connectors.sheets")
    import requests

    monkeypatch.setattr(requests, "post", fake_post)
    res = sheets.push_row({"email": "a@b.com"})
    assert res and res.get("ok")
