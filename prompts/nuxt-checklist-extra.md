# Nuxt / SPA — дополнительные критерии (101–120)

> Типичные ошибки самописных сайтов на **Nuxt 2/3**, SSR/SSG и client-only SPA.  
> Блок **N** добавляется к основному чеклисту (120 критериев total).

**Scope:** `NUXT` — проверяется если в HTML есть признаки Nuxt или в config `stack: nuxt`

---

## N. Nuxt / SPA & самописные фронты (101–120)

| # | Sev | Scope | Критерий | Как проверить | ✅/⚠️/❌ |
|---|-----|-------|----------|---------------|---------|
| 101 | 🔴 | NUXT | **SSR/SSG:** в view-source есть осмысленный текст (>150 символов), не пустой shell | curl + View Source | |
| 102 | 🔴 | NUXT | Payload **__NUXT__** / **__NUXT_DATA__** / `window.__NUXT__` в HTML (Nuxt 3) | grep HTML | |
| 103 | 🔴 | NUXT | **H1 в исходном HTML** — не только после гидрации JS | view-source | |
| 104 | 🔴 | NUXT | **`<title>` в исходном HTML** — useHead/useSeoMeta отработал на сервере | view-source | |
| 105 | 🟠 | NUXT | **meta description** в исходном HTML (не client-only) | view-source | |
| 106 | 🟠 | NUXT | **canonical** в исходном HTML | view-source | |
| 107 | 🟠 | NUXT | **`/_nuxt/` assets** — главный JS-бандл отдаёт 200 (не 404) | HEAD первого `/_nuxt/*.js` | |
| 108 | 🟡 | NUXT | **`html lang="..."`** задан и соответствует локали URL | `<html lang>` | |
| 109 | 🔴 | NUXT | Нет паттерна **пустого `#__nuxt`/`#app`** (<200 символов видимого текста) | parse body text | |
| 110 | 🟠 | NUXT | **OG-теги** в исходном HTML (не только после Vue mount) | view-source head | |
| 111 | 🟡 | NUXT | **JSON-LD** в исходном HTML для SEO-страниц | script ld+json | |
| 112 | 🟠 | NUXT | **CLS:** ≥50% `<img>` без width/height (типично для самописных Nuxt) | parse img attrs | |
| 113 | 🟡 | NUXT | Не более **10 blocking scripts** в `<head>` | count script no defer/async | |
| 114 | 🟡 | NUXT | Нет **`<meta http-equiv="refresh">`** редиректа (soft SEO trap) | grep refresh | |
| 115 | 🟠 | NUXT | **Один `<title>`** — layout + page не дублируют | count title tags | |
| 116 | 🟠 | NUXT | **i18n prefix:** `/ru/` → lang=ru или hreflang ru | lang vs URL | |
| 117 | 🟠 | NUXT | **preload** критичных шрифтов или CSS (не всё через JS) | link rel=preload | |
| 118 | 🟡 | NUXT | **`modulepreload` / prefetch** для route chunks — признак нормального Nuxt build | link rel | |
| 119 | 🔴 | NUXT | Нет **`data-server-rendered="true"`** missing + empty body (CSR-only mode) | Nuxt 2 SSR marker / text | |
| 120 | 🟡 | NUXT | **robots/noindex** не задан ошибочно в nuxt.config через meta на prod | meta robots | |
