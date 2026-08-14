#!/usr/bin/env python3
"""CLI runner for Kie + SEO checks (without starting the web server)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.model_checker import run_model_check
from app.seo_checker import run_seo_check
from app.storage import (
    finish_model_run,
    finish_seo_run,
    init_db,
    start_model_run,
    start_seo_run,
)


async def run_models() -> int:
    run_id = start_model_run()
    payload = await run_model_check()
    if payload.get("error") and not payload.get("results"):
        print(payload["error"], file=sys.stderr)
        finish_model_run(run_id, [])
        return 1
    summary = finish_model_run(run_id, payload["results"], payload.get("credit"))
    print(json.dumps({"run_id": run_id, "summary": summary, **payload}, ensure_ascii=False, indent=2))
    return 0 if summary.get("fail", 0) == 0 else 2


async def run_seo() -> int:
    run_id = start_seo_run()
    payload = await run_seo_check()
    if payload.get("error") and not payload.get("results"):
        print(payload["error"], file=sys.stderr)
        finish_seo_run(run_id, [])
        return 1
    summary = finish_seo_run(run_id, payload["results"])
    print(json.dumps({"run_id": run_id, "summary": summary, **payload}, ensure_ascii=False, indent=2))
    return 0 if summary.get("fail", 0) == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Kie + SEO monitor CLI")
    parser.add_argument("target", choices=["models", "seo", "all"], help="What to check")
    args = parser.parse_args()

    init_db()
    if args.target == "models":
        return asyncio.run(run_models())
    if args.target == "seo":
        return asyncio.run(run_seo())
    code = asyncio.run(run_models())
    seo_code = asyncio.run(run_seo())
    return max(code, seo_code)


if __name__ == "__main__":
    raise SystemExit(main())
