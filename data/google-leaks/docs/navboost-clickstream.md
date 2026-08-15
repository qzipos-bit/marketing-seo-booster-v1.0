# NavBoost & Clickstream Signals

> **Sources:** Content Warehouse leak attributes · US v. Google antitrust trial testimony (Pandu Nayak, 2023) · SparkToro / iPullRank analysis.

## System overview

**NavBoost** is an internal Google system that adjusts rankings using aggregated user navigation behavior from search results. It was referenced in leaked API docs and confirmed in federal antitrust proceedings.

## Key leaked / trial-referenced attributes

| Attribute | Interpretation (analyst consensus) |
|-----------|-----------------------------------|
| `goodClicks` | Positive engagement clicks from SERP |
| `badClicks` | Quick return / dissatisfaction clicks |
| `lastLongestClicks` | Dwell / longest click patterns on result set |
| `unsquashedClicks` | Raw click counts before normalization |
| `navBoost` | NavBoost scoring container / re-rank feature |

## Google public position vs. leak

| Topic | Public messaging | Leak / trial signal |
|-------|------------------|---------------------|
| Click data | Often minimized as ranking input | Long-running click-based re-ranking |
| User behavior | "Helpful content" abstractly | Quantified good/bad click classes |

## Operational recommendations (crypto / YMYL)

1. **SERP snippet honesty** — Title/H1/meta must match page content; bait titles create bad clicks on regulated topics.
2. **Intent satisfaction** — Exchange pair pages: rates, limits, steps above the fold; reduce pogo-sticking to competitors.
3. **Brand queries** — NavBoost favors sites users recognize; invest in brand search volume and consistent NAP/entity.
4. **A/B titles carefully** — Winning CTR with misleading claims increases bad-click risk on YMYL pages.

## Audit mapping

| Audit item | Why |
|------------|-----|
| EE18, EE19 | Trust / transparency reduces bad clicks |
| YY02, YY03 | Harm prevention — misleading claims → dissatisfaction |
| Checklist title/meta items | titlematchScore alignment |
| Pro bot / render gap | If Googlebot sees different content → engagement mismatch |

## Further reading

- SparkToro original leak post (NavBoost section)
- DOJ trial transcripts / coverage: Search Engine Journal, The Verge (2023)
- iPullRank Google Algo Leak repository
