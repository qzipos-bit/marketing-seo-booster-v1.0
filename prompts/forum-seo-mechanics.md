# SEO Forum & Community Mechanics (2025–2026)

Сводка практик из профессиональных чеклистов, r/TechSEO, WebmasterWorld и GEO-гайдов.

## 1. AI Crawler Readiness (новый must-have)

- ~40% сайтов **случайно блокируют** AI-ботов в robots.txt (Originality.ai).
- Разделять **search bots** (Googlebot) и **training/citation bots** (GPTBot, Google-Extended).
- Проверять: PerplexityBot, ClaudeBot, Anthropic-AI, ChatGPT-User, GPTBot, GoogleOther, Applebot-Extended.
- **llms.txt** — structured hint для LLM-crawler (аналог robots для AI).

## 2. Schema Drift

- JSON-LD должен совпадать с **видимым** контентом (H1, FAQ, Product name).
- Частая ошибка на Nuxt/SPA: schema генерируется на клиенте или из другого шаблона.

## 3. Redirect Chains & Loops

- Целевой максимум: **1 hop** (ideal), допустимо **2 hops**.
- Цепочки 3+ — типичная находка Screaming Frog / Sitebulb на форумах.
- Все permanent → **301**, не 302 для миграций.

## 4. Template-Level Duplicates

- Массовые дубли title/description на exchange/category URL — сигнал **thin template**.
- Диагностика: сравнение 5–20 URL одного типа, не одной страницы.

## 5. Security Headers (Trust + indirect SEO)

- HSTS, CSP, X-Frame-Options, X-Content-Type-Options — grade A на securityheaders.com.
- YMYL (crypto exchange) — privacy + contact обязательны.

## 6. Core Web Vitals — INP

- INP заменил FID; форумы рекомендуют INP < 200ms для интерактивных SPA.
- Уже частично покрыто блоками A/N; INP требует CrUX / Lighthouse (manual).

## 7. Priority Roadmap (pro workflow)

Каждая находка классифицируется:

| Priority | Критерий |
|----------|----------|
| P0 Urgent | 🔴 fail + блокирует index/AI crawl |
| P1 High | 🟠 fail или 🔴 warn |
| P2 Medium | 🟡 fail |
| P3 Low | manual / polish |

## 8. Quarterly Audit Rhythm

- После миграции CMS, redesign, смены хостинга — полный прогон.
- Сравнение delta между прогонами (score, новые fail).

## Реализация в kie-seo-monitor

| Механика | Модуль | UI |
|----------|--------|-----|
| AI bot matrix | `pro_seo_auditor.py` | `/pro` |
| Security headers | `pro_seo_auditor.py` | `/pro` |
| Redirect trace | `pro_seo_auditor.py` | `/pro` |
| Duplicate titles/desc | `pro_seo_auditor.py` | `/pro` |
| Schema drift | checklist 141 + pro report | checklist + `/pro` |
| Priority roadmap | `build_priority_roadmap()` | `/pro` export |
| Checklist 121–145 | `pro-forum-checklist-extra.md` | `/checklist` (145) |
