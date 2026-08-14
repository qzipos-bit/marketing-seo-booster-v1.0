"""Load EEAT and YMYL specialist checklists for crypto projects."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.config_loader import ROOT

EEAT_MD = ROOT / "prompts" / "crypto-eeat-checklist.md"
YMYL_MD = ROOT / "prompts" / "crypto-ymyl-checklist.md"
SOURCES_MD = ROOT / "prompts" / "crypto-audit-sources.md"

EEAT_BLOCK_NAMES = {
    "E": "Experience",
    "X": "Expertise",
    "A": "Authoritativeness",
    "T": "Trustworthiness",
}

YMYL_BLOCK_NAMES = {
    "Y1": "Классификация YMYL",
    "Y2": "Предотвращение вреда",
    "Y3": "Точность и consensus",
    "Y4": "Репутация и регуляторика",
    "Y5": "Transactional trust",
}

SEV_MAP = {"🔴": "critical", "🟠": "high", "🟡": "medium", "🟢": "low"}

SOURCE_URLS = {
    "G-QRG": "https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf",
    "G-HC": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    "G-SPAM": "https://developers.google.com/search/docs/essentials/spam-policies",
    "G-RAT": "https://developers.google.com/search/docs/appearance/structured-data/review-snippet",
    "G-ORG": "https://developers.google.com/search/docs/appearance/structured-data/organization",
    "G-AI": "https://developers.google.com/search/docs/fundamentals/creating-helpful-content",
    "R-SEC": "https://www.sec.gov/newsroom/press-releases",
    "R-FINCEN": "https://www.fincen.gov/msb-registrant-search",
    "R-FATF": "https://www.fatf-gafi.org/en/topics/virtual-assets.html",
    "R-MICA": "https://finance.ec.europa.eu/regulation-and-supervision/fintech/crypto-assets_en",
    "R-FCA": "https://register.fca.org.uk/s/search",
    "R-ESMA": "https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/crypto-assets",
    "S-ORG": "https://schema.org/Organization",
    "S-FS": "https://schema.org/FinancialService",
    "S-FAQ": "https://schema.org/FAQPage",
    "S-PERSON": "https://schema.org/Person",
    "I-CRAWLUX": "https://www.crawlux.com/guides/eeat-ymyl-crypto/",
    "I-ANYLEARN": "https://anylearn.cc/lessons/eeat-and-entity-seo-for-crypto",
    "I-GUIDEX": "https://theguidex.com/insights/google-quality-rater-guidelines",
}


def _parse_specialist_tables(text: str, block_names: dict[str, str], id_prefix: str) -> list[dict]:
    items: list[dict] = []
    current_block = ""

    for line in text.splitlines():
        block_match = re.match(r"^## (Y\d|[A-Z])\.", line)
        if block_match:
            current_block = block_match.group(1)
            continue

        if not line.startswith("|") or line.startswith("|---") or "# | Sev" in line:
            continue

        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 5:
            continue
        item_id = cols[0]
        if not re.match(rf"^{id_prefix}\d{{2}}$", item_id):
            continue

        sev_icon = cols[1]
        source_raw = cols[5] if len(cols) > 5 else cols[4].split("|")[-1] if False else ""
        source = cols[5].strip() if len(cols) > 5 else ""

        items.append(
            {
                "id": item_id,
                "block": current_block,
                "block_name": block_names.get(current_block, current_block),
                "severity": SEV_MAP.get(sev_icon, "medium"),
                "scope": cols[2],
                "title": cols[3].replace("**", ""),
                "how": cols[4],
                "source": source,
                "source_url": _source_url(source),
            }
        )
    return items


def _source_url(source: str) -> str | None:
    for sid, url in SOURCE_URLS.items():
        if sid in source:
            return url
    return None


@lru_cache(maxsize=1)
def load_eeat_catalog() -> list[dict]:
    return _parse_specialist_tables(
        EEAT_MD.read_text(encoding="utf-8"),
        EEAT_BLOCK_NAMES,
        "EE",
    )


@lru_cache(maxsize=1)
def load_ymyl_catalog() -> list[dict]:
    return _parse_specialist_tables(
        YMYL_MD.read_text(encoding="utf-8"),
        YMYL_BLOCK_NAMES,
        "YY",
    )


def render_sources_html(md: str) -> str:
    """Minimal markdown → HTML for library page (tables + headings)."""
    import html as html_mod

    lines = md.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            out.append(f"<h1>{html_mod.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html_mod.escape(line[3:])}</h2>")
        elif line.startswith("> "):
            out.append(f"<blockquote>{html_mod.escape(line[2:])}</blockquote>")
        elif line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|---"):
            rows = []
            header = [c.strip() for c in line.strip("|").split("|")]
            rows.append("<tr>" + "".join(f"<th>{html_mod.escape(c)}</th>" for c in header) + "</tr>")
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                cols = [c.strip() for c in lines[i].strip("|").split("|")]
                cells = []
                for c in cols:
                    if c.startswith("http"):
                        cells.append(f'<td><a href="{html_mod.escape(c)}" target="_blank" rel="noopener">{html_mod.escape(c[:50])}…</a></td>' if len(c) > 50 else f'<td><a href="{html_mod.escape(c)}" target="_blank" rel="noopener">{html_mod.escape(c)}</a></td>')
                    else:
                        cells.append(f"<td>{html_mod.escape(c)}</td>")
                rows.append("<tr>" + "".join(cells) + "</tr>")
                i += 1
            out.append("<table>" + "".join(rows) + "</table>")
            continue
        elif line.strip():
            out.append(f"<p>{html_mod.escape(line)}</p>")
        i += 1
    return "\n".join(out)


def load_sources_library() -> str:
    if SOURCES_MD.exists():
        return SOURCES_MD.read_text(encoding="utf-8")
    return ""


def catalog_by_type(checklist_type: str) -> list[dict]:
    if checklist_type == "ymyl":
        return load_ymyl_catalog()
    return load_eeat_catalog()


def block_names_for(checklist_type: str) -> dict[str, str]:
    return YMYL_BLOCK_NAMES if checklist_type == "ymyl" else EEAT_BLOCK_NAMES
