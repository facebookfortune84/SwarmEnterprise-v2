from pathlib import Path


def test_frontend_domain_config_mentions_launch_domains():
    root = Path(__file__).resolve().parents[2]
    index_html = (root / "frontend" / "public" / "index.html").read_text(encoding="utf-8")
    config_js = (root / "frontend" / "public" / "config.js").read_text(encoding="utf-8")

    assert "realms2riches.com" in index_html
    assert "corp.realms2riches.com" in index_html
    assert "realms2riches.tech" in index_html
    assert "SWARM_DOMAIN_CONFIG" in config_js
