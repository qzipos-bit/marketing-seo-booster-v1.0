# Crypto Exchange — E-E-A-T Checklist

Критерии для non-custodial / instant swap exchanges. Источники: Google QRG §3.4, Search Central, schema.org.

## E. Experience (первый опыт)

| # | Sev | Scope | Критерий | Как проверять | Источник |
| EE01 | 🟠 | EX | How-it-works с пошаговым процессом swap | 4+ шага: выбор пары → адрес → подтверждение → получение | G-QRG §3.4 Experience |
| EE02 | 🟡 | EX | Реальные детали UX (время, лимиты, сети) | Упоминание network fee, min/max amount, ETA | G-HC |
| EE03 | 🟡 | EX | FAQ отвечает на практические вопросы пользователя | ≥5 FAQ с конкретикой (не generic) | G-QRG §3.4.1 |
| EE04 | 🟡 | BLOG | Контент с first-hand опытом (обзоры, гайды) | Author + дата + «мы протестировали» / скриншоты | G-QRG §3.4.1 |
| EE05 | 🟢 | ALL | Отзывы пользователей с контекстом | Testimonials с деталями, не только звёзды | G-RAT |

## X. Expertise (экспертиза)

| # | Sev | Scope | Критерий | Как проверять | Источник |
| EE06 | 🔴 | SITE | Author/Editorial policy | Страница About editorial или author bios на блоге | G-QRG §3.4 Expertise |
| EE07 | 🟠 | BLOG | Именованные авторы с credentials | Person schema или bio: роль, опыт в crypto/fintech | S-PERSON |
| EE08 | 🟠 | EX | Точная терминология (custodial, on-chain, slippage) | Нет грубых ошибок в финансовых терминах | G-QRG §3.2 MC accuracy |
| EE09 | 🟡 | EX | Сравнения с конкурентами — фактологичны | Таблица fees/features без необоснованных claim | G-SPAM |
| EE10 | 🟡 | SITE | Дата обновления контента | dateModified / «Last updated» на money pages | I-CRAWLUX |

## A. Authoritativeness (авторитет)

| # | Sev | Scope | Критерий | Как проверять | Источник |
| EE11 | 🔴 | SITE | Organization schema с name + url + logo | JSON-LD Organization на homepage/about | S-ORG, G-ORG |
| EE12 | 🟠 | SITE | sameAs: соцсети / LinkedIn / Crunchbase | sameAs массив в Organization schema | G-ORG |
| EE13 | 🟠 | SITE | About: юрлицо, год основания, юрисдикция | Legal entity name, registration country | I-ANYLEARN |
| EE14 | 🟡 | SITE | Press / Media / Partners страница | Упоминания в СМИ или партнёры с верификацией | G-QRG §3.3 reputation |
| EE15 | 🟡 | SITE | Консистентный NAP (name, address, contact) | Одинаковые контакты в footer, contact, about | I-ANYLEARN |
| EE16 | 🟢 | SITE | Wikidata / Knowledge Panel сигналы | Поиск бренда в KG (ручная) | I-ANYLEARN |

## T. Trustworthiness (доверие — центр E-E-A-T)

| # | Sev | Scope | Критерий | Как проверять | Источник |
| EE17 | 🔴 | SITE | HTTPS на всех money pages | Все URL https://, нет mixed content | G-QRG Trust |
| EE18 | 🔴 | SITE | Privacy Policy доступна и линкуется | /privacy или аналог в footer | G-QRG §3.4 Trust |
| EE19 | 🔴 | SITE | Terms of Service доступны | /terms, /tos в footer | G-QRG Trust |
| EE20 | 🔴 | SITE | Financial / risk disclaimer | «Not financial advice», risk of loss | R-SEC, G-QRG YMYL |
| EE21 | 🟠 | SITE | Контакт: email или форма + response SLA | support@, live chat, ticket system | G-QRG Trust |
| EE22 | 🟠 | SITE | Security page: 2FA, non-custodial, encryption | /security или блок Trust | I-CRAWLUX |
| EE23 | 🟠 | ALL | Нет overclaim: 100% anonymous, guaranteed profit | Regex: untraceable, guaranteed returns | G-SPAM, R-SEC |
| EE24 | 🟠 | SITE | Cookie / GDPR consent где нужно | Cookie banner для EU traffic | R-MICA |
| EE25 | 🟡 | SITE | Review schema только при реальных отзывах | AggregateRating без fake reviews | G-RAT |
| EE26 | 🟡 | EX | Прозрачные fees (не скрыты до checkout) | Fees на странице или /fees | G-QRG Trust |
| EE27 | 🟡 | SITE | llms.txt / robots для AI crawlers | llms.txt exists, AI bots policy | G-AI |
| EE28 | 🟢 | SITE | Status page / uptime transparency | status.domain.com или аналог | I-CRAWLUX |
