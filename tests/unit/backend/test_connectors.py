import json


def test_hubspot_connector(monkeypatch):
    calls = {}
    def fake_post(url, json=None, headers=None, params=None, timeout=10):
        calls['url'] = url
        calls['json'] = json
        class R:
            def raise_for_status(self):
                return None
            def json(self):
                return {'id': 'hs_1'}
        return R()

    import backend.connectors.hubspot as hs
    monkeypatch.setattr('backend.connectors.hubspot.requests.post', fake_post)
    res = hs.create_contact('a@b.com', {'company': 'TestCo'})
    assert res and res.get('id') == 'hs_1'
    assert 'crm/v3/objects/contacts' in calls['url']


def test_close_connector(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=10):
        class R:
            def raise_for_status(self):
                return None
            def json(self):
                return {'id': 'close_1'}
        return R()

    import backend.connectors.close as close
    monkeypatch.setattr('backend.connectors.close.requests.post', fake_post)
    res = close.create_lead('a@b.com', {'name': 'A'})
    assert res and res.get('id') == 'close_1'


def test_sheets_connector(monkeypatch):
    def fake_post(url, json=None, timeout=10):
        class R:
            def raise_for_status(self):
                return None
            def json(self):
                return {'ok': True}
        return R()

    import backend.connectors.sheets as sheets
    monkeypatch.setattr('backend.connectors.sheets.requests.post', fake_post)
    monkeypatch.setenv('SHEETS_ENDPOINT', 'http://sheets.example.com/append')
    res = sheets.push_row({'email': 'a@b.com'})
    assert res and res.get('ok')
