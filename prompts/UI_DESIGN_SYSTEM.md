# Marketing SEO Booster — UI Design System v2

> Единый промпт для всех страниц. Референс: Ahrefs, Linear, Vercel Dashboard.

## Принципы

1. **Один светлый canvas** — тёмная только шапка (52px). Никаких тёмных sidebar/hero на страницах.
2. **Одна навигация** — глобальный topbar. Без дублирующих боковых меню на каждой странице.
3. **Одинаковая иерархия** на каждой странице:
   - Page header (breadcrumb + H1 + subtitle + actions)
   - KPI row (3–6 метрик в карточках)
   - Toolbar (фильтры, поиск, CTA)
   - Content (таблица / карточки / панели)
4. **Data-dense, не decorative** — 13–14px base, uppercase labels 11px, метрики 24–28px bold.
5. **Семантические цвета** — green pass, amber warn, red fail, blue info. CTA orange `#f59e0b`.

## Layout

```
┌─ TOPBAR (dark #111827, 52px) ─────────────────────────────────┐
│ Logo │ Nav + Dropdowns │                    [Скан] [Экспорт] │
├────────────────────────────────────────────────────────────────┤
│ PAGE HEADER (white, border-bottom)                             │
│ breadcrumb · muted                                             │
│ H1 title                              [page actions]           │
│ subtitle                                                       │
├────────────────────────────────────────────────────────────────┤
│ KPI ROW — grid 4–6 cards                                       │
├────────────────────────────────────────────────────────────────┤
│ TOOLBAR — chips, search, select                                │
├────────────────────────────────────────────────────────────────┤
│ MAIN CONTENT — tables / card grid / panels                     │
└────────────────────────────────────────────────────────────────┘
Max width: 1440px, padding: 24px 28px
```

## Tokens

```css
--msb-bg: #f4f5f7;
--msb-surface: #ffffff;
--msb-border: #e5e7eb;
--msb-text: #111827;
--msb-muted: #6b7280;
--msb-accent: #2563eb;
--msb-cta: #f59e0b;
--msb-pass: #16a34a;
--msb-warn: #d97706;
--msb-fail: #dc2626;
--msb-radius: 8px;
--msb-radius-lg: 12px;
--msb-shadow: 0 1px 2px rgba(0,0,0,.04);
--msb-shadow-md: 0 4px 12px rgba(0,0,0,.08);
```

## Components

| Класс | Назначение |
|-------|------------|
| `.msb-page` | Обёртка страницы, max-width 1440px |
| `.msb-page-header` | Breadcrumb + title + actions |
| `.msb-kpi-row` | Сетка метрик |
| `.msb-kpi` | Одна метрика |
| `.msb-toolbar` | Панель фильтров |
| `.msb-chip` | Фильтр-chip |
| `.msb-btn` / `.msb-btn--primary` | Кнопки |
| `.msb-card` | Карточка контента |
| `.msb-card-grid` | Сетка checklist-карточек |
| `.msb-table-wrap` | Scrollable table |
| `.msb-table` | Data table |
| `.msb-badge` | Status badge |
| `.msb-panel` | Белая панель с заголовком |
| `.msb-tabs` | Sub-tabs (EEAT/YMYL) |
| `.msb-empty` | Empty state |
| `.msb-alert` | Warning banner |

## Typography

- Font: `Inter, system-ui, sans-serif`
- H1 page: 1.35rem / 600
- Breadcrumb: 0.78rem / muted
- Subtitle: 0.88rem / muted
- Table header: 0.72rem uppercase letter-spacing .04em

## Запрещено

- Inline `<style>` блоки в шаблонах (только msb.css)
- Дублирующие sidebar с навигацией
- Тёмные hero-gradient на светлых страницах
- Эмодзи в кнопках topbar
- Разные CSS-файлы на разных страницах (только msb.css)

## Шаблон страницы

```jinja
{% extends "base.html" %}
{% set active = 'checklist' %}
{% block title %}Чеклист — {{ product_full }}{% endblock %}

{% block page_header %}
{% set breadcrumb = 'Аудит / Чеклист' %}
{% set page_title = 'SEO Чеклист 145' %}
{% set page_subtitle = '...' %}
{% include 'partials/page_header.html' %}
{% endblock %}

{% block content %}
  ...
{% endblock %}

{% block scripts %}
<script>...</script>
{% endblock %}
```
