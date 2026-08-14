# Roadmap: 5 Pro Features (Forum + LinkedIn Research)

> Источники: r/TechSEO, r/SEO, WebmasterWorld patterns, Search Engine Land,
> LinkedIn posts (Twinkle Das, Sanjay Shankar, Kashmala Malik/HigherGEO, Anthony Lee GEO audit),
> Fractl AI Search Vocabulary 2026, JetOctopus log analysis, claude-seo/seo-drift ecosystem.

## Что говорят форумы (EN) vs LinkedIn

| Тема | Reddit / TechSEO | LinkedIn |
|------|------------------|----------|
| GEO/AEO | Скепсис, «buzzwords» (111 upvotes hostile thread) | Позитив, продукты, agency workflows |
| AI visibility | «Fix technical first» | Citation tracking, entity coverage, LLM readability |
| #1 blind spot | JS rendering gaps, crawl budget waste | **robots.txt allows bot, CDN blocks 403** |
| Automation | Log files, Screaming Frog, migrations | n8n agents, GSC+AI audit pipelines |
| Metrics shift | Indexing, CWV/INP, log ground truth | Share of Voice in ChatGPT/Perplexity |
| Drift | Deploy breaks canonical/noindex/schema | **seo-drift = «git for SEO»**, CI gates |

**Вывод:** LinkedIn продаёт GEO-нарратив; форумы требуют доказуемую инфраструктуру.
Лучший продукт для про = **technical truth + AI citation layer + drift over time**.

---

## Feature 1: AI Citation Radar 🎯

**Идея:** Прогон 8–12 «buyer queries» из config через Kie (GPT, Claude, Perplexity, Gemini).
Фиксируем: cited URLs, упоминание нашего домена, конкуренты, snippet ответа.

**Зачем (LinkedIn):** Anthony Lee framework — «Would an AI cite this page?»;
85% brand mentions идут с external domains (AirOps study).

**Что уже есть:** Kie models, pro AI bot matrix.
**Что добавить:** `citation_probe.py`, queries в config, dashboard `/citations`, history SQLite.

**Effort:** M (2–3 дня) · **Impact:** 🔥🔥🔥 для Quickex/crypto

---

## Feature 2: SEO Drift Guard 📉

**Идея:** Baseline snapshot 13–17 SEO-полей (title, canonical, robots, schema hash, H1[], OG, CWV).
После деплоя — diff с severity CRITICAL/WARN/INFO. Exit code ≠0 для CI.

**Зачем:** #1 LinkedIn pattern (seo-drift, claude-seo v1.9); форумы — «migration breaks SEO silently».

**Что уже есть:** checklist runs в SQLite, pro audit.
**Что добавить:** `drift_monitor.py`, `POST /api/drift/baseline`, `compare`, trend chart.

**Effort:** M (2 дня) · **Impact:** 🔥🔥🔥 для prod Quickex/Nuxt deploys

---

## Feature 3: Bot Access Reality Test 🛡️

**Идея:** Не только parse robots.txt — **реальный GET** с UA GPTBot, ClaudeBot, PerplexityBot
vs normal Chrome. Сравнение status/body length/Cloudflare challenge.

**Зачем (LinkedIn/Kashmala Malik):** «#1 issue: teams allow bots in robots while CDN returns 403».

**Что уже есть:** AI bot matrix (robots only).
**Что добавить:** `bot_reality_check.py`, matrix column «HTTP reality», alert on mismatch.

**Effort:** S (1 день) · **Impact:** 🔥🔥 — быстрый win, уникально vs Screaming Frog

---

## Feature 4: Citability / GEO Score Engine 📊

**Идея:** Per-page score 0–100 по форумным/Princeton GEO сигналам:
- answer capsule (первый абзац)
- stats/numbers in content
- FAQ + FAQPage schema match
- H2 as questions
- HTML tables
- author + dateModified
- entity-clear language (names vs pronouns)
- quotable sentences (LLM extract test via Kie optional)

**Зачем:** LinkedIn HigherGEO, Princeton +40% visibility with citations/stats;
Twinkle Das n8n audit — «LLM readability as native dimension».

**Что уже есть:** checklist items 127–128, partial schema drift.
**Что добавить:** `citability_scorer.py`, block L in checklist, `/geo` page heatmap.

**Effort:** M–L (3–4 дня) · **Impact:** 🔥🔥 для content/LQA команды Quickex

---

## Feature 5: Render Gap Lab (Nuxt/SPA) 🔬

**Иdea:** Side-by-side: curl HTML vs Playwright rendered DOM.
Diff: H1, title, meta, internal links count, JSON-LD, visible word count.

**Зачем (r/TechSEO):** «AI bots don't render JS»; JetOctopus — JS vs non-JS crawl gaps;
Quickex = Nuxt — highest ROI for this project.

**Что уже есть:** Nuxt block N (101–120), view-source checks.
**Что добавить:** Playwright optional dep, `render_gap.py`, report per URL.

**Effort:** L (3–5 дней, Playwright) · **Impact:** 🔥🔥🔥 для Nuxt stack

---

## Recommended build order

| Phase | Feature | Why first |
|-------|---------|-----------|
| **1** | Bot Access Reality Test | 1 day, fixes blind spot in current /pro |
| **2** | SEO Drift Guard | Leverages existing SQLite, high pro value |
| **3** | AI Citation Radar | Uses Kie API you already pay for |
| **4** | Citability Score | Extends checklist for content team |
| **5** | Render Gap Lab | Heaviest; max value for Quickex Nuxt |

## Out of scope (v2 candidates)

- Log file upload analyzer (JetOctopus-class)
- GSC OAuth integration (needs Google credentials)
- SERP cluster / topical authority graph
- Entity SameAs vs LinkedIn/Crunchbase live check
