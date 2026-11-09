#!/usr/bin/env python3
"""Deterministic job-search coverage audit, no network access and no third-party dependencies.

The audit measures differences *between supplied search methods*, NOT true market
recall. Observations must come from real searches; the script cannot discover,
validate or submit applications by itself.

Run from the repository root:  uv run --locked python -m scripts.coverage_audit --input ...
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Let "python scripts/coverage_audit.py" find the project's own definition of "the same job link".
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jobhunter.job_identity import TRACKING_PARAMS, canonical_key  # noqa: E402

STRATEGIES = {"primary", "mba", "function", "employer_category", "secondary", "evergreen"}
FITS = {"very_high", "high", "medium", "low", "unknown"}
FIT_RANK = {"very_high": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
ELIGIBILITIES = {"confirmed_eligible", "possible", "unknown", "confirmed_ineligible"}
STATUSES = {"verified_open", "unverified", "confirmed_closed"}
APP_STATES = {"applied", "company_receipt_unconfirmed", "unknown", "not_applied_verified"}
ALREADY_APPLIED = {"applied", "company_receipt_unconfirmed"}  # a sent application is never "not applied"


def normalized_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").casefold()).strip()


def normalized_url(url: str) -> str:
    """A readable link: https, no "www.", no fragment, no tracking parameters (the project's list)."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError("official_url must be an absolute HTTP(S) URL")
    # Keep non-tracking query params: certain ATS providers encode requisition in them.
    query = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not TRACKING_PARAMS.match(k))
    return urlunsplit(("https", parts.netloc.casefold().removeprefix("www."), parts.path.rstrip("/") or "/",
                       urlencode(query), ""))


def link_key(url: str) -> str:
    """Which job a link points at: the project's own identity (Greenhouse, Lever, Ashby, LinkedIn aware)."""
    return canonical_key(normalized_url(url)) if url else ""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def one_of(value, allowed: set, message: str) -> None:
    # Check the type first: a list or object from the JSON must be a clean error, not a crash.
    require(isinstance(value, str) and value in allowed, message)


