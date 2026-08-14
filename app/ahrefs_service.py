"""Ahrefs weekly link intelligence + designer brief export."""

from __future__ import annotations

import csv
import io
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.ahrefs_client import (
    AhrefsError,
    fetch_backlinks_stats,
    fetch_domain_rating,
    fetch_new_backlinks,
    fetch_new_refdomains,
    fetch_organic_metrics,
)
from app.config_loader import DATA_DIR, ahrefs_api_key, load_config
from app.storage import finish_ahrefs_run, start_ahrefs_run

logger = logging.getLogger(__name__)

SPAM_ANCHOR_RE = re.compile(
    r"black\s*hat|telegram|@\w+|seo\s*backlink|ranking\s*↑|casino\s*spam",
    re.I,
)
SPAM_DOMAIN_RE = re.compile(
    r"backlink|serpboost|linkbuilding|pbn|\.info$|\.asia$|seoexpress|ranking-boost|"
    r"traffic-growth|guest-post|link-equity|organic-traffic-and-outreach",
    re.I,
)

EXPORTS_DIR = DATA_DIR / "exports"


def ahrefs_config() -> dict[str, Any]:
    cfg = load_config()
    return (cfg.get("ahrefs") or {}) | {"domain": (cfg.get("seo") or {}).get("domain")}


def week_period(anchor: date | None = None) -> tuple[str, str]:
    """Monday→today window for weekly report."""
    today = anchor or date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat(), today.isoformat()


def _page_bucket(url_to: str, domain: str) -> str:
    path = urlparse(url_to).path.lower()
    if path in ("", "/"):
        return "homepage"
    if "/blog/" in path or "/news/" in path:
        return "blog"
    if "/exchange-" in path or "/swap-" in path:
        return "exchange"
    if "/premium" in path or "/vip" in path:
        return "premium"
    if domain and domain not in url_to:
        return "other"
    return "content"


def classify_link(link: dict[str, Any], domain: str) -> dict[str, Any]:
    dr = float(link.get("domain_rating_source") or 0)
    anchor = (link.get("anchor") or "").strip()
    url_from = link.get("url_from") or ""
    url_to = link.get("url_to") or ""
    is_dofollow = bool(link.get("is_dofollow"))
    from_host = urlparse(url_from).netloc.lower()

    spam = bool(
        SPAM_ANCHOR_RE.search(anchor)
        or (dr < 3 and SPAM_DOMAIN_RE.search(from_host))
        or len(anchor) > 120
    )
    quality = dr >= 15 and is_dofollow and not spam
    notable = dr >= 8 and is_dofollow and not spam

    return {
        **link,
        "dr": dr,
        "bucket": _page_bucket(url_to, domain),
        "is_spam": spam,
        "is_quality": quality,
        "is_notable": notable,
    }


def classify_refdomain(rd: dict[str, Any]) -> dict[str, Any]:
    dr = float(rd.get("domain_rating") or 0)
    domain = (rd.get("domain") or "").lower()
    spam = bool(SPAM_DOMAIN_RE.search(domain)) or (dr < 5 and domain.endswith(".shop"))
    return {**rd, "dr": dr, "is_spam": spam, "is_quality": dr >= 15 and not spam}


