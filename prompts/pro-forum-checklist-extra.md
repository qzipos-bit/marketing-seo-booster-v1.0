# Pro SEO — форумы & комьюнити 2025–2026 (121–145)

> Источники: Rankeo 45-point audit, Search Engine Journal, Originality.ai (AI crawlers),
> r/TechSEO / WebmasterWorld (redirect chains, schema drift), Semrush community (duplicate templates).

**Scope:** `SITE` — site-wide · `ALL` — каждая проверяемая страница

---

## I. AI Readiness & GEO (121–128)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 121 | 🔴 | SITE | **llms.txt** на корне (`/llms.txt` → 200, не пустой) | GET /llms.txt | |
| 122 | 🔴 | SITE | **PerplexityBot** не заблокирован в robots.txt | robots UA matrix | |
| 123 | 🔴 | SITE | **ClaudeBot / Anthropic-AI** — осознанная политика доступа | robots UA matrix | |
| 124 | 🟠 | SITE | **GPTBot / ChatGPT-User** — явная политика (не accidental block) | robots UA matrix | |
| 125 | 🟠 | SITE | **Google-Extended / GoogleOther** — training vs search разделены | robots UA matrix | |
| 126 | 🟡 | SITE | **Applebot-Extended** доступен (Apple Intelligence citations) | robots UA matrix | |
| 127 | 🟠 | ALL | **FAQPage** schema на money/pillar страницах | JSON-LD type | |
| 128 | 🟡 | ALL | **Data tables** — HTML `<table>` для AI citability | count table | |

## J. Security & Trust (129–135)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 129 | 🔴 | SITE | **Strict-Transport-Security** (HSTS) в ответе сервера | response headers | |
| 130 | 🟠 | SITE | **X-Content-Type-Options: nosniff** | response headers | |
| 131 | 🟠 | SITE | **X-Frame-Options** или CSP `frame-ancestors` | response headers | |
| 132 | 🟡 | SITE | **Content-Security-Policy** задан (не пустой) | response headers | |
| 133 | 🟠 | ALL | **Mixed content** — нет `http://` ресурсов на HTTPS странице | grep src/href | |
| 134 | 🟡 | SITE | **Privacy policy** — ссылка в footer / навигации | crawl homepage | |
| 135 | 🟡 | SITE | **Контакты** — email или телефон на сайте | visible text | |

## K. Pro Architecture (136–145)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 136 | 🔴 | ALL | **Redirect chain ≤2 hops** до финального URL | trace 3xx | |
| 137 | 🟠 | ALL | **Нет redirect loop** | trace 3xx | |
| 138 | 🟠 | ALL | Канонический редирект **301** (не 302) где применимо | HEAD chain | |
| 139 | 🔴 | SITE | **Уникальные title** — нет дублей между страницами шаблона | cross-page scan | |
| 140 | 🟠 | SITE | **Уникальные meta description** — нет массовых дублей | cross-page scan | |
| 141 | 🟠 | ALL | **Schema drift** — JSON-LD name/title ≈ visible H1 (±40%) | compare ld+json | |
| 142 | 🟡 | ALL | **Internal links ≥3** на странице (same-domain) | count a[href] | |
| 143 | 🟡 | SITE | **Sitemap** в robots.txt и sitemap.xml → 200 | robots + GET | |
| 144 | 🟠 | ALL | **Self-referencing canonical** (не chain на другой URL) | link rel=canonical | |
| 145 | 🟡 | SITE | **Googlebot** не заблокирован (search ≠ training) | robots UA matrix | |