def group_observations(items: list[dict]) -> list[list[int]]:
    """Group sightings of the same job. The result never depends on the order of the input.

    Within one company: the same requisition id is the same job. A sighting without a requisition joins the
    one requisition that shares its link; if its link is shared by several requisitions it stays apart
    (marked ambiguous) and is never guessed. Sightings with neither a requisition nor a link merge only when
    title and place are identical. Different requisitions are never merged.
    """
    by_company: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_company[item["company"]].append(item)
    groups: list[dict] = []
    for company_items in by_company.values():
        with_req: dict[str, list[int]] = defaultdict(list)
        owners: dict[str, set[str]] = defaultdict(set)
        for it in company_items:
            if it["req"]:
                with_req[it["req"]].append(it["index"])
                if it["key"]:
                    owners[it["key"]].add(it["req"])
        grouped = {req: {"members": list(idx), "ambiguous": False} for req, idx in with_req.items()}
        by_link: dict[str, dict] = {}
        by_title: dict[tuple, dict] = {}
        for it in company_items:
            if it["req"]:
                continue
            if it["key"]:
                candidates = owners.get(it["key"], set())
                if len(candidates) == 1:
                    grouped[next(iter(candidates))]["members"].append(it["index"])
                else:
                    slot = by_link.setdefault(it["key"], {"members": [], "ambiguous": len(candidates) > 1})
                    slot["members"].append(it["index"])
            else:
                by_title.setdefault((it["title"], it["loc"]), {"members": [], "ambiguous": False})["members"].append(it["index"])
        groups.extend(list(grouped.values()) + list(by_link.values()) + list(by_title.values()))
    for g in groups:
        g["members"].sort()
    groups.sort(key=lambda g: g["members"][0])  # stable output order: first appearance in the input
    return groups


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
        one_of(strategy, STRATEGIES, f"Search {sid}: unknown strategy {strategy!r}")
        require(isinstance(s.get("query", ""), str) and s.get("query", "").strip(), f"Search {sid}: query required")
        search_by_id[sid] = s
    has_primary = any(s["strategy"] == "primary" for s in searches)

    items = []
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
            one_of(o.get(key, default), allowed, f"Observation {i}: invalid {key}")
        require(bool(o.get("source_url") or o.get("official_url")), f"Observation {i}: source_url or official_url required")
        try:
            clean, key = normalized_url(str(o.get("official_url", ""))), link_key(str(o.get("official_url", "")))
        except ValueError as e:
            raise ValueError(f"Observation {i}: {e}") from None
        items.append({"index": i, "company": normalized_text(o["company"]), "req": normalized_text(str(o.get("requisition_id", ""))),
                      "title": normalized_text(o["title"]), "loc": normalized_text(o["location"]), "key": key, "url": clean})

    results = []
    for g in group_observations(items):
        members = [items[i] for i in g["members"]]
        obs = [(observations[m["index"]], search_by_id[str(observations[m["index"]]["search_id"])]["strategy"]) for m in members]
        first = observations[members[0]["index"]]
        methods = sorted({strategy for _, strategy in obs})
        status_values = {o.get("official_application_status", "unverified") for o, _ in obs}
        app_values = {o.get("application_history", "unknown") for o, _ in obs}
        eligibility_values = {o.get("eligibility", "unknown") for o, _ in obs}
        fit_values = {o.get("fit", "unknown") for o, _ in obs}
        status = "conflicting" if {"verified_open", "confirmed_closed"} <= status_values else ("verified_open" if "verified_open" in status_values else ("confirmed_closed" if "confirmed_closed" in status_values else "unverified"))
        already_applied = bool(app_values & ALREADY_APPLIED)
        history_known = app_values == {"not_applied_verified"}
        hard_ineligible = "confirmed_ineligible" in eligibility_values
        eligibility_confirmed = "confirmed_eligible" in eligibility_values and not hard_ineligible
        strong_fit = bool(fit_values.intersection({"high", "very_high"}))
        # Open, strong and not ruled out. It becomes "actionable" only when nothing about it is still unknown.
        open_strong = strong_fit and status == "verified_open" and not already_applied and not hard_ineligible
        actionable = open_strong and history_known and eligibility_confirmed
        needs_check = open_strong and not actionable
        check_reasons = ([] if not needs_check else
                         (["application_history_unknown"] if not history_known else []) +
                         (["eligibility_not_confirmed"] if not eligibility_confirmed else []))
        was_primary = "primary" in methods
        missing_primary = actionable and not was_primary and has_primary
        check_missing_primary = needs_check and not was_primary and has_primary
        # Distinct from actionable: unresolved high-fit findings remain auditable. Needs a primary pass to compare with.
        recovery = (strong_fit and not was_primary and has_primary and status in {"unverified", "conflicting"}
                    and not already_applied and not hard_ineligible)
        reqs = sorted({m["req"] for m in members if m["req"]})
        results.append({
            "company": first["company"], "title": first["title"], "location": first["location"],
            "requisition_ids": reqs, "official_urls": sorted({m["url"] for m in members if m["url"]}),
            "search_methods": methods, "search_ids": sorted({o["search_id"] for o, _ in obs}),
            "source_urls": sorted({str(o.get("source_url") or o.get("official_url")) for o, _ in obs}),
            "fit": max(fit_values, key=FIT_RANK.__getitem__),
            "eligibility_conflict": len(eligibility_values) > 1 and "confirmed_ineligible" in eligibility_values,
            "application_history": "applied" if "applied" in app_values else ("company_receipt_unconfirmed" if "company_receipt_unconfirmed" in app_values else "not_applied_verified" if history_known else "unknown"),
            "official_application_status": status,
            "actionable_strong": actionable,
            "needs_check": needs_check, "check_reasons": check_reasons,
            "ambiguous_link": g["ambiguous"],
            "missed_by_primary": missing_primary,
            "needs_check_missed_by_primary": check_missing_primary,
            "secondary_recovery_pending": recovery,
            "status_conflict": status == "conflicting",
        })

    actionable = [x for x in results if x["actionable_strong"]]
    missed = [x for x in results if x["missed_by_primary"]]
    checks = [x for x in results if x["needs_check"]]
    checks_missed = [x for x in results if x["needs_check_missed_by_primary"]]
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
    if checks:
        warnings.append("Some strong, verified-open roles have unknown application history or unconfirmed eligibility; they are listed as needing a human check and are NOT counted as actionable.")
    if any(x["ambiguous_link"] for x in results):
        warnings.append("A link shared by several requisitions could not be assigned to one of them; those sightings were kept apart, not guessed.")
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
            "strong_open_needs_check": len(checks),
            "strong_open_needs_check_missed_by_primary": len(checks_missed),
            "alternate_only_strong_pending_verification": len(pending),
            "missed_share_within_discovered_actionable": round(len(missed)/len(actionable), 4) if actionable else None,
            "queries_by_strategy": dict(sorted(strategy_counts.items())),
            "distinct_jobs_by_strategy": discovery_counts,
        },
        "missed_by_primary": missed, "needs_check_missed_by_primary": checks_missed, "pending_recovery": pending,
        "jobs": results, "warnings": warnings,
    }


