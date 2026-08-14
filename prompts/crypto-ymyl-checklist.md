# Crypto Exchange — YMYL Checklist

Your Money or Your Life — финансовая безопасность пользователя. Источники: Google QRG §2.3, §3.4.1, SEC, FATF.

## Y1. Классификация YMYL

| # | Sev | Scope | Критерий | Как проверять | Источник |
| YY01 | 🔴 | ALL | Страница относится к YMYL Financial Security | Crypto swap/exchange = clear YMYL | G-QRG §2.3 |
| YY02 | 🔴 | EX | Money page: влияет на финансовое решение пользователя | Exchange pair, buy/sell, fees — high scrutiny | G-QRG §2.3 |
| YY03 | 🟠 | BLOG | Investment advice контент помечен как YMYL | Статьи про «лучшие монеты» = YMYL bar | G-QRG §2.3 |
| YY04 | 🟡 | ALL | Harm potential оценён: неточность = финансовый ущерб | Factual claims на money pages проверены | G-QRG §2.3 |

## Y2. Предотвращение вреда (harm prevention)

| # | Sev | Scope | Критерий | Как проверять | Источник |
| YY05 | 🔴 | ALL | Disclaimer: не финансовый совет | «Informational purposes only», not investment advice | R-SEC |
| YY06 | 🔴 | EX | Риск потери капитала явно указан | Volatility, total loss possible | R-SEC, R-ESMA |
| YY07 | 🔴 | EX | Non-custodial vs custodial — ясно объяснено | Пользователь понимает кто держит ключи | R-FATF |
| YY08 | 🟠 | EX | Нет гарантий доходности / APY без рисков | No «guaranteed», «risk-free profit» | G-SPAM |
| YY09 | 🟠 | EX | Предупреждение о scam / phishing | Блок «verify URL», official domain | I-CRAWLUX |
| YY10 | 🟠 | SITE | KYC/AML политика доступна | /aml, /kyc или раздел compliance | R-FATF |
| YY11 | 🟡 | EX | Geo-restrictions / санкции disclosed | Restricted countries list | R-FATF, R-MICA |

## Y3. Точность и expert consensus

| # | Sev | Scope | Критерий | Как проверять | Источник |
| YY12 | 🔴 | EX | Курсы/fees не вводят в заблуждение | Realistic fee display, no hidden spread claims | G-QRG §3.2 |
| YY13 | 🟠 | BLOG | Факты с источниками (on-chain data, regulators) | Citations, links to primary sources | G-QRG YMYL accuracy |
| YY14 | 🟠 | EX | Нет outdated financial promises | Контент обновлён <12 мес на money pages | I-CRAWLUX |
| YY15 | 🟡 | EX | Сравнение с конкурентами — честное | Нет ложных «#1» без доказательств | G-SPAM |
| YY16 | 🟡 | BLOG | Medical/health claims отсутствуют на crypto pages | N/A cross-topic contamination | G-QRG |

## Y4. Репутация и регуляторные заявления

| # | Sev | Scope | Критерий | Как проверять | Источник |
| YY17 | 🔴 | SITE | Лицензии/регистрации — только верифицируемые | MSB FinCEN, FCA register — с номером | R-FINCEN, R-FCA |
| YY18 | 🟠 | SITE | Нет ложных «regulated by» без proof | License number + link to regulator | G-QRG §3.3 reputation |
| YY19 | 🟠 | SITE | Отрицательная репутация проверена | Поиск scam reports, trustpilot patterns | G-QRG §3.3 |
| YY20 | 🟡 | SITE | Прозрачность ownership (кто владеет сервисом) | Company name, directors, jurisdiction | I-ANYLEARN |
| YY21 | 🟡 | SITE | Incident history / hacks disclosed honestly | Post-mortem если был инцидент | G-QRG Trust |

## Y5. Transactional trust (финансовые страницы)

| # | Sev | Scope | Критерий | Как проверять | Источник |
| YY22 | 🔴 | EX | HTTPS + secure checkout flow | TLS, no payment data on HTTP | G-QRG Trust |
| YY23 | 🟠 | EX | Refund / stuck transaction policy | Support path для failed swaps | I-CRAWLUX |
| YY24 | 🟠 | EX | Min/max limits видны до транзакции | Лимиты на странице обмена | G-QRG Trust |
| YY25 | 🟠 | SITE | Support response channel 24/7 claim — реален | Live chat / ticket, не fake widget | G-QRG |
| YY26 | 🟡 | EX | FinancialService schema если применимо | schema.org/FinancialService | S-FS |
| YY27 | 🟡 | SITE | PCI / payment partners disclosed если card on-ramp | Payment provider logos verifiable | G-QRG |
| YY28 | 🟢 | SITE | Bug bounty / security contact | security@ email или HackerOne | I-CRAWLUX |