def build_designer_brief(payload: dict[str, Any]) -> str:
    cfg = ahrefs_config()
    site = (load_config().get("seo") or {}).get("site_name") or payload.get("target", "site")
    period = payload.get("period") or {}
    metrics = payload.get("metrics") or {}
    summary = payload.get("summary") or {}
    quality = payload.get("quality_links") or []
    notable = payload.get("notable_links") or []
    by_bucket: dict[str, list] = payload.get("links_by_bucket") or {}
    spam_count = summary.get("spam_links", 0)

    dr_val = metrics.get("domain_rating", "—")
    live_bl = metrics.get("live_backlinks")
    live_rd = metrics.get("live_refdomains")
    lines = [
        f"# Ahrefs · еженедельный бриф для дизайна — {site}",
        "",
        f"**Период:** {period.get('from')} → {period.get('to')}  ",
        f"**Сформирован:** {payload.get('generated_at', '')[:19].replace('T', ' ')} UTC",
        "",
        "## Сводка",
        "",
        f"- **Domain Rating:** {dr_val}",
        f"- **Живых ссылок:** {live_bl:,}" if live_bl is not None else "- **Живых ссылок:** —",
        f"- **Referring domains:** {live_rd:,}" if live_rd is not None else "- **Referring domains:** —",
        f"- **Органический трафик (оценка):** {metrics.get('org_traffic', '—')}",
        f"- **Ключевых слов в топе:** {metrics.get('org_keywords', '—')}",
        f"- **Новых ссылок за неделю:** {summary.get('new_links', 0)}",
        f"- **Новых доменов:** {summary.get('new_refdomains', 0)}",
        f"- **Качественных (DR≥15, dofollow):** {summary.get('quality_links', 0)}",
        f"- **Спам / риск:** {spam_count}",
        "",
        "## Что важно для дизайна",
        "",
    ]

    actions = []
    if by_bucket.get("homepage"):
        actions.append(
            f"- **Главная** получила {len(by_bucket['homepage'])} новых ссылок — проверь hero, trust-блоки, OG-превью."
        )
    if by_bucket.get("exchange"):
        pairs = sorted({urlparse(l.get("url_to", "")).path for l in by_bucket["exchange"]})[:5]
        actions.append(
            f"- **Страницы обмена** ({len(by_bucket['exchange'])} ссылок): {', '.join(pairs)} — актуальны OG/Twitter-карточки."
        )
    if by_bucket.get("blog"):
        actions.append(
            f"- **Блог/контент** ({len(by_bucket['blog'])} ссылок) — можно усилить иллюстрации и share-превью."
        )
    if quality:
        actions.append(
            f"- **{len(quality)} качественных ссылок** — кандидаты для блока «Нас упоминают» / social proof на лендинге."
        )
    if not actions:
        actions.append("- За неделю нет заметных ссылок на ключевые страницы — фокус на контент и визуал без срочных правок.")
    lines.extend(actions)
    lines.append("")

    if quality:
        lines.extend(["## Качественные ссылки (DR≥15, dofollow)", ""])
        for link in quality[:15]:
            lines.append(
                f"- **DR {link['dr']:.0f}** · [{urlparse(link['url_from']).netloc}]({link['url_from']})  \n"
                f"  → `{link.get('url_to', '')}`  \n"
                f"  Анкор: _{link.get('anchor') or '—'}_"
            )
        lines.append("")

    if notable and len(notable) > len(quality):
        lines.extend(["## Заметные ссылки (DR≥8)", ""])
        for link in notable[:10]:
            if link.get("is_quality"):
                continue
            lines.append(
                f"- DR {link['dr']:.0f} · {urlparse(link['url_from']).netloc} → {link.get('url_to', '')}"
            )
        lines.append("")

    quality_rds = payload.get("quality_refdomains") or []
    if quality_rds:
        lines.extend(["## Новые качественные домены", ""])
        for rd in quality_rds[:10]:
            lines.append(f"- **DR {rd['dr']:.0f}** · {rd.get('domain')} ({rd.get('links_to_target', 1)} ссылок)")
        lines.append("")

    if spam_count:
        lines.extend([
            "## Спам / риск (для SEO, не для дизайна)",
            "",
            f"Обнаружено **{spam_count}** подозрительных ссылок. Полный список — в CSV-выгрузке.",
            "",
        ])

    min_dr = cfg.get("quality_dr_min", 15)
    lines.extend([
        "---",
        "",
        f"_Автоотчёт Marketing SEO Booster · порог качества DR≥{min_dr}_",
        "_Отправь этот файл в дизайн вместе с CSV при еженедельном созвоне._",
    ])
    return "\n".join(lines)


