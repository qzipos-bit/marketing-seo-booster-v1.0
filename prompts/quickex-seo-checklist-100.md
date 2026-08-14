# Quickex — SEO Checklist (100 критериев)

> Профессиональный чеклист для аудита quickex.io на основе `quickex-seo-audit.md`.  
> **Как пользоваться:** для каждой страницы / локали пройди все применимые пункты.  
> Отметки: ✅ Pass · ⚠️ Warn · ❌ Fail · ➖ N/A (не применимо к типу страницы)

**Legenda severity:** 🔴 CRITICAL · 🟠 HIGH · 🟡 MEDIUM · 🟢 LOW

**Типы страниц:** `ALL` · `EX` exchange · `HP` homepage · `PR` premium · `SITE` site-level

---

## A. Technical SEO & Crawlability (001–020)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 001 | 🔴 | ALL | Целевой URL отдаёт **HTTP 200** (не 404/410/5xx) | curl -I / DevTools Network | |
| 002 | 🔴 | ALL | **Final URL** после редиректов совпадает с canonical (нет лишних hop) | Trace redirect chain | |
| 003 | 🔴 | ALL | Страница **indexable**: нет `noindex` на money-page | meta robots / X-Robots-Tag | |
| 004 | 🟠 | ALL | **Canonical** присутствует и self-referencing | `<link rel="canonical">` | |
| 005 | 🔴 | EX | Canonical указывает на **ту же пару и язык** (не другую пару) | Сравнить slug в URL | |
| 006 | 🟠 | ALL | **HTTPS** везде; нет mixed content (http assets) | DevTools Console | |
| 007 | 🟠 | SITE | Единый хост: **www vs non-www** — один канон, второй 301 | curl оба варианта | |
| 008 | 🟡 | ALL | **Trailing slash** политика единообразна (со slash или без) | Сравнить дубли URL | |
| 009 | 🟠 | SITE | **robots.txt** доступен (200) и не содержит `Disallow: /` | /robots.txt | |
| 010 | 🟠 | SITE | **Sitemap** указан в robots.txt (`Sitemap:` directive) | robots.txt | |
| 011 | 🟠 | SITE | **sitemap.xml** доступен (200), валидный XML | /sitemap.xml | |
| 012 | 🟡 | EX | URL страницы **присутствует в sitemap** (или child sitemap) | grep URL в sitemap | |
| 013 | 🔴 | ALL | Контент **SSR/пререндер** — в HTML есть H1 и основной текст (не пустой shell) | View Source / curl | |
| 014 | 🟠 | ALL | **Viewport** meta для mobile (`width=device-width`) | `<meta name="viewport">` | |
| 015 | 🟡 | ALL | **Charset UTF-8** задан | `<meta charset="utf-8">` | |
| 016 | 🟡 | ALL | Нет **битых внутренних ссылок** на первом экране и в nav | Link checker / manual | |
| 017 | 🟡 | EX | Slug URL `/exchange-{from}-{to}` **соответствует** монетам на странице | URL vs H1/widget | |
| 018 | 🟠 | ALL | **TTFB / latency** ≤ 3s (warn > 3s, fail > 6s) | DevTools / monitor | |
| 019 | 🟡 | ALL | **Pagination / params** не создают дубли indexable (utm, session) | Canonical + robots | |
| 020 | 🟡 | SITE | **404** страница кастомная, не soft-404 (200 с пустым контентом) | /nonexistent-url | |

---

## B. Meta Tags & Social (021–035)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 021 | 🔴 | ALL | **meta title** [`meta_title`] **не пустой** на indexable URL | `<title>` | |
| 022 | 🟠 | ALL | Длина meta title **45–65 символов** (warn вне диапазона) | Посчитать chars | |
| 023 | 🟠 | EX | Primary keyword **ближе к началу** meta title | Визуально / Ahrefs KW | |
| 024 | 🟡 | ALL | Бренд **Quickex** в title (| Quickex или в конце) — единообразно | Сравнить 3+ страницы | |
| 025 | 🔴 | EX | meta title **уникален** для пары (не copy-paste другой пары) | Diff с соседними парами | |
| 026 | 🟠 | ALL | **meta description** присутствует | `<meta name="description">` | |
| 027 | 🟠 | ALL | Длина description **120–170 символов** | char count | |
| 028 | 🔴 | ALL | Description **не содержит body-copy** (>300 символов = fail) | char count + read | |
| 029 | 🟡 | ALL | Description **не дублирует H1** дословно | diff title vs H1 | |
| 030 | 🟡 | ALL | Description содержит **intent + УТП + мягкий CTA** | Readability | |
| 031 | 🟡 | ALL | **og:title** заполнен и согласован с meta title | OG tags | |
| 032 | 🟡 | ALL | **og:description** заполнен | OG tags | |
| 033 | 🟡 | ALL | **og:image** присутствует, абсолютный URL, ≥200px | OG debugger / HTML | |
| 034 | 🟢 | ALL | **twitter:card** (summary/summary_large_image) задан | meta twitter | |
| 035 | 🟢 | ALL | **twitter:title / description** не пустые | meta twitter | |

