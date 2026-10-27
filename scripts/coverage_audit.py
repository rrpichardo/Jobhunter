#!/usr/bin/env python3
"""Deterministic job-search coverage audit, no network access or dependencies.

The audit measures differences *between supplied search methods*, NOT true market
recall. Observations must come from real searches; the script cannot discover,
validate or submit applications by itself.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

STRATEGIES = {"primary", "mba", "function", "employer_category", "secondary", "evergreen"}
FITS = {"very_high", "high", "medium", "low", "unknown"}
ELIGIBILITIES = {"confirmed_eligible", "possible", "unknown", "confirmed_ineligible"}
STATUSES = {"verified_open", "unverified", "confirmed_closed"}
APP_STATES = {"applied", "company_receipt_unconfirmed", "unknown", "not_applied_verified"}
TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "referrer", "source", "fbclid", "gclid"}


def normalized_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").casefold()).strip()


def normalized_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("official_url must be an absolute HTTP(S) URL")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING and not k.lower().startswith("utm_")]
    # Keep non-tracking query params: certain ATS providers encode requisition in them.
    return urlunsplit(("https", parts.netloc.casefold().removeprefix("www."), parts.path.rstrip("/") or "/", urlencode(sorted(query)), ""))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def audit(data: dict) -> dict:
    require(isinstance(data, dict), "Top-level input must be an object")
    searches = data.get("searches")
    observations = data.get("observations")
    require(isinstance(searches, list) and len(searches) > 0, "Provide nonempty 'searches' array")
    require(isinstance(observations, list), "Provide 'observations' array")

    search_by_id = {}
    for s in searches:
        require(isinstance(s, dict), "Search entries must be objects")
        sid = str(s.get("id", "")).strip()
        strategy = s.get("strategy")
        require(sid and sid not in search_by_id, "Search IDs must be unique and nonblank")
        require(strategy in STRATEGIES, f"Search {sid}: unknown strategy {strategy!r}")
        require(isinstance(s.get("query", ""), str) and s.get("query", "").strip(), f"Search {sid}: query required")
        search_by_id[sid] = s

    groups = []
    for i, o in enumerate(observations):
        require(isinstance(o, dict), f"Observation {i}: expected object")
        search_id = str(o.get("search_id", ""))
        require(search_id in search_by_id, f"Observation {i}: unknown search_id {search_id!r}")
        for key in ("company", "title", "location"):
            require(isinstance(o.get(key), str) and o[key].strip(), f"Observation {i}: {key} required")
        for key, allowed, default in (
            ("fit", FITS, "unknown"), ("eligibility", ELIGIBILITIES, "unknown"),
            ("official_application_status", STATUSES, "unverified"),
            ("application_history", APP_STATES, "unknown"),
        ):
            require(o.get(key, default) in allowed, f"Observation {i}: invalid {key}")
        require(bool(o.get("source_url") or o.get("official_url")), f"Observation {i}: source_url or official_url required")
        company = normalized_text(o["company"])
        req = normalized_text(str(o.get("requisition_id", "")))
        title = normalized_text(o["title"])
        loc = normalized_text(o["location"])
        url = normalized_url(str(o.get("official_url", "")))

        group = None
        for g in groups:
            if g["company_key"] != company:
                continue
            if req and g["reqs"] and req in g["reqs"]:
                group = g; break
            if url and url in g["urls"] and (not req or not g["reqs"] or req in g["reqs"]):
                group = g; break
            # Title/location is intentionally NOT enough to merge two requisitions.
            if not req and not url and not g["reqs"] and not g["urls"] and (title, loc) == (g["title_key"], g["loc_key"]):
                group = g; break
        if group is None:
            group = {"company_key": company, "title_key": title, "loc_key": loc,
                     "company": o["company"], "title": o["title"], "location": o["location"],
                     "reqs": set(), "urls": set(), "observations": []}
            groups.append(group)
        if req:
            group["reqs"].add(req)
        if url:
            group["urls"].add(url)
        group["observations"].append((o, search_by_id[search_id]["strategy"]))

    results = []
    for g in groups:
        obs = g["observations"]
        methods = sorted({strategy for _, strategy in obs})
        status_values = {o.get("official_application_status", "unverified") for o, _ in obs}
        app_values = {o.get("application_history", "unknown") for o, _ in obs}
        eligibility_values = {o.get("eligibility", "unknown") for o, _ in obs}
        fit_values = {o.get("fit", "unknown") for o, _ in obs}
        status = "conflicting" if {"verified_open", "confirmed_closed"} <= status_values else ("verified_open" if "verified_open" in status_values else ("confirmed_closed" if "confirmed_closed" in status_values else "unverified"))
        applied = "applied" in app_values
        strong_fit = bool(fit_values.intersection({"high", "very_high"}))
        hard_ineligible = "confirmed_ineligible" in eligibility_values
        actionable = strong_fit and status == "verified_open" and not applied and not hard_ineligible
        was_primary = "primary" in methods
        missing_primary = actionable and not was_primary and any(s["strategy"] == "primary" for s in searches)
        # Distinct from actionable: unresolved high-fit findings remain auditable.
        recovery = strong_fit and not was_primary and status in {"unverified", "conflicting"} and not applied and not hard_ineligible
        results.append({
            "company": g["company"], "title": g["title"], "location": g["location"],
            "requisition_ids": sorted(g["reqs"]), "official_urls": sorted(g["urls"]),
            "search_methods": methods, "search_ids": sorted({o["search_id"] for o, _ in obs}),
            "source_urls": sorted({str(o.get("source_url") or o.get("official_url")) for o, _ in obs}),
            "fit": "very_high" if "very_high" in fit_values else ("high" if "high" in fit_values else sorted(fit_values)[0]),
            "eligibility_conflict": len(eligibility_values) > 1 and "confirmed_ineligible" in eligibility_values,
            "application_history": "applied" if applied else ("company_receipt_unconfirmed" if "company_receipt_unconfirmed" in app_values else "unknown" if "unknown" in app_values else "not_applied_verified"),
            "official_application_status": status,
            "actionable_strong": actionable,
            "missed_by_primary": missing_primary,
            "secondary_recovery_pending": recovery,
            "status_conflict": status == "conflicting",
        })

    actionable = [x for x in results if x["actionable_strong"]]
    missed = [x for x in results if x["missed_by_primary"]]
    pending = [x for x in results if x["secondary_recovery_pending"]]
    strategy_counts = Counter(s["strategy"] for s in searches)
    discovery_counts = {strategy: sum(strategy in x["search_methods"] for x in results) for strategy in sorted(STRATEGIES)}
    warnings = []
    if not strategy_counts["primary"]:
        warnings.append("No primary search recorded; missed-by-primary comparison cannot be interpreted as an evaluated primary pass.")
    if not (set(strategy_counts) - {"primary"}):
        warnings.append("No alternative discovery strategy recorded; the audit cannot test primary-search blind spots.")
    if any(x["status_conflict"] for x in results):
        warnings.append("Conflicting official-open/closed evidence requires human resolution; none of these are counted as verified open.")
    if pending:
        warnings.append("High-fit alternate-only candidates require official application verification before they can be promoted.")
    warnings.append("Missed share is a within-input discovery-overlap proxy, NOT market-wide recall or proof of complete search coverage.")

    return {
        "run_id": str(data.get("run_id", "unknown")),
        "summary": {
            "queries_executed": len(searches), "observations": len(observations),
            "unique_jobs": len(results), "actionable_strong_jobs": len(actionable),
            "actionable_strong_found_by_primary": len(actionable) - len(missed),
            "actionable_strong_missed_by_primary": len(missed),
            "alternate_only_strong_pending_verification": len(pending),
            "missed_share_within_discovered_actionable": round(len(missed)/len(actionable), 4) if actionable else None,
            "queries_by_strategy": dict(sorted(strategy_counts.items())),
            "distinct_jobs_by_strategy": discovery_counts,
        },
        "missed_by_primary": missed, "pending_recovery": pending,
        "jobs": results, "warnings": warnings,
    }


def markdown_report(result: dict) -> str:
    s = result["summary"]
    lines = ["### Search-coverage audit", "",
             f"Searches recorded: **{s['queries_executed']}**; unique observed jobs: **{s['unique_jobs']}**.",
             f"Strong, reported-as-verified-open, non-applied matches: **{s['actionable_strong_jobs']}**; absent from primary pass: **{s['actionable_strong_missed_by_primary']}**.",
             f"Alternate-only high-fit roles requiring verification: **{s['alternate_only_strong_pending_verification']}**.", "",
             "| Recovered role | Search methods | Official application evidence |",
             "|---|---|---|"]
    for x in result["missed_by_primary"] + result["pending_recovery"]:
        label = (x["company"] + " — " + x["title"]).replace("|", "\\|")
        lines.append(f"| {label} | {', '.join(x['search_methods'])} | {x['official_application_status']} |")
    if not result["missed_by_primary"] and not result["pending_recovery"]:
        lines.append("| None in supplied observations | — | — |")
    lines += ["", "*This compares only searches actually recorded in the input. It does not measure all jobs on the internet or independently confirm employer status.*"]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="JSON evidence collected from the job scan")
    parser.add_argument("--output", type=Path, help="Optional machine-readable JSON audit")
    parser.add_argument("--markdown", type=Path, help="Optional short Markdown audit")
    args = parser.parse_args(argv)
    try:
        result = audit(json.loads(args.input.read_text(encoding="utf-8")))
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"Coverage audit failed: {e}", file=sys.stderr)
        return 2
    json_text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(json_text, encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(markdown_report(result), encoding="utf-8")
    if not args.output and not args.markdown:
        print(json_text, end="")
    else:
        print(f"Audited {result['summary']['unique_jobs']} unique observed roles; missed {result['summary']['actionable_strong_missed_by_primary']} strong roles from primary pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
