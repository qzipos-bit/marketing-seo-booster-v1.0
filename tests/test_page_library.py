"""Tests for mandatory page library."""

from pathlib import Path

from app.page_library import (
    _load_mandatory_urls,
    get_scan_pages,
    mandatory_page_urls,
    page_entry_from_url,
)


def test_page_entry_from_url_pair_label():
    entry = page_entry_from_url("https://quickex.io/exchange-btc-xmr", mandatory=True)
    assert entry["pair"] == "btc-xmr"
    assert entry["mandatory"] is True
    assert "BTC" in entry["label"]


def test_mandatory_pages_file(tmp_path, monkeypatch):
    _load_mandatory_urls.cache_clear()
    f = tmp_path / "pages.txt"
    f.write_text(
        "https://quickex.io/exchange-btc-eth\n"
        "https://quickex.io/exchange-eth-btc\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CONFIG_PROFILE", "quickex")
    monkeypatch.setattr(
        "app.page_library.mandatory_pages_file_path",
        lambda: Path(f),
    )
    urls = mandatory_page_urls()
    assert len(urls) == 2
    assert "exchange-btc-eth" in urls[0]


def test_get_scan_pages_merges_config_and_mandatory(monkeypatch, tmp_path):
    _load_mandatory_urls.cache_clear()
    f = tmp_path / "mandatory.txt"
    f.write_text("https://quickex.io/exchange-btc-xmr\n", encoding="utf-8")
    monkeypatch.setenv("CONFIG_PROFILE", "quickex")
    monkeypatch.setattr("app.page_library.mandatory_pages_file_path", lambda: Path(f))

    pages = get_scan_pages()
    urls = {p["url"] for p in pages}
    assert "https://quickex.io/exchange-btc-xmr" in urls
    assert "https://quickex.io/" in urls
    mandatory = [p for p in pages if p.get("mandatory")]
    assert len(mandatory) >= 1