---

## C. Content & Page Structure — Exchange (036–060)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 036 | 🔴 | EX | **H1** [`title`] присутствует (ровно один видимый H1) | `<h1>` на live | |
| 037 | 🔴 | EX | H1 содержит **полные имена монет**: `Bitcoin (BTC) to Monero (XMR)` | Read H1 | |
| 038 | 🔴 | EX | H1 **без** шаблона `BTC (BTC)` / `XMR (XMR)` | grep live HTML | |
| 039 | 🟠 | EX | H1 **не дублирует** meta title дословно | diff | |
| 040 | 🟡 | EX | **subtitle / main_subtitle** заполнен, поддерживает intent | Под H1 | |
| 041 | 🟠 | EX | Блок **How-to** (`exchange_pair_section1_title`) — заголовок есть | Scroll / TMS map | |
| 042 | 🟠 | EX | **how_step1–4** — все 4 шага заполнены, без template leak | Visible steps | |
| 043 | 🟠 | EX | **how_text_1–4** (тела шагов) — заполнены, не пустые | Expand steps / HTML | |
| 044 | 🔴 | EX | В how steps **нет** `{instrument`, `BTC (BTC)`, `123`, `1122` | grep | |
| 045 | 🟡 | EX | Блок **Exchange rate today** — title + description | Rate section | |
| 046 | 🟡 | EX | **section_pairs_pair_from** (TOP links) — title + описание | Internal links block | |
| 047 | 🟡 | EX | **section_pairs_pair_to** (BOTTOM links) — title + описание | Internal links block | |
| 048 | 🟡 | EX | Перелинковка ведёт на **валидные** exchange URL | Click 2–3 links | |
| 049 | 🟠 | EX | **FAQ** — минимум 3–5 вопросов видимы | Accordion | |
| 050 | 🟡 | EX | FAQ ответы **уникальны для пары**, не generic placeholder | Read Q/A | |
| 051 | 🟠 | EX | **about_section** — заголовок + subtitle про обе монеты | About block | |
| 052 | 🔴 | EX | About: формат **`Bitcoin (BTC):`** не `BTC (Bitcoin):` | Read about | |
| 053 | 🟡 | EX | **section_why** (benefits) — блок присутствует | Benefits | |
| 054 | 🟡 | EX | **KYC / anonymous** блок (`section3_*`) — честная формулировка | Read section3 | |
| 055 | 🟡 | EX | **Transparent rate** (`section4_*`) — без ложных claim | Read section4 | |
| 056 | 🟡 | EX | **Instant swap** (`section5_*`) — без overclaim speed | Read section5 | |
| 057 | 🟡 | EX | **Reviews / trust** блок виден на странице | Trust widget | |
| 058 | 🟢 | EX | Left nav anchors (`nav_*`) работают (scroll to section) | Click nav | |
| 059 | 🟡 | HP | Homepage: **уникальный H1**, не generic «Crypto Exchange» only | / | |
| 060 | 🟡 | PR | Premium/VIP: meta **не содержит body-copy** в title/description | /premium | |

---

## D. LQA, Brand & TMS Quality (061–075)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 061 | 🔴 | EX | **Направление пары** в тексте совпадает с URL (FROM→TO) | Compare widget vs copy | |
| 062 | 🔴 | RU | В RU-текстах **нет латинского «swap»** (только «обмен») | grep `swap` on /ru/ | |
| 063 | 🟠 | EX | **EN↔RU parity**: смысл совпадает, нет противоречий | Side-by-side EN/RU | |
| 064 | 🔴 | ALL | **Комиссии** в тексте: Fixed 1% / Floating 0.5% — без выдуманных цифр | grep fee % | |
| 065 | 🟠 | ALL | **KYC claim** честный: без KYC для стандартных сумм, не «100% anonymous» | Read KYC block | |
| 066 | 🟠 | EX | Privacy-пары (btc-xmr): **нет overclaim** («untraceable», «100%») | Read copy | |
| 067 | 🟠 | EX | **Нейминг сети**: `Tether (TRC20)` не `USDT (USDT)` | Token names | |
| 068 | 🟡 | EX | TMS **meta_title** заполнен (не null → шаблон на live) | TMS GET vs live | |
| 069 | 🟡 | EX | TMS **meta_description** заполнен | TMS GET | |
| 070 | 🟡 | EX | TMS **title (H1)** override есть на high-risk паре | TMS GET | |
| 071 | 🟢 | EX | **nav_how_to_swap_title** — не трогаем без запроса (DEFER) | Mark N/A unless audit | |
| 072 | 🟢 | EX | **how_step2** «Provide … address» — DEFER, не fail | Mark N/A unless audit | |
| 073 | 🟢 | EX | **«Step N.»** prefix в how_step — DEFER | Mark N/A unless audit | |
| 074 | 🟡 | ALL | Нет **опечаток бренда**: Quickex, не Quicex / QuickEx | grep | |
| 075 | 🟡 | ALL | **Non-custodial** messaging согласован (не «мы храним») | Read trust copy | |

