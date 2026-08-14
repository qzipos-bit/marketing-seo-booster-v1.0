# Библиотека источников — аудит крипто-проектов (EEAT / YMYL)

> Сформировано для Marketing SEO Booster. Приоритет: **официальные документы Google и регуляторов**, затем отраслевые разборы QRG.  
> **AI-промпт для сбора документов и глубокого E-E-A-T анализа:** `prompts/eeat-research-prompt.md`  
> **AI-промпт для YMYL harm prevention аудита:** `prompts/ymyl-research-prompt.md`

## Официальные документы Google

| ID | Документ | URL | Что проверяем |
|----|----------|-----|---------------|
| G-QRG | Search Quality Rater Guidelines (Sep 2025) | https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf | YMYL §2.3, E-E-A-T §3.4, PQ §3–8 |
| G-HC | Creating helpful, reliable, people-first content | https://developers.google.com/search/docs/fundamentals/creating-helpful-content | E-E-A-T, YMYL bar |
| G-SPAM | Spam policies for Google web search | https://developers.google.com/search/docs/essentials/spam-policies | Scaled content, misleading claims |
| G-RAT | Review snippet / structured data | https://developers.google.com/search/docs/appearance/structured-data/review-snippet | Review schema abuse |
| G-ORG | Organization structured data | https://developers.google.com/search/docs/appearance/structured-data/organization | Entity, sameAs, logo |
| G-AI | Google Search Central AI content guidance | https://developers.google.com/search/docs/fundamentals/creating-helpful-content | AI-generated YMYL risk |
| G-SG | Structured data general guidelines | https://developers.google.com/search/docs/appearance/structured-data/sd-policies | Schema abuse, required fields |

## Регуляторика и compliance (крипто / финансы)

| ID | Источник | URL | Применение |
|----|----------|-----|------------|
| R-SEC | SEC — Investor alerts (crypto) | https://www.sec.gov/newsroom/press-releases | Investment claims, securities risk |
| R-SEC-CRYPTO | SEC Crypto Assets hub | https://www.sec.gov/crypto | Securities vs commodity framing |
| R-FINCEN | FinCEN MSB registration | https://www.fincen.gov/msb-registrant-search | US MSB disclosure |
| R-FATF | FATF Virtual Assets guidance | https://www.fatf-gafi.org/en/topics/virtual-assets.html | AML/KYC expectations |
| R-MICA | EU MiCA regulation overview | https://finance.ec.europa.eu/regulation-and-supervision/fintech/crypto-assets_en | EU licensing narrative |
| R-FCA | FCA cryptoasset register (UK) | https://register.fca.org.uk/s/search | UK authorization claims |
| R-ESMA | ESMA crypto warnings | https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/crypto-assets | EU investor warnings |
| R-CFTC | CFTC virtual currency resources | https://www.cftc.gov/digitalassets/index.htm | Commodity derivatives, fraud alerts |
| R-FTC | FTC consumer crypto guidance | https://consumer.ftc.gov/articles/what-know-about-cryptocurrency-and-scams | Scam patterns, consumer harm |

## Schema.org и entity SEO

| ID | Документ | URL |
|----|----------|-----|
| S-ORG | Organization | https://schema.org/Organization |
| S-FS | FinancialService | https://schema.org/FinancialService |
| S-FAQ | FAQPage | https://schema.org/FAQPage |
| S-PERSON | Person (author) | https://schema.org/Person |
| S-WP | AboutPage | https://schema.org/AboutPage |
| S-REVIEW | Review / AggregateRating | https://schema.org/Review |

## Entity, reputation и верификация (веб)

| ID | Источник | URL | Применение |
|----|----------|-----|------------|
| W-LINKEDIN | LinkedIn Company | https://www.linkedin.com/company/ | Entity, team, NAP |
| W-CRUNCH | Crunchbase | https://www.crunchbase.com/ | Funding, founding date |
| W-WIKI | Wikidata | https://www.wikidata.org/ | Knowledge Graph signals |
| W-TRUSTPILOT | Trustpilot | https://www.trustpilot.com/ | UGC reviews (triangulate) |
| W-WAYBACK | Internet Archive | https://web.archive.org/ | Historical claims |
| W-COINGECKO | CoinGecko exchanges | https://www.coingecko.com/en/exchanges | Listing / trust score |

## Отраслевые разборы QRG (не официальные, для операционной проверки)

| ID | Источник | URL | Примечание |
|----|----------|-----|------------|
| I-CRAWLUX | Crypto E-E-A-T & YMYL 2026 | https://www.crawlux.com/guides/eeat-ymyl-crypto/ | Trust signals checklist |
| I-ANYLEARN | E-E-A-T for crypto content | https://anylearn.cc/lessons/eeat-and-entity-seo-for-crypto | Entity + YMYL bucket |
| I-GUIDEX | QRG explained 2026 | https://theguidex.com/insights/google-quality-rater-guidelines | Sep 2025 updates |
| I-MOZ-EEAT | Moz E-E-A-T guide | https://moz.com/learn/seo/google-eat | General framework |

## «Сливы» и внутренние паттерны (публичные обсуждения)

| ID | Тема | Где искать | Сигнал |
|----|------|------------|--------|
| L-API-2024 | Content Warehouse API leak (14k attributes) | [/leaks](/leaks) · SparkToro · iPullRank | NavBoost, siteAuthority, Chrome data |
| L-HCU | Helpful Content / YMYL demotion | SEO форумы, Google Search Central blog | Thin affiliate, no author |
| L-REVIEWS | Review update impact | https://developers.google.com/search/blog | Fake reviews, self-serving |
| L-SGE | AI Overviews citation bias | Industry studies 2024–2026 | Entity strength, citations |
| L-CRYPTO-SPAM | March 2024 spam updates | Search Engine Journal, Moz | Crypto sites −30–60% без E-E-A-T |
| L-CHROME | Chrome engagement signals | Leak docs siteAuthority | Trust proxy from UX |

## Минимальный набор страниц для аудита крипто-exchange

1. Homepage  
2. About / Company  
3. Privacy Policy  
4. Terms of Service  
5. AML / KYC policy (если есть)  
6. Fees / How it works  
7. Security / Trust page  
8. Contact / Support  
9. Blog author pages (если есть контент)  
10. Exchange pair landing (YMYL money page)

## Как использовать в MSB

- **EEAT** (`/eeat`) — Experience, Expertise, Authoritativeness, Trust  
- **YMYL** (`/ymyl`) — Your Money or Your Life, финансовый harm-bar  
- **AI Research** — `prompts/eeat-research-prompt.md` + кнопка «AI E-E-A-T Research» на `/eeat`  
- Каждый критерий ссылается на `source_id` из таблиц выше
