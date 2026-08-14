# Marketing SEO Booster v1.0

Инструмент **Marketing SEO Booster** — постоянный SEO-скрининг, аудит 145 критериев, AI-аналитика и история данных.

1. **Проверки нейросетей** через [Kie API](https://kie.ai/) — latency, статус, preview ответа, история прогонов.
2. **SEO-аудит** страниц — title, description, H1, canonical, OG, JSON-LD, sitemap, robots.txt.
3. **Постоянный скрининг** — полный скан каждые N минут с хранением истории в SQLite.

## Быстрый старт

```bash
cd kie-seo-monitor
cp .env.example .env
# добавь KIE_API_KEY в .env
chmod +x run.sh
./run.sh
```

Открой: **http://127.0.0.1:8787**

**История сканов:** http://127.0.0.1:8787/history

## CLI (без дашборда)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python run_check.py models   # только Kie
python run_check.py seo      # только SEO
python run_check.py all      # всё
```

## Настройка

| Файл | Что менять |
|------|------------|
| `.env` | `KIE_API_KEY`, порт, интервал auto-check |
| `config.yaml` | список моделей Kie и URL для SEO |

### SEO

По умолчанию проверяется **localhost:3000** (Altcoinlog dev). Перед SEO-check подними сайт:

```bash
cd ../Altcoinlog && npm run dev
```

Добавь прод-URL в `config.yaml` → `seo.pages`.

### Auto-check

`AUTO_CHECK_INTERVAL_MIN=30` — каждые 30 минут модели + SEO.  
`0` — только ручной запуск с дашборда.

### Постоянный скрининг (история аудита)

`SCAN_INTERVAL_MIN=60` — полный аудит-цикл каждые 60 минут (SEO + чеклист + GEO + модели + pro).  
Результаты сохраняются в SQLite (`scan_runs`, `scan_page_snapshots`).

| URL | Описание |
|-----|----------|
| `/history` | Дашборд истории сканов и тренды |
| `GET /health` | Healthcheck (DB + scheduler) |
| `GET /ready` | Readiness (свежесть последнего скана) |
| `POST /api/scan/run` | Запуск скана вручную |
| `GET /api/scan/history` | JSON история |
| `GET /api/export/scan-history.csv` | Экспорт в CSV |

Кнопка **▶ Скан** в верхней панели — тот же полный прогон.

### Production (Docker)

```bash
cp .env.example .env
# задай KIE_API_KEY, MONITOR_API_TOKEN (обязательно в prod)

docker compose up -d --build
# http://127.0.0.1:8787/health
```

Бэкап БД каждые 6 часов:

```bash
docker compose --profile backup up -d backup
# или локально: make backup
```

Локальный prod без Docker:

```bash
ENV=production MONITOR_API_TOKEN=your-secret ./run-prod.sh
```

### Переменные окружения

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `ENV` | development | `production` — без /docs, без --reload |
| `MONITOR_API_TOKEN` | (пусто) | Bearer для POST `/api/*` |
| `SCAN_SKIP_AI_REVIEW` | true | Не вызывать Kie AI review в full scan |
| `LOG_LEVEL` | INFO | Уровень логов |
| `LOG_FORMAT` | text | `json` для production |

## Структура

```
kie-seo-monitor/
  app/
    main.py           # FastAPI + дашборд
    model_checker.py  # Kie probe
    seo_checker.py    # SEO audit
    storage.py        # SQLite history
  templates/          # HTML dashboard
  static/             # CSS
  data/monitor.db     # история (создаётся автоматически)
  config.yaml
  run.sh
  run-prod.sh
  run_check.py
  Dockerfile
  docker-compose.yml
  Makefile
  scripts/backup_db.sh
  tests/
```

## Quickex SEO (профиль)

Профессиональный SEO-промпт: **`prompts/quickex-seo-audit.md`**  
Копия в TMS-проекте: `SEO_spider_mcp_server_Cursor/tms_audit/prompts/QUICKEX_SEO_AUDIT.md`

```bash
./run-quickex.sh
# или
CONFIG_PROFILE=quickex ./run.sh
```

**Checklist dashboard:** http://127.0.0.1:8787/checklist — **145 критериев** (100 SEO + 20 Nuxt + 25 Pro), фильтры, score, grade.

**Pro SEO dashboard:** http://127.0.0.1:8787/pro — AI crawler matrix, security headers, redirect chains, duplicate templates, priority roadmap (P0–P3).

**SEO Lab (5 features):** http://127.0.0.1:8787/lab

**Выгрузки (Ahrefs-style):** http://127.0.0.1:8787/exports

Промпт редизайна: `prompts/UI_REDESIGN_AHREFS.md`

| Endpoint | Формат |
|----------|--------|
| `/api/export/checklist.csv` | Чеклист 145 |
| `/api/export/scan-history.csv` | История полных сканов |
| `/api/export/snapshot.json` | Все latest runs |
| `/api/export/lab/{feature}.csv` | bot_reality, drift, citations, geo, render_gap |
| `/api/export/history` | Лог выгрузок (SQLite) |

| # | Feature | API |
|---|---------|-----|
| 3 | Bot Reality Test | `POST /api/lab/bot-reality` |
| 2 | SEO Drift Guard | `POST /api/lab/drift/baseline`, `/compare` |
| 1 | AI Citation Radar | `POST /api/lab/citations` |
| 4 | GEO / Citability Score | `POST /api/lab/geo` |
| 5 | Render Gap Lab | `POST /api/lab/render-gap` |
| all | Run all | `POST /api/lab/run-all` |

Render Gap: `pip install playwright && playwright install chromium` (optional).

Проверяет live quickex.io: Tier-1 пары, homepage, premium, sitemap, robots.  
При `seo.ai_review.enabled: true` — до 3 страниц отправляются в **GPT 5.6 Terra** с полным SEO-промптом (Executive Summary + JSON).

Промпт покрывает 7 слоёв: Technical, Meta, Content, LQA, Keywords, Schema, Trust — с severity CRITICAL→LOW и правилами Quickex (H1 vs meta title, Bitcoin (BTC), RU «обмен»).

**Чеклисты:**
- `prompts/quickex-seo-checklist-100.md` — базовые 100
- `prompts/nuxt-checklist-extra.md` — Nuxt/SPA 101–120
- `prompts/pro-forum-checklist-extra.md` — Pro 121–145 (AI readiness, security, architecture)
- `prompts/forum-seo-mechanics.md` — сводка практик из форумов/GEO 2026

**Pro-механики** (`app/pro_seo_auditor.py`):
- AI bots matrix: PerplexityBot, ClaudeBot, GPTBot, Google-Extended, Applebot-Extended…
- `/llms.txt` check
- Security headers (HSTS, CSP, X-Frame-Options)
- Redirect chain tracer (≤2 hops rule)
- Cross-page duplicate title/description
- Schema drift (JSON-LD vs H1)
- Priority roadmap export: `GET /api/pro/export.md`

- `GET /api/status` — последние результаты JSON
- `POST /api/check/models` — прогон моделей
- `POST /api/check/seo` — SEO аудит
- `POST /api/check/all` — оба прогона
- `POST /api/check/checklist` — аудит 145 критериев
- `POST /api/check/pro` — checklist + pro report
