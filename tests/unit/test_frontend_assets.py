from pathlib import Path


def test_frontend_includes_growth_hub_assets():
    root = Path(__file__).resolve().parents[1]
    index_html = (root / ".." / "frontend" / "public" / "index.html").resolve().read_text(
        encoding="utf-8"
    )
    outreach_js = (root / ".." / "frontend" / "public" / "outreach-hub.js").resolve()

    assert "outreach-hub.js" in index_html
    assert "Growth" in index_html
    assert "campaignComposer" in index_html
    assert outreach_js.exists()


def test_frontend_composer_only_resets_after_successful_queue():
    outreach_js = (Path(__file__).resolve().parents[1] / ".." / "frontend" / "public" / "outreach-hub.js").resolve().read_text(encoding="utf-8")

    assert "if (result && result.status === \"queued\")" in outreach_js
    assert 'form.reset();' in outreach_js
