"""Unit tests for competitor URL discovery and diff logic."""

from app.competitor_monitor import (
    _diff_pages,
    _extract_sitemap_locs,
    _normalize_path,
    _score_path,
    build_snapshots_csv,
)
from app.storage import (
    finish_competitor_run,
    get_known_competitor_paths,
    insert_competitor_snapshots,
    start_competitor_run,
    upsert_known_competitor_paths,
)


SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
</sitemapindex>"""

SITEMAP_PAGES = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/exchange/btc-eth</loc></url>
  <url><loc>https://example.com/blog/news</loc></url>
  <url><loc>https://example.com/static/file.pdf</loc></url>
</urlset>"""


def test_extract_sitemap_index():
    children, pages = _extract_sitemap_locs(SITEMAP_INDEX)
    assert children == ["https://example.com/sitemap-pages.xml"]
    assert pages == []


def test_extract_sitemap_pages():
    children, pages = _extract_sitemap_locs(SITEMAP_PAGES)
    assert children == []
    assert len(pages) == 3


def test_score_path_prioritizes_exchange():
    assert _score_path("/exchange/btc-eth") > _score_path("/blog/news")
    assert _score_path("/") > _score_path("/random-page")


def test_diff_new_landing_uses_known_paths():
    known = {"/", "/about"}
    previous = {"/": {"title": "Home", "meta_description": "", "h1": "", "content_hash": "a", "word_count": 100, "url": "https://x.io/"}}
    current = [
        {"path": "/", "url": "https://x.io/", "title": "Home", "meta_description": "", "h1": "", "content_hash": "a", "word_count": 100},
        {"path": "/exchange-btc", "url": "https://x.io/exchange-btc", "title": "New", "meta_description": "", "h1": "", "content_hash": "b", "word_count": 50},
    ]
    changes = _diff_pages("test", previous, known, current)
    new = [c for c in changes if c["change_type"] == "new_landing"]
    assert len(new) == 1
    assert new[0]["path"] == "/exchange-btc"


def test_diff_no_new_on_first_run():
    previous = {}
    known = set()
    current = [
        {"path": "/", "url": "https://x.io/", "title": "Home", "meta_description": "", "h1": "", "content_hash": "a", "word_count": 100},
    ]
    changes = _diff_pages("test", previous, known, current)
    assert not any(c["change_type"] == "new_landing" for c in changes)


def test_known_paths_registry(tmp_path, monkeypatch):
    from app.storage import init_db

    db = tmp_path / "known_paths.db"
    monkeypatch.setattr("app.storage.DB_PATH", db)
    init_db()
    run_id = start_competitor_run("test")
    pages = [
        {"competitor_id": "changenow", "path": "/foo-test", "url": "https://changenow.io/foo-test"},
        {"competitor_id": "changenow", "path": "/bar-test", "url": "https://changenow.io/bar-test"},
    ]
    insert_competitor_snapshots(run_id, pages)
    new_count = upsert_known_competitor_paths("changenow", run_id, pages)
    assert new_count == 2
    known = get_known_competitor_paths("changenow")
    assert "/foo-test" in known and "/bar-test" in known

    new_count2 = upsert_known_competitor_paths(
        "changenow",
        run_id,
        pages + [{"path": "/baz-test", "url": "https://changenow.io/baz-test"}],
    )
    assert new_count2 == 1
    assert "/baz-test" in get_known_competitor_paths("changenow")
    finish_competitor_run(run_id, {"status": "ok"}, [])


def test_build_snapshots_csv():
    csv = build_snapshots_csv([
        {"competitor_id": "x", "competitor_name": "X", "url": "https://x.io/", "path": "/", "title": "T"},
    ])
    assert "competitor_id" in csv
    assert "changenow" not in csv or "x" in csv
