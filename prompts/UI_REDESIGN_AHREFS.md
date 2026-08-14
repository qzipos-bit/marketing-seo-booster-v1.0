# UI Redesign — Ahrefs-style (анализ + промпт)

> Референсы: Ahrefs Site Explorer (quickex.io), Keywords Explorer, Backlinks report.

---

## 1. Профессиональный разбор Ahrefs UI

### 1.1 Архитектура layout

| Зона | Назначение | Стиль |
|------|------------|-------|
| **Top bar (тёмный)** | Лого, глобальный поиск URL/keyword, API, аккаунт | `#1a1d21`, высота 48–52px |
| **Sub-header** | Breadcrumbs, заголовок отчёта, CTA (Update, Export, API) | белый, border-bottom 1px `#e5e7eb` |
| **Sidebar (светлый)** | Группы навигации с collapsible секциями | `#f9fafb`, ширина 220–260px |
| **Main canvas** | Карточки метрик + таблицы + графики | белый `#fff`, padding 24px |

### 1.2 Information hierarchy (как у про-сервисов)

1. **North Star metrics** — 3–4 крупные цифры вверху (DR, Organic traffic, Keywords).
2. **Trend sparkline** — мини-график рядом с метрикой (зелёный/красный delta).
3. **Фильтры** — горизонтальная панель над таблицей (All / Dofollow / DR / + Add filter).
4. **Data table** — плотная, много колонок, сортируемая, с badges (New, Lost, BEST LINK).
5. **Drill-down** — клик по строке → модалка с evidence (у нас уже есть в checklist).

### 1.3 Цветовая система

```
--ah-bg:        #f3f4f6
--ah-surface:   #ffffff
--ah-sidebar:   #f9fafb
--ah-topbar:    #1f2937
--ah-border:    #e5e7eb
--ah-text:      #111827
--ah-muted:     #6b7280
--ah-link:      #2563eb
--ah-positive:  #16a34a
--ah-negative:  #dc2626
--ah-warning:   #d97706
--ah-accent:    #f59e0b  /* Ahrefs orange для CTA */
```

### 1.4 Типографика

- **Font:** Inter / system-ui, 13–14px base для таблиц, 11px uppercase labels.
- **Metrics:** 28–32px bold для главных чисел.
- **Secondary:** 12px muted для подписей (First seen, Share %).

### 1.5 Паттерны выгрузок (что делают «ребята»)

| Инструмент | Форматы | Что выгружают |
|------------|---------|---------------|
| **Ahrefs** | CSV, API (JSON), Looker Studio | Текущий filtered view таблицы, не весь аккаунт |
| **Screaming Frog** | CSV, XLSX | Crawl export по выбранным колонкам |
| **Semrush** | PDF, CSV, XLSX | Position History, Backlinks |
| **GSC** | CSV, API | Queries, Pages, Coverage |
| **Claude SEO / drift** | JSON, SQLite | Snapshot diff для CI |

**Правило про:** export = **текущий фильтр + выбранные колонки + timestamp прогона**.

---

## 2. Маппинг на наш SEO Monitor

| Ahrefs модуль | Наш аналог | Метрики для export |
|---------------|------------|-------------------|
| Site Explorer Overview | Dashboard + Pro | score, grade, bot matrix, security |
| Keywords Explorer | Citation Radar + GEO | query, model, cites_domain, geo_score |
| Backlinks table | Checklist 145 | id, block, status, severity, evidence |
| Position History | Drift Guard | baseline vs current diff |
| Filters bar | Checklist chips | block, status filters → reflected in CSV |

---

## 3. Промпт для редизайна (для Figma / AI / разработчика)

```
Спроектируй SaaS SEO-дашборд «SEO Monitor» в стиле Ahrefs Site Explorer.

КОНТЕКСТ: инструмент для SEO-проаудита crypto-exchange (Quickex): чеклист 145 критериев,
AI citation radar, drift guard, bot reality test, Kie models health.

LAYOUT:
- Фиксированный тёмный topbar (#1f2937): лого, селектор сайта (quickex.io), поиск по критериям,
  кнопки [API] [Экспорт ▾] [Запустить аудит].
- Светлый sidebar с группами: Обзор | Чеклист | SEO Lab | Pro-аудит | Модели Kie.
- Main area: белые карточки с 1px border #e5e7eb, radius 8px, без тяжёлых теней.

TOP METRICS ROW (4 карточки):
- SEO Score % + grade badge (A–F)
- Pass / Warn / Fail counts с цветными delta
- AI Cite Rate % (из Citation Radar)
- Drift Critical count

FILTER BAR (над таблицей чеклиста):
- Chips: Все блоки | A–K | статусы
- Search input «canonical, H1…»
- Справа: [Колонки ▾] [Экспорт CSV] [Экспорт JSON]

DATA TABLE:
- Колонки: # | Блок | Критерий | Severity | Status | Evidence (truncate)
- Status badges: зелёный pass, жёлтый warn, красный fail
- Row hover #f9fafb, клик → slide-over panel с полным evidence

EXPORT UX:
- Dropdown «Экспорт»: CSV (текущий вид), JSON (raw), Markdown (отчёт), Полный snapshot
- Показывать timestamp и URL страницы в имени файла: quickex_checklist_2026-08-14.csv

ЦВЕТА: нейтральный light UI, синие ссылки, семантические green/red/orange для трендов.
НЕ использовать тёмную тему как основную — только topbar тёмный.

DENSITY: data-dense но читаемо, 13px в таблицах, ample whitespace между секциями.
```

---

## 4. Спецификация export API (реализовано)

| Endpoint | Формат | Данные |
|----------|--------|--------|
| `GET /api/export/checklist.csv` | CSV | Последний checklist run |
| `GET /api/export/checklist.json` | JSON | + summary, blocks |
| `GET /api/export/pro.json` | JSON | Pro report + roadmap |
| `GET /api/export/pro.csv` | CSV | Bot matrix + security flat |
| `GET /api/export/lab/{feature}.csv` | CSV | bot_reality, drift, citations, geo, render_gap |
| `GET /api/export/models.csv` | CSV | Model probe results |
| `GET /api/export/seo.csv` | CSV | SEO page scores |
| `GET /api/export/snapshot.json` | JSON | Все latest runs одним файлом |
| `GET /api/export/history` | JSON | Лог выгрузок (SQLite) |

Имена файлов: `{site}_{module}_{date}.{ext}`

---

## 5. Roadmap редизайна (фазы)

| Фаза | Что | Срок |
|------|-----|------|
| **1** | Export API + кнопки в UI | ✅ сейчас |
| **2** | Ahrefs light theme CSS | ✅ сейчас |
| **3** | Единый base layout + topbar | следующий спринт |
| **4** | Sparklines / history charts | нужен Chart.js |
| **5** | GSC/Ahrefs API import | опционально |
