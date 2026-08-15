# Google Content Warehouse API Leak (March–May 2024)

> **Status:** Google confirmed authenticity (May 29, 2024).  
> **Source:** Internal Content Warehouse / Content API protobuf documentation accidentally published to a public GitHub repository (Mar 27 – May 7, 2024), indexed by HexDocs.  
> **Scale:** 2,596 modules · 14,014 API attributes · 2,500+ pages of documentation.

## What was leaked

The leak is **not source code**. It is **field-level API documentation** describing data structures Google stores about web documents, sites, links, clicks, quality signals, and ranking-related metadata. Analysts mapped attributes to ranking systems; Google warned the docs are out of context and may include deprecated or training-only fields.

## Primary English-language analysis (read these first)

| Analyst | URL | Focus |
|---------|-----|--------|
| Rand Fishkin (SparkToro) | https://sparktoro.com/blog/an-anonymous-source-shared-thousands-of-leaked-google-search-api-documents-with-me-everyone-in-seo-should-see-them/ | Original disclosure, NavBoost, site authority |
| Michael King (iPullRank) | https://ipullrank.com/google-algo-leak | Attribute mapping, actionable SEO |
| Mike King deck / repo | https://github.com/iPullRank/google-algo-leak | Searchable attribute index |
| Wikipedia synthesis | https://en.wikipedia.org/wiki/2024_Google_Search_documentation_leak | Timeline, confirmed facts |
| The Verge | https://www.theverge.com/2024/5/29/24167407/google-search-algorithm-documents-leak-confirmation | Google confirmation quote |
| Search Engine Land | https://searchengineland.com/google-search-documentation-leak-442617 | Industry summary |
| Growfusely | https://growfusely.com/blog/google-api-leak/ | Ranking factor checklist |
| Optimal Digital | https://www.winwithoptimal.com/insights/google-api-leak/ | NavBoost, demotions |

## Confirmed themes (cross-validated by multiple analysts)

### 1. User interaction / clickstream (NavBoost family)

Attributes referenced in leak and antitrust trial testimony:

- `goodClicks`, `badClicks`, `lastLongestClicks`, `unsquashedClicks`
- `navBoost` / NavBoost re-ranking from SERP engagement
- **Public contradiction:** Google historically downplayed direct use of clicks for ranking; trial + leak suggest long-running click-based systems (~2005+ per VP testimony)

**SEO implication:** Title/meta that improve CTR without bait-and-switch; pages must satisfy intent (reduce bad clicks / quick returns).

### 2. Site-wide authority

- `siteAuthority` / site authority style metrics appear in documentation
- **Public contradiction:** Google denied "domain authority" as a score; leak suggests site-level authority signals exist

**SEO implication:** YMYL/crypto sites need site-wide trust (About, policies, entity schema, reviews), not only page-level optimization.

### 3. Chrome browser data

- `chromeInTotal`, `chrome_trans_clicks`, Chrome-related view/click aggregates
- **Public contradiction:** Google stated Chrome data not used for ranking

**SEO implication:** Real user engagement and brand demand matter; thin affiliate pages without brand footprint may underperform.

### 4. Title & topical matching

- `titlematchScore` — relevance of title to query
- Topical focus: `siteFocusScore`, `siteRadius` (site theme concentration vs. scatter)

**SEO implication:** Pair pages need keyword-aligned titles; avoid publishing unrelated blog spam on exchange domains.

### 5. Link graph (evolved PageRank)

Multiple PageRank variants documented (`rawPagerank`, deprecated NS seeds, `firstCoveragePageRank`). Anchor text still present but analysts note reduced omnipresence vs. early SEO era.

**SEO implication:** Quality editorial links still matter; anchor diversity; toxic link spikes (see Ahrefs tab) risk demotion.

### 6. Demotion & quality systems

Documented demotion-style attributes (names vary by module):

- Low-quality / thin content demotions (Panda lineage)
- Nav demotion (poor site navigation UX)
- Exact-match domain demotion
- Link mismatch / irrelevant link demotion
- User dissatisfaction signals

**SEO implication:** Fix UX navigation, avoid EMD-style microsites, align internal linking with money pages.

### 7. Freshness & sandbox

- Freshness attributes for time-sensitive queries
- "Sandbox" / young-site dampening discussed in analyst summaries (not a single named public attribute)

**SEO implication:** New pair pages need sustained internal links + external mentions over weeks, not only publish-once.

## What the leak does NOT tell us

- No numeric weights for attributes
- No proof every attribute is used in live Search ranking (may be deprecated, experimental, or used in other products)
- No replacement for Quality Rater Guidelines for YMYL judgment

## Use in Marketing SEO Booster

Rules extracted to IDs `LK-CW-*` in the leak rules database. Recommendations engine maps your **EEAT / YMYL / Checklist / Pro** failures to these signals.
