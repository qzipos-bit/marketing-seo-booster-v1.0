# Site Authority, Topicality & Title Matching

> **Leak attributes:** `siteAuthority`, `siteFocusScore`, `siteRadius`, `titlematchScore`, topical embedding fields.

## siteAuthority

Analysts identified site-wide authority metrics in leaked modules. Functionally similar to what SEOs called "domain authority" — Google publicly avoided endorsing third-party DA scores but leak suggests **internal** site-level authority exists.

**For crypto exchanges:** Authority built via regulatory transparency, press (DR 40+), consistent entity, not spam link farms.

## Topical focus (siteFocusScore / siteRadius)

Measures whether a site stays on-topic or publishes scattered unrelated content to chase long-tail.

**Risk for Quickex:** Exchange + casino blog spam + unrelated AI articles → topical radius penalty.

**Fix:** Cluster content by intent (swap guides, pair SEO, compliance) with strong internal linking to money pages.

## titlematchScore

Measures alignment between page title and query intent. Still weighted per multiple leak analysts (Mike King / SparkToro).

**Fix:** Pair pages: `{FROM} to {TO} Exchange | Quickex` pattern; avoid generic "Best Crypto Platform".

## Audit mapping

| Signal | Audit triggers |
|--------|----------------|
| siteAuthority | EEAT A*, YMYL Y4, low Ahrefs quality links |
| siteFocusScore | Thin blog, off-topic content warnings |
| titlematchScore | Checklist title/H1 failures, duplicate titles (Pro) |

## English sources

- SparkToro leak article (site authority section)
- iPullRank attribute browser
- Search Engine Land leak coverage
