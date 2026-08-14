"""Load SEO + Nuxt checklist catalog from markdown files."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.config_loader import ROOT

CHECKLIST_MD = ROOT / "prompts" / "quickex-seo-checklist-100.md"
NUXT_MD = ROOT / "prompts" / "nuxt-checklist-extra.md"
PRO_MD = ROOT / "prompts" / "pro-forum-checklist-extra.md"

BLOCK_NAMES = {
    "A": "Техническое SEO",
    "B": "Мета и соцсети",
    "C": "Контент и структура",
    "D": "LQA и бренд",
    "E": "Ключевые слова",
    "F": "Структурированные данные",
    "G": "i18n и hreflang",
    "H": "Доверие и UX",
    "N": "Nuxt / SPA",
    "I": "AI Readiness",
    "J": "Безопасность",
    "K": "Pro-архитектура",
}

SEV_MAP = {"🔴": "critical", "🟠": "high", "🟡": "medium", "🟢": "low"}


def _parse_md_tables(text: str) -> list[dict]:
    items: list[dict] = []
    current_block = "A"

    for line in text.splitlines():
        block_match = re.match(r"^## ([A-HNIJK])\.", line)
        if block_match:
            current_block = block_match.group(1)
            continue

        if not line.startswith("|") or line.startswith("|---") or "# | Sev" in line:
            continue

        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 5 or not re.match(r"^\d{3}$", cols[0]):
            continue

        sev_icon = cols[1]
        items.append(
            {
                "id": cols[0],
                "block": current_block,
                "block_name": BLOCK_NAMES.get(current_block, current_block),
                "severity": SEV_MAP.get(sev_icon, "medium"),
                "scope": cols[2],
                "title": cols[3].replace("**", ""),
                "how": cols[4],
            }
        )
    return items


@lru_cache(maxsize=1)
def load_catalog() -> list[dict]:
    base = _parse_md_tables(CHECKLIST_MD.read_text(encoding="utf-8"))
    nuxt = _parse_md_tables(NUXT_MD.read_text(encoding="utf-8")) if NUXT_MD.exists() else []
    pro = _parse_md_tables(PRO_MD.read_text(encoding="utf-8")) if PRO_MD.exists() else []
    items = base + nuxt + pro
    if len(base) != 100:
        raise ValueError(f"Expected 100 base checklist items, got {len(base)}")
    return items


def catalog_by_id() -> dict[str, dict]:
    return {item["id"]: item for item in load_catalog()}