---

## E. Keywords, Intent & Competitors (076–085)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 076 | 🟠 | EX | **Primary KW** (Ahrefs top) в meta title — естественно | Ahrefs + title | |
| 077 | 🟠 | EX | Primary KW в **H1** или первом абзаце | Read above fold | |
| 078 | 🟡 | EX | **Secondary / LSI** в FAQ или about (2+ вхождения) | Read FAQ/about | |
| 079 | 🟡 | EX | Нет **keyword stuffing** (один KW >5× подряд) | Read / count | |
| 080 | 🟡 | EX | Privacy intent: **anonymous / no KYC / fast** — уместно для xmr-пар | Intent match | |
| 081 | 🟡 | EX | **Search intent** (informational vs transactional) соответствует типу страницы | SERP analysis | |
| 082 | 🟡 | EX | **Gap vs ChangeNOW**: структура блоков не слабее (how/FAQ/about) | competitor_scans | |
| 083 | 🟡 | EX | **Gap vs Changelly**: meta/H1 покрывают top KW | competitor_scans | |
| 084 | 🟢 | EX | Title/description **не копируют** конкурента дословно | diff competitor | |
| 085 | 🟡 | EX | **Long-tail** из PAA закрыт минимум 1 FAQ | Compare PAA vs FAQ | |

---

## F. Structured Data & Rich Results (086–090)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 086 | 🟡 | ALL | **JSON-LD** присутствует (`application/ld+json`) | View Source | |
| 087 | 🟡 | EX | **FAQPage** schema есть, если FAQ виден | Rich Results Test | |
| 088 | 🟡 | EX | FAQ schema **matches** видимым Q/A (нет hidden FAQ only in schema) | Compare | |
| 089 | 🟡 | SITE | **Organization / WebSite** schema на homepage или global | JSON-LD types | |
| 090 | 🟡 | ALL | JSON-LD **валидный JSON** (нет syntax error) | Parser / validator | |

---

## G. i18n & Hreflang (091–095)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 091 | 🟠 | EX | **hreflang** теги присутствуют для языковых версий | link rel=alternate | |
| 092 | 🟠 | EX | **x-default** hreflang задан | hreflang=x-default | |
| 093 | 🔴 | EX | hreflang **reciprocal** (ru↔en ссылаются друг на друга) | Check pair langs | |
| 094 | 🟠 | EX | hreflang URL **200** и тот же path пары | curl each lang | |
| 095 | 🟡 | EX | Контент **локализован**, не EN duplicate на /ru/ | Read /ru/ body | |

---

## H. Trust, UX & Performance Signals (096–100)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 096 | 🟡 | ALL | **Favicon** и app icons присутствуют | `<link rel="icon">` | |
| 097 | 🟡 | ALL | **CTA** не spam (не >3 aggressive popups above fold) | Visual | |
| 098 | 🟡 | EX | **Exchange widget** загружается и показывает пару | Visual / functional | |
| 099 | 🟡 | ALL | **Core Web Vitals** LCP < 2.5s (field or lab, warn if worse) | PageSpeed / CrUX | |
| 100 | 🟡 | ALL | **Accessibility basics**: images с alt, контраст кнопок приемлемый | Lighthouse a11y | |

---

## Scoring (как считать итог)

```
Pass (✅)  = 1 балл
Warn (⚠️) = 0.5 балла
Fail (❌)  = 0 баллов
N/A (➖)   = исключить из знаменателя

Score = (sum points / applicable criteria) × 100
```

| Score | Grade | Действие |
|-------|-------|----------|
| 90–100 | A | Мониторинг, minor polish |
| 75–89 | B | План правок MEDIUM |
| 60–74 | C | Приоритет HIGH issues |
| < 60 | F | STOP — CRITICAL blockers |

**Любой 🔴 CRITICAL = Fail** независимо от % (страница не готова к индексации/ранжированию).

---

## Шаблон отчёта (копировать)

```markdown
# SEO Checklist Report — {pair} ({lang})
URL: 
Date: 
Auditor: 

| Block | Pass | Warn | Fail | N/A | Block % |
| A Technical | | | | | |
| B Meta | | | | | |
| C Content | | | | | |
| D LQA | | | | | |
| E Keywords | | | | | |
| F Schema | | | | | |
| G i18n | | | | | |
| H Trust | | | | | |
| **TOTAL** | | | | | **__%** |

CRITICAL fails: 
Top 3 fixes: 
```

---

## Связанные файлы

- Промпт для AI: `quickex-seo-audit.md`
- Макет exchange: `PAGE_LAYOUT_EXCHANGE.md`
- Паспорт: `QUICKEX_PROJECT_PASSPORT.md`
- Tier-1 пары: `PRIORITY_MUST_AUDIT.md`