def build_links_csv(links: list[dict[str, Any]]) -> str:
    fields = [
        "first_seen",
        "dr",
        "is_dofollow",
        "is_quality",
        "is_spam",
        "bucket",
        "url_from",
        "url_to",
        "anchor",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for link in links:
        writer.writerow({k: link.get(k, "") for k in fields})
    return buf.getvalue()


def _save_export_files(payload: dict[str, Any], md: str, csv_content: str) -> dict[str, str]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    period_to = (payload.get("period") or {}).get("to") or date.today().isoformat()
    slug = (payload.get("target") or "site").replace(".", "_")
    base = f"{slug}_ahrefs_design_{period_to}"
    md_path = EXPORTS_DIR / f"{base}.md"
    csv_path = EXPORTS_DIR / f"{base}.csv"
    md_path.write_text(md, encoding="utf-8")
    csv_path.write_text(csv_content, encoding="utf-8")
    return {"md": str(md_path), "csv": str(csv_path), "md_name": md_path.name, "csv_name": csv_path.name}


async def run_ahrefs_weekly(trigger: str = "manual") -> dict[str, Any]:
    if not ahrefs_api_key():
        return {"error": "AHREFS_API_KEY не задан в .env", "results": None}

    cfg = ahrefs_config()
    target = cfg.get("domain") or (load_config().get("seo") or {}).get("domain")
    if not target:
        return {"error": "Домен не задан в config (seo.domain)", "results": None}

    mode = cfg.get("mode") or "domain"
    link_limit = int(cfg.get("link_limit") or 200)
    refdomain_limit = int(cfg.get("refdomain_limit") or 100)
    date_from, date_to = week_period()

    run_id = start_ahrefs_run(target, date_from, date_to, trigger)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            dr_data, bl_stats, org_metrics, raw_links, raw_rds = await _gather(
                client,
                target,
                mode,
                date_from,
                link_limit,
                refdomain_limit,
            )
    except AhrefsError as exc:
        finish_ahrefs_run(run_id, {"error": str(exc), "summary": {"status": "fail"}})
        return {"run_id": run_id, "error": str(exc)}

    classified = [classify_link(lnk, target) for lnk in raw_links]
    refdomains = [classify_refdomain(rd) for rd in raw_rds]

    quality_links = [l for l in classified if l["is_quality"]]
    notable_links = [l for l in classified if l["is_notable"]]
    spam_links = [l for l in classified if l["is_spam"]]
    quality_rds = [rd for rd in refdomains if rd["is_quality"]]

    by_bucket: dict[str, list] = {}
    for link in classified:
        by_bucket.setdefault(link["bucket"], []).append(link)

    metrics = {
        "domain_rating": dr_data.get("domain_rating"),
        "ahrefs_rank": dr_data.get("ahrefs_rank"),
        "live_backlinks": bl_stats.get("live"),
        "live_refdomains": bl_stats.get("live_refdomains"),
        "all_time_backlinks": bl_stats.get("all_time"),
        "org_traffic": org_metrics.get("org_traffic"),
        "org_keywords": org_metrics.get("org_keywords"),
        "org_keywords_top3": org_metrics.get("org_keywords_1_3"),
    }

    summary = {
        "status": "ok",
        "new_links": len(classified),
        "new_refdomains": len(refdomains),
        "quality_links": len(quality_links),
        "notable_links": len(notable_links),
        "spam_links": len(spam_links),
        "dofollow_links": sum(1 for l in classified if l.get("is_dofollow")),
    }

    payload: dict[str, Any] = {
        "target": target,
        "period": {"from": date_from, "to": date_to},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trigger": trigger,
        "metrics": metrics,
        "summary": summary,
        "links": classified,
        "refdomains": refdomains,
        "quality_links": quality_links,
        "notable_links": notable_links,
        "quality_refdomains": quality_rds,
        "links_by_bucket": {k: v for k, v in by_bucket.items()},
    }

    md = build_designer_brief(payload)
    csv_content = build_links_csv(classified)
    files = _save_export_files(payload, md, csv_content)
    payload["export_files"] = files
    payload["designer_brief_md"] = md

    finish_ahrefs_run(run_id, payload)
    return {"run_id": run_id, "error": None, "summary": summary, "metrics": metrics, "export_files": files}


async def _gather(
    client: httpx.AsyncClient,
    target: str,
    mode: str,
    since: str,
    link_limit: int,
    refdomain_limit: int,
):
    import asyncio

    return await asyncio.gather(
        fetch_domain_rating(client, target),
        fetch_backlinks_stats(client, target, mode),
        fetch_organic_metrics(client, target, mode),
        fetch_new_backlinks(client, target, since, mode=mode, limit=link_limit),
        fetch_new_refdomains(client, target, since, mode=mode, limit=refdomain_limit),
    )
