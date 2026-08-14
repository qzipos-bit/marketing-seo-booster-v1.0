"""Map audit failures to Google leak rules → actionable recommendations."""

from __future__ import annotations

from typing import Any

from app.leak_library import get_document, get_rule, list_rules
from app.pro_seo_auditor import build_priority_roadmap
from app.storage import (
    latest_checklist_run,
    latest_pro_run,
    latest_specialist_run,
)


def _collect_audit_issues() -> list[dict[str, Any]]:
    """Gather fail/warn/manual items from all audit sources."""
    issues: list[dict[str, Any]] = []

    sources = [
        ("checklist", latest_checklist_run()),
        ("eeat", latest_specialist_run("eeat")),
        ("ymyl", latest_specialist_run("ymyl")),
        ("pro", latest_pro_run()),
    ]

    for source_name, run in sources:
        if not run:
            continue
        results = run.get("results") or []
        for r in results:
            st = r.get("status")
            if st not in ("fail", "warn", "manual"):
                continue
            issues.append(
                {
                    "source": source_name,
                    "id": r.get("id"),
                    "status": st,
                    "severity": r.get("severity", "medium"),
                    "title": r.get("title"),
                    "evidence": (r.get("evidence") or "")[:300],
                    "block": r.get("block"),
                }
            )

    return issues


def _priority_for(severity: str, status: str, rule_severity: str) -> str:
    sev_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    combined = min(sev_rank.get(severity, 3), sev_rank.get(rule_severity, 3))
    if status == "fail" and combined == 0:
        return "P0"
    if status == "fail" and combined <= 1:
        return "P1"
    if status in ("fail", "warn") and combined <= 1:
        return "P1"
    if status == "fail":
        return "P2"
    return "P3"


def build_leak_recommendations() -> dict[str, Any]:
    """
    Cross-reference audit issues with leak rules.
    Returns prioritized recommendations with leak citations.
    """
    issues = _collect_audit_issues()
    rules = list_rules()
    rules_by_trigger: dict[str, list[dict[str, Any]]] = {}
    for rule in rules:
        for tid in rule.get("audit_triggers") or []:
            rules_by_trigger.setdefault(tid.upper(), []).append(rule)

    recommendations: list[dict[str, Any]] = []
    seen: set[str] = set()

    for issue in issues:
        iid = (issue.get("id") or "").upper()
        matched_rules = rules_by_trigger.get(iid, [])
        if not matched_rules:
            continue

        for rule in matched_rules:
            key = f"{issue['id']}:{rule['id']}"
            if key in seen:
                continue
            seen.add(key)

            doc = get_document(rule["document_id"])
            priority = _priority_for(
                issue.get("severity", "medium"),
                issue.get("status", "warn"),
                rule.get("severity", "medium"),
            )

            recommendations.append(
                {
                    "priority": priority,
                    "audit_source": issue["source"],
                    "audit_id": issue["id"],
                    "audit_status": issue["status"],
                    "audit_title": issue["title"],
                    "audit_evidence": issue["evidence"],
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "rule_category": rule["category"],
                    "leak_attributes": rule["leak_attributes"],
                    "google_public": rule["google_public"],
                    "leak_evidence": rule["leak_evidence"],
                    "action": rule["recommendation"],
                    "document_id": rule["document_id"],
                    "document_title": doc["title"] if doc else rule["document_id"],
                    "document_url": doc["source_url"] if doc else None,
                    "sort": (
                        {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority, 9),
                        issue["id"] or "",
                    ),
                }
            )

    recommendations.sort(key=lambda x: x["sort"])
    for r in recommendations:
        r.pop("sort", None)

    # Fallback roadmap items without leak mapping
    roadmap = []
    for source_name, run in [
        ("checklist", latest_checklist_run()),
        ("eeat", latest_specialist_run("eeat")),
        ("ymyl", latest_specialist_run("ymyl")),
        ("pro", latest_pro_run()),
    ]:
        if run and run.get("results"):
            for item in build_priority_roadmap(run["results"]):
                item["audit_source"] = source_name
                roadmap.append(item)

    mapped_ids = {r["audit_id"] for r in recommendations}
    unmapped = [r for r in roadmap if r.get("id") not in mapped_ids]

    audit_summary = {
        "total_issues": len(issues),
        "mapped": len(recommendations),
        "unmapped_roadmap": len(unmapped),
        "sources": {
            "checklist": bool(latest_checklist_run()),
            "eeat": bool(latest_specialist_run("eeat")),
            "ymyl": bool(latest_specialist_run("ymyl")),
            "pro": bool(latest_pro_run()),
        },
    }

    if not any(audit_summary["sources"].values()):
        audit_summary["hint"] = (
            "Запусти EEAT, YMYL, Checklist или Pro аудит — рекомендации строятся на их результатах."
        )

    return {
        "recommendations": recommendations,
        "unmapped_roadmap": unmapped[:20],
        "audit_summary": audit_summary,
        "top_priorities": [r for r in recommendations if r["priority"] in ("P0", "P1")][:12],
    }


def export_recommendations_markdown() -> str:
    data = build_leak_recommendations()
    lines = [
        "# Google Leak Recommendations — Audit-Based Actions",
        "",
        f"Mapped: **{data['audit_summary'].get('mapped', 0)}** · "
        f"Audit issues: **{data['audit_summary'].get('total_issues', 0)}**",
        "",
    ]

    if data["audit_summary"].get("hint"):
        lines.append(f"> {data['audit_summary']['hint']}")
        lines.append("")

    for rec in data["recommendations"]:
        lines.extend(
            [
                f"## {rec['priority']} · {rec['audit_id']} — {rec['audit_title']}",
                "",
                f"**Audit:** {rec['audit_source']} ({rec['audit_status']})  ",
                f"**Leak rule:** `{rec['rule_id']}` — {rec['rule_name']}  ",
                f"**Attributes:** {rec['leak_attributes']}  ",
                f"**Google said:** _{rec['google_public']}_  ",
                f"**Leak shows:** {rec['leak_evidence']}  ",
                f"**Source:** [{rec['document_title']}]({rec['document_url'] or '#'})",
                "",
                f"### Действие",
                rec["action"],
                "",
                f"_Evidence:_ {rec['audit_evidence'] or '—'}",
                "",
                "---",
                "",
            ]
        )

    return "\n".join(lines)
