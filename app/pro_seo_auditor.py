"""Pro SEO mechanics from forum/community best practices (2025–2026)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

TIMEOUT = 25

AI_BOTS = (
    ("PerplexityBot", "Perplexity citations"),
    ("ClaudeBot", "Anthropic Claude"),
    ("Anthropic-AI", "Anthropic training"),
    ("GPTBot", "OpenAI training"),
    ("ChatGPT-User", "ChatGPT browsing"),
    ("Google-Extended", "Google AI training"),
    ("GoogleOther", "Google auxiliary"),
    ("Applebot-Extended", "Apple Intelligence"),
)

SEARCH_BOTS = (
    ("Googlebot", "Google Search"),
    ("Bingbot", "Bing Search"),
)

SECURITY_HEADERS = (
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "content-security-policy",
)

CONTACT_PATTERNS = (
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    re.compile(r"\+?\d[\d\s().-]{8,}\d"),
)
PRIVACY_PATTERNS = re.compile(r"privacy\s*policy|политик[аи]\s*конфиденциальности", re.I)


@dataclass
class SiteProContext:
    base: str
    robots_text: str = ""
    sitemap_ok: bool = False
    sitemap_in_robots: bool = False
    llms_txt_ok: bool = False
    llms_txt_preview: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    bot_access: dict[str, str] = field(default_factory=dict)
    redirect_chains: dict[str, list[dict]] = field(default_factory=dict)
    page_snapshots: list[dict[str, Any]] = field(default_factory=list)
    duplicate_titles: list[str] = field(default_factory=list)
    duplicate_descriptions: list[str] = field(default_factory=list)
    homepage_html: str = ""
    homepage_visible: str = ""


def _normalize_header_key(h: str) -> str:
    return h.lower().strip()


def parse_robots_access(robots_text: str, user_agent: str) -> str:
    """Return allowed | blocked | unknown for a user-agent."""
    if not robots_text.strip():
        return "allowed"

    blocks: list[tuple[str, list[tuple[str, str]]]] = []
    current_agents: list[str] = []
    current_rules: list[tuple[str, str]] = []

    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("user-agent:"):
            if current_agents:
                blocks.append((",".join(current_agents), list(current_rules)))
            current_agents = [line.split(":", 1)[1].strip()]
            current_rules = []
        elif lower.startswith(("disallow:", "allow:")):
            kind = "disallow" if lower.startswith("disallow") else "allow"
            path = line.split(":", 1)[1].strip()
            current_rules.append((kind, path))

    if current_agents:
        blocks.append((",".join(current_agents), list(current_rules)))

    ua_lower = user_agent.lower()
    matched_rules: list[tuple[str, str]] = []
    wildcard_rules: list[tuple[str, str]] = []

    for agents, rules in blocks:
        agent_list = [a.strip().lower() for a in agents.split(",")]
        if ua_lower in agent_list or "*" in agent_list:
            if "*" in agent_list and ua_lower not in agent_list:
                wildcard_rules = rules
            else:
                matched_rules = rules

    rules = matched_rules or wildcard_rules
    if not rules:
        return "allowed"

    disallow_root = any(k == "disallow" and (p == "/" or p == "/*") for k, p in rules)
    allow_root = any(k == "allow" and p in ("/", "/*") for k, p in rules)
    if disallow_root and not allow_root:
        return "blocked"

    for kind, path in reversed(rules):
        if path == "/" or path == "/*":
            return "blocked" if kind == "disallow" else "allowed"

    return "allowed"


def build_bot_matrix(robots_text: str) -> dict[str, dict[str, str]]:
    matrix: dict[str, dict[str, str]] = {"ai": {}, "search": {}}
    for bot, desc in AI_BOTS:
        matrix["ai"][bot] = parse_robots_access(robots_text, bot)
        matrix["ai"][f"{bot}__desc"] = desc  # type: ignore
    for bot, desc in SEARCH_BOTS:
        matrix["search"][bot] = parse_robots_access(robots_text, bot)
        matrix["search"][f"{bot}__desc"] = desc  # type: ignore
    return matrix


async def trace_redirect_chain(
    client: httpx.AsyncClient, url: str, max_hops: int = 10
) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    current = url
    seen: set[str] = set()

    for _ in range(max_hops):
        if current in seen:
            chain.append({"url": current, "status": "loop", "location": ""})
            break
        seen.add(current)
        try:
            resp = await client.get(current, follow_redirects=False)
        except Exception as exc:
            chain.append({"url": current, "status": "error", "location": str(exc)[:120]})
            break

        hop = {
            "url": current,
            "status": resp.status_code,
            "location": resp.headers.get("location", ""),
        }
        chain.append(hop)

        if resp.status_code not in (301, 302, 303, 307, 308):
            break
        location = resp.headers.get("location")
        if not location:
            break
        current = urljoin(current, location)

    return chain


def _page_meta(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = str(desc_tag["content"]).strip() if desc_tag and desc_tag.get("content") else ""
    h1_el = soup.find("h1")
    h1 = h1_el.get_text(strip=True) if h1_el else ""
    canon = soup.find("link", rel="canonical")
    canonical = str(canon["href"]).strip() if canon and canon.get("href") else ""

    internal = 0
    parsed = urlparse(url)
    base_host = parsed.netloc.lower()
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(url, href)
        if urlparse(full).netloc.lower() == base_host:
            internal += 1

    mixed = len(re.findall(r'(?:src|href)=["\']http://', html, re.I))
    tables = len(soup.find_all("table"))
    faq_schema = any("FAQPage" in s.get_text() for s in soup.find_all("script", type="application/ld+json"))

    ld_names: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text())
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    if "@graph" in item and isinstance(item["@graph"], list):
                        for node in item["@graph"]:
                            if isinstance(node, dict) and node.get("name"):
                                ld_names.append(str(node["name"]))
                    elif item.get("name"):
                        ld_names.append(str(item["name"]))
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "url": url,
        "title": title,
        "description": desc,
        "h1": h1,
        "canonical": canonical,
        "internal_links": internal,
        "mixed_http": mixed,
        "tables": tables,
        "faq_schema": faq_schema,
        "ld_names": ld_names,
    }


def _similar(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_duplicates(snapshots: list[dict[str, Any]], key: str) -> list[str]:
    groups: dict[str, list[str]] = {}
    for snap in snapshots:
        val = (snap.get(key) or "").strip()
        if not val or len(val) < 5:
            continue
        groups.setdefault(val, []).append(snap["url"])
    dups = []
    for val, urls in groups.items():
        if len(urls) > 1:
            dups.append(f"«{val[:60]}…» → {len(urls)} URL: {', '.join(urls[:3])}")
    return dups


def build_priority_roadmap(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_penalty = {"fail": 0, "warn": 1, "manual": 2}

    items = []
    for r in results:
        st = r.get("status")
        if st not in ("fail", "warn"):
            continue
        sev = r.get("severity", "medium")
        if st == "fail" and sev == "critical":
            priority = "P0"
        elif st == "fail" and sev in ("critical", "high"):
            priority = "P1"
        elif st == "fail":
            priority = "P2"
        else:
            priority = "P2" if sev in ("critical", "high") else "P3"

        items.append(
            {
                "id": r.get("id"),
                "priority": priority,
                "severity": sev,
                "status": st,
                "title": r.get("title"),
                "block": r.get("block"),
                "evidence": (r.get("evidence") or "")[:200],
                "sort": (sev_order.get(sev, 9), status_penalty.get(st, 9), r.get("id", "")),
            }
        )

    items.sort(key=lambda x: x["sort"])
    for it in items:
        it.pop("sort", None)
    return items


def evaluate_pro_item(item_id: str, ctx: SiteProContext, page: dict[str, Any]) -> dict[str, Any]:
    """Evaluate checklist items 121–145."""
    snap = page
    url = snap.get("url", "")
    chain = ctx.redirect_chains.get(url, [])
    headers = {k.lower(): v for k, v in ctx.headers.items()}
    bots = ctx.bot_access

    def ok(msg: str) -> dict[str, Any]:
        return {"status": "pass", "evidence": msg}

    def warn(msg: str) -> dict[str, Any]:
        return {"status": "warn", "evidence": msg}

    def fail(msg: str) -> dict[str, Any]:
        return {"status": "fail", "evidence": msg}

    def manual(msg: str) -> dict[str, Any]:
        return {"status": "manual", "evidence": msg}

    if item_id == "121":
        if ctx.llms_txt_ok:
            return ok(f"llms.txt OK: {ctx.llms_txt_preview[:80]}")
        return fail("Нет /llms.txt или пустой ответ — AI crawlers без structured hint")

    if item_id == "122":
        st = bots.get("PerplexityBot", "unknown")
        if st == "allowed":
            return ok("PerplexityBot: allowed")
        if st == "blocked":
            return fail("PerplexityBot заблокирован — потеря Perplexity citations")
        return warn("PerplexityBot: неявная политика (нет правил)")

    if item_id == "123":
        claude = bots.get("ClaudeBot", "unknown")
        anth = bots.get("Anthropic-AI", "unknown")
        if claude == "blocked" or anth == "blocked":
            return fail(f"ClaudeBot={claude}, Anthropic-AI={anth}")
        if claude == "allowed" and anth == "allowed":
            return ok("Claude crawlers: allowed")
        return warn(f"ClaudeBot={claude}, Anthropic-AI={anth}")

    if item_id == "124":
        gpt = bots.get("GPTBot", "unknown")
        chat = bots.get("ChatGPT-User", "unknown")
        if gpt == "blocked" and chat == "blocked":
            return ok("GPTBot + ChatGPT-User заблокированы (осознанный opt-out training)")
        if gpt == "blocked" or chat == "blocked":
            return warn(f"Частичная блокировка: GPTBot={gpt}, ChatGPT-User={chat}")
        return ok(f"GPTBot={gpt}, ChatGPT-User={chat}")

    if item_id == "125":
        ge = bots.get("Google-Extended", "unknown")
        go = bots.get("GoogleOther", "unknown")
        if ge == "blocked":
            return ok("Google-Extended blocked — training opt-out, Googlebot отдельно")
        return warn(f"Google-Extended={ge}, GoogleOther={go} — проверь training policy")

    if item_id == "126":
        st = bots.get("Applebot-Extended", "unknown")
        if st == "allowed":
            return ok("Applebot-Extended: allowed")
        if st == "blocked":
            return warn("Applebot-Extended blocked — нет Apple Intelligence citations")
        return ok("Applebot-Extended: implicit allow")

    if item_id == "127":
        if snap.get("faq_schema"):
            return ok("FAQPage schema найден")
        return warn("Нет FAQPage schema — AI engines хуже извлекают Q&A")

    if item_id == "128":
        n = snap.get("tables", 0)
        if n >= 1:
            return ok(f"HTML tables: {n}")
        return warn("Нет data tables — ниже AI citability (forum: 4x citations с таблицами)")

    if item_id == "129":
        hsts = headers.get("strict-transport-security")
        if hsts:
            return ok(f"HSTS: {hsts[:60]}")
        return fail("Нет Strict-Transport-Security")

    if item_id == "130":
        xcto = headers.get("x-content-type-options", "")
        if "nosniff" in xcto.lower():
            return ok("X-Content-Type-Options: nosniff")
        return fail("Нет X-Content-Type-Options: nosniff")

    if item_id == "131":
        xfo = headers.get("x-frame-options")
        csp = headers.get("content-security-policy", "")
        if xfo or "frame-ancestors" in csp:
            return ok("Clickjacking protection OK")
        return fail("Нет X-Frame-Options / CSP frame-ancestors")

    if item_id == "132":
        csp = headers.get("content-security-policy")
        if csp and len(csp) > 10:
            return ok(f"CSP задан ({len(csp)} chars)")
        return warn("CSP отсутствует — grade ниже A на securityheaders.com")

    if item_id == "133":
        mixed = snap.get("mixed_http", 0)
        if mixed == 0:
            return ok("Mixed content не найден")
        return fail(f"Mixed content: {mixed} http:// ресурсов на HTTPS")

    if item_id == "134":
        text = ctx.homepage_visible.lower()
        if PRIVACY_PATTERNS.search(text) or PRIVACY_PATTERNS.search(ctx.homepage_html):
            return ok("Privacy policy упоминается на homepage")
        return warn("Privacy policy не найден в footer/homepage")

    if item_id == "135":
        text = ctx.homepage_visible
        if any(p.search(text) for p in CONTACT_PATTERNS):
            return ok("Контакт (email/phone) найден")
        return warn("Контакты не обнаружены на homepage")

    if item_id == "136":
        hops = [h for h in chain if isinstance(h.get("status"), int) and h["status"] in (301, 302, 303, 307, 308)]
        if any(h.get("status") == "loop" for h in chain):
            return fail("Redirect loop")
        if len(hops) <= 2:
            return ok(f"Redirect hops: {len(hops)}")
        return fail(f"Redirect chain {len(hops)} hops (>2): {' → '.join(h['url'][:40] for h in chain[:4])}")

    if item_id == "137":
        if any(h.get("status") == "loop" for h in chain):
            return fail("Redirect loop detected")
        return ok("Redirect loop нет")

    if item_id == "138":
        temp = [h for h in chain if h.get("status") in (302, 303, 307)]
        if temp:
            return warn(f"Временные редиректы: {len(temp)}× (302/303/307)")
        return ok("Permanent redirects или без редиректа")

    if item_id == "139":
        if ctx.duplicate_titles:
            return fail(ctx.duplicate_titles[0])
        return ok("Title уникален среди проверенных страниц")

    if item_id == "140":
        if ctx.duplicate_descriptions:
            return fail(ctx.duplicate_descriptions[0])
        return ok("Description уникален среди проверенных страниц")

    if item_id == "141":
        h1 = snap.get("h1") or snap.get("title") or ""
        names = snap.get("ld_names") or []
        if not names:
            return manual("Нет JSON-LD name для сравнения")
        best = max(_similar(h1, n) for n in names)
        if best >= 0.4:
            return ok(f"Schema↔H1 similarity: {best:.0%}")
        return fail(f"Schema drift: H1 «{h1[:40]}» vs LD «{names[0][:40]}» ({best:.0%})")

    if item_id == "142":
        n = snap.get("internal_links", 0)
        if n >= 3:
            return ok(f"Internal links: {n}")
        if n >= 1:
            return warn(f"Internal links: {n} (<3)")
        return fail("Нет internal links на странице")

    if item_id == "143":
        if ctx.sitemap_ok and ctx.sitemap_in_robots:
            return ok("sitemap.xml 200 + указан в robots.txt")
        if ctx.sitemap_ok:
            return warn("sitemap.xml OK, но не в robots.txt")
        return fail("sitemap.xml недоступен")

    if item_id == "144":
        canon = snap.get("canonical") or ""
        if not canon:
            return fail("Нет canonical")
        if urlparse(canon).path.rstrip("/") == urlparse(url).path.rstrip("/"):
            return ok("Self-referencing canonical")
        return warn(f"Canonical указывает на другой path: {canon[:80]}")

    if item_id == "145":
        st = bots.get("Googlebot", "unknown")
        if st == "allowed":
            return ok("Googlebot: allowed")
        if st == "blocked":
            return fail("Googlebot заблокирован — критично для SEO")
        return warn("Googlebot: implicit allow")

    return manual(f"Pro item {item_id} не реализован")


async def build_site_pro_context(
    client: httpx.AsyncClient,
    base: str,
    page_urls: list[str],
    robots_text: str = "",
) -> SiteProContext:
    ctx = SiteProContext(base=base, robots_text=robots_text)

    try:
        r = await client.get(f"{base}/")
        ctx.homepage_html = r.text
        soup = BeautifulSoup(r.text, "lxml")
        ctx.homepage_visible = soup.get_text("\n", strip=True)
        ctx.headers = {_normalize_header_key(k): v for k, v in r.headers.items()}
    except Exception:
        pass

    if not robots_text:
        try:
            rr = await client.get(f"{base}/robots.txt")
            if rr.status_code == 200:
                ctx.robots_text = rr.text
        except Exception:
            pass
    else:
        ctx.robots_text = robots_text

    ctx.bot_access = {}
    for bot, _ in AI_BOTS + SEARCH_BOTS:
        ctx.bot_access[bot] = parse_robots_access(ctx.robots_text, bot)

    ctx.sitemap_in_robots = "sitemap" in ctx.robots_text.lower()
    try:
        sm = await client.get(f"{base}/sitemap.xml")
        ctx.sitemap_ok = sm.status_code == 200 and "<" in sm.text[:500]
    except Exception:
        ctx.sitemap_ok = False

    try:
        lm = await client.get(f"{base}/llms.txt")
        if lm.status_code == 200 and len(lm.text.strip()) > 20:
            ctx.llms_txt_ok = True
            ctx.llms_txt_preview = lm.text.strip()[:200]
    except Exception:
        pass

    snapshots = []
    for url in page_urls:
        try:
            resp = await client.get(url)
            snapshots.append(_page_meta(resp.text, str(resp.url)))
            ctx.redirect_chains[url] = await trace_redirect_chain(client, url)
        except Exception as exc:
            snapshots.append({"url": url, "error": str(exc)[:80]})
            ctx.redirect_chains[url] = [{"url": url, "status": "error", "location": str(exc)[:80]}]

    ctx.page_snapshots = snapshots
    ctx.duplicate_titles = find_duplicates(snapshots, "title")
    ctx.duplicate_descriptions = find_duplicates(snapshots, "description")
    return ctx


async def run_pro_audit(pages: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Full pro report for /pro dashboard."""
    from app.config_loader import load_config

    cfg = load_config()
    seo_pages = pages or (cfg.get("seo") or {}).get("pages") or []
    html_pages = [p for p in seo_pages if p.get("type", "html") == "html"]
    if not html_pages:
        return {"error": "Нет HTML-страниц в config"}

    first_url = html_pages[0]["url"]
    parsed = urlparse(first_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    urls = [p["url"] for p in html_pages]

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        robots = ""
        try:
            rr = await client.get(f"{base}/robots.txt")
            if rr.status_code == 200:
                robots = rr.text
        except Exception:
            pass
        ctx = await build_site_pro_context(client, base, urls, robots)

    bot_matrix = build_bot_matrix(ctx.robots_text)
    security = {
        h: ctx.headers.get(h, "—") for h in SECURITY_HEADERS
    }

    from app.bot_reality_check import run_bot_reality_check

    bot_reality = await run_bot_reality_check(first_url, ctx.robots_text)

    return {
        "error": None,
        "base": base,
        "pages_scanned": len(urls),
        "bot_matrix": bot_matrix,
        "bot_reality": bot_reality,
        "security_headers": security,
        "llms_txt": {"ok": ctx.llms_txt_ok, "preview": ctx.llms_txt_preview},
        "sitemap": {"ok": ctx.sitemap_ok, "in_robots": ctx.sitemap_in_robots},
        "duplicate_titles": ctx.duplicate_titles,
        "duplicate_descriptions": ctx.duplicate_descriptions,
        "redirect_chains": ctx.redirect_chains,
        "page_snapshots": ctx.page_snapshots,
        "bot_access_flat": ctx.bot_access,
    }


def pro_report_markdown(report: dict[str, Any], roadmap: list[dict[str, Any]]) -> str:
    lines = [
        "# Pro SEO Report",
        "",
        f"**Site:** {report.get('base')}",
        f"**Pages scanned:** {report.get('pages_scanned')}",
        "",
        "## AI Crawler Matrix",
        "",
        "| Bot | Status |",
        "|-----|--------|",
    ]
    for bot, st in (report.get("bot_access_flat") or {}).items():
        lines.append(f"| {bot} | {st} |")

    lines.extend(["", "## Security Headers", ""])
    for h, v in (report.get("security_headers") or {}).items():
        lines.append(f"- **{h}:** `{v[:80] if v != '—' else '—'}`")

    if report.get("duplicate_titles"):
        lines.extend(["", "## Duplicate Titles", ""])
        for d in report["duplicate_titles"]:
            lines.append(f"- {d}")

    lines.extend(["", "## Priority Roadmap", ""])
    for item in roadmap[:30]:
        lines.append(
            f"- **{item['priority']}** [{item['id']}] {item['title']} — _{item['evidence'][:100]}_"
        )
    return "\n".join(lines)