def markdown_report(result: dict) -> str:
    s = result["summary"]
    lines = ["### Search-coverage audit", "",
             f"Searches recorded: **{s['queries_executed']}**; unique observed jobs: **{s['unique_jobs']}**.",
             f"Strong, verified-open roles with application history verified and eligibility confirmed: **{s['actionable_strong_jobs']}**; absent from primary pass: **{s['actionable_strong_missed_by_primary']}**.",
             f"Strong, verified-open roles needing a human check (history or eligibility unknown): **{s['strong_open_needs_check']}**; absent from primary pass: **{s['strong_open_needs_check_missed_by_primary']}**.",
             f"Alternate-only high-fit roles requiring verification: **{s['alternate_only_strong_pending_verification']}**.", "",
             "| Recovered role | Search methods | Official application evidence | Why it is listed |",
             "|---|---|---|---|"]
    rows = ([(x, "missed by primary") for x in result["missed_by_primary"]] +
            [(x, "human check: " + ", ".join(x["check_reasons"])) for x in result["needs_check_missed_by_primary"]] +
            [(x, "alternate-only, unverified") for x in result["pending_recovery"]])
    for x, why in rows:
        label = (x["company"] + " — " + x["title"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {label} | {', '.join(x['search_methods'])} | {x['official_application_status']} | {why} |")
    if not rows:
        lines.append("| None in supplied observations | — | — | — |")
    lines += ["", "*This compares only searches actually recorded in the input. It does not measure all jobs on the internet or independently confirm employer status.*"]
    return "\n".join(lines) + "\n"


def check_output_path(path: Path | None) -> None:
    """Fail before any work if the output cannot be created. An existing file is never overwritten."""
    if path is None:
        return
    require(path.parent.is_dir(), f"output folder does not exist: {path.parent}")
    require(not path.exists(), f"{path} already exists; this command never overwrites an existing file")


def write_new(path: Path, text: str) -> None:
    try:
        with path.open("x", encoding="utf-8") as handle:  # "x" refuses an existing file even if it appeared meanwhile
            handle.write(text)
    except FileExistsError:
        raise ValueError(f"{path} already exists; this command never overwrites an existing file") from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="JSON evidence collected from the job scan")
    parser.add_argument("--output", type=Path, help="Optional machine-readable JSON audit (must not exist yet)")
    parser.add_argument("--markdown", type=Path, help="Optional short Markdown audit (must not exist yet)")
    args = parser.parse_args(argv)
    try:
        check_output_path(args.output)
        check_output_path(args.markdown)
        require(args.output is None or args.markdown is None or args.output != args.markdown,
                "--output and --markdown must be different files")
        result = audit(json.loads(args.input.read_text(encoding="utf-8")))
        json_text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            write_new(args.output, json_text)
        if args.markdown:
            write_new(args.markdown, markdown_report(result))
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"Coverage audit failed: {e}", file=sys.stderr)
        return 2
    if not args.output and not args.markdown:
        print(json_text, end="")
    else:
        print(f"Audited {result['summary']['unique_jobs']} unique observed roles; missed {result['summary']['actionable_strong_missed_by_primary']} strong roles from primary pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
