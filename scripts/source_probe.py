"""Probe every V0 source once and build one combined delivery artifact; no Sheet writes.

Run with `uv run --locked python -m scripts.source_probe --output <new file outside checkout>`.
One bounded GET per source, no retries, no login, no social access, no secrets. A 401/403/
406/429 stops that source immediately (`blocked`). Keys, accounts and mailboxes that are not
set up are recorded `needs setup` without any request. Keyed APIs (JSearch, Jooble) get exactly one
request each and their keys are never recorded, printed or put in an error. The artifact is delivered
separately with `scripts.sheets_sync`.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import time
from urllib.parse import quote

import httpx
import yaml

from jobhunter.artifacts import safe_error_code, write_artifact
from jobhunter.postings import (AI_TERMS, DETAIL_SOURCES, LISTING_ONLY, PARSERS, Posting, ai_pm_match,
                                collection_location_match, dedupe, is_pm_title, to_row)

USER_AGENT = "JobHunterBot/0.1 (personal job search; polite single requests)"
MAX_BYTES = 40 * 1024 * 1024
PER_SOURCE_LIMIT = 8
TOTAL_LIMIT = 150
BLOCKED = {401, 403, 406, 429}
URLS = {"greenhouse": "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true",
        "lever": "https://api.lever.co/v0/postings/{board}?mode=json",
        "ashby": "https://api.ashbyhq.com/posting-api/job-board/{board}"}
JSON_KINDS = {"greenhouse", "lever", "ashby", "remotive", "remoteok", "himalayas", "jobicy",
              "themuse", "hn", "jsearch", "jooble"}
KEYED_KINDS = {"jsearch", "jooble"}

# httpx logs every request URL at INFO, and Jooble's key is in its URL path.
for _name in ("httpx", "httpcore"):
    logging.getLogger(_name).setLevel(logging.WARNING)


def record(source_id, status, stamp, *, error="", http=None, listed=None, valid=None, rejected=None,
           candidates=None, selected=0, coverage="", attempts=1):
    return {"source_id": source_id, "status": status, "captured_at": stamp, "jobs_fetched": listed,
            "valid_jobs": valid, "rejected_items": rejected, "pm_candidates": candidates,
            "selected_for_m0": selected, "attempts": attempts, "http_status": http,
            "retry_after_seconds": None, "coverage": coverage, "error": error}


def fetch_once(client, url):
    """(status, text, error_code). One attempt; never follows redirects or retries."""
    return _send(client, 'GET', url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, */*"})


def _send(client, method, url, **request):
    try:
        with client.stream(method, url, timeout=30, follow_redirects=False, **request) as response:
            if response.status_code != 200:
                return response.status_code, '', ''
            data = bytearray()
            for chunk in response.iter_bytes(chunk_size=min(65536, MAX_BYTES + 1)):
                if len(data) + len(chunk) > MAX_BYTES:
                    return response.status_code, None, 'invalid_board_response'
                data.extend(chunk)
            try:
                text = data.decode(response.encoding or 'utf-8', errors='replace')
            except LookupError:
                text = data.decode('utf-8', errors='replace')
            return response.status_code, text, ''
    except httpx.TimeoutException:
        return None, None, "timeout"
    except httpx.HTTPError:
        return None, None, "transport_error"


def keyed_request(entry, environ):
    """(missing env names, request kwargs). The kwargs hold the secret; never record or print them."""
    values = {name: (environ.get(name) or "").strip() for name in entry["env"]}
    missing = [name for name, value in values.items() if not value]
    if missing:
        return missing, None
    base = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if entry["kind"] == "jsearch":
        return [], {"method": "GET", "url": entry["url"], "params": entry["params"],
                    "headers": {**base, "X-RapidAPI-Key": values["JSEARCH_API_KEY"],
                                "X-RapidAPI-Host": "jsearch.p.rapidapi.com"}}
    return [], {"method": "POST", "url": entry["url"].rstrip("/") + "/" + quote(values["JOOBLE_API_KEY"], safe=""),
                "json": entry["body"], "headers": base}


def fetch_keyed(client, request):
    """Same contract as fetch_once for a request carrying a secret.

    Only status codes and fixed error codes leave this function: exception text and URLs can
    contain the key, so they are never kept.
    """
    request = dict(request)
    method, url = request.pop("method"), request.pop("url")
    try:
        return _send(client, method, url, **request)
    except Exception:  # noqa: BLE001 - any message may embed the URL; map it to a fixed code
        return None, None, "transport_error"


def fetch_details(client, entry, stubs, stamp, *, delay, sleep):
    """One polite GET per shortlisted job page; a refusal stops the rest for this source."""
    postings, rejected, problem, attempts = [], 0, None, 0
    detail = DETAIL_SOURCES[entry["kind"]][1]
    for stub in stubs:
        sleep(delay)
        attempts += 1
        status, body, error = fetch_once(client, stub["url"])
        if error or status != 200:
            rejected += 1
            if status in BLOCKED:
                problem = ('blocked', f'http_{status}', status)
                break  # stop this source immediately; never retry or probe further
            if problem is None:
                problem = ('failed', error or f'http_{status}', status)
            continue
        try:
            found = detail(body)
            postings.append(Posting(stub["job_id"], entry["id"], found.get("company") or stub["company"], stub["title"],
                                    found.get("location") or stub["location"], found["text"], stub["url"], stamp,
                                    salary=found.get("salary") or stub["salary"], tag="other"))
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            rejected += 1
    return postings, rejected, problem, attempts


def probe_source(client, entry, stamp, *, delay=0, sleep=time.sleep, environ=None):
    """Returns (source record or None for an unresponsive candidate, postings, note)."""
    kind, source_id = entry["kind"], entry["id"]
    url = entry["url"]
    if kind in KEYED_KINDS:
        missing, request = keyed_request(entry, os.environ if environ is None else environ)
        if missing:
            return (record(source_id, "needs setup", stamp, attempts=0), [],
                    "keys_missing:" + ",".join(missing))
        status, body, error = fetch_keyed(client, request)
        del request  # the key never outlives the call
    else:
        status, body, error = fetch_once(client, url)
    if error:
        return record(source_id, "failed", stamp, error=error), [], error
    if status == 404 and entry.get("candidate"):
        return None, [], "not_found"
    if status in BLOCKED:
        return record(source_id, "blocked", stamp, error=f"http_{status}", http=status), [], f"blocked_{status}"
    if status != 200:
        return record(source_id, "failed", stamp, error=f"http_{status}", http=status), [], f"http_{status}"
    ctx = {"board": entry.get("board", ""), "company": entry.get("company", ""),
           "tag": entry.get("tag", "other"), "source_id": source_id, "captured_at": stamp}
    try:
        data = json.loads(body) if kind in JSON_KINDS else body
    except (ValueError, RecursionError):
        return record(source_id, "failed", stamp, error="invalid_json", http=200), [], "invalid_json"
    problem, attempts, detail_skipped = None, 1, 0
    try:
        if kind in LISTING_ONLY:
            counts = LISTING_ONLY[kind](data, ctx)
            return record(source_id, "OK-zero-jobs", stamp, http=200, listed=counts["listed"],
                          valid=counts["listed"], rejected=0, candidates=counts["pm_titles"],
                          coverage="partial-response"), [], "listing_only"
        if kind in DETAIL_SOURCES:
            stubs, rejected = DETAIL_SOURCES[kind][0](data, {**ctx, "url": url})
            shortlist = [s for s in stubs if is_pm_title(s["title"])
                         and collection_location_match(s["location"], s["salary"])]
            shortlist.sort(key=lambda stub: not bool(AI_TERMS.search(stub['title'])))
            detail_skipped = max(0, len(shortlist) - PER_SOURCE_LIMIT)
            postings, failed, problem, detail_attempts = fetch_details(
                client, entry, shortlist[:PER_SOURCE_LIMIT], stamp, delay=delay, sleep=sleep)
            attempts += detail_attempts
            rejected += failed
            total = len(stubs)
        else:
            postings, rejected, total = PARSERS[kind](data, ctx)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        code = "duplicate_source_id" if str(exc) == "duplicate_source_id" else "invalid_board_response"
        return record(source_id, "failed", stamp, error=code, http=200), [], code
    candidates = [p for p in postings if is_pm_title(p.title)]
    selected = [p for p in postings if ai_pm_match(p)][:PER_SOURCE_LIMIT]
    coverage = "complete-response" if entry.get("board") else "partial-response"
    if kind in DETAIL_SOURCES:
        candidates = shortlist
    if rejected:
        coverage += "-with-rejections"
    skipped_note = f'; details_skipped={detail_skipped}' if detail_skipped else ''
    if problem is not None:
        status, error, http = problem
        return record(source_id, status, stamp, error=error, http=http, listed=total,
                      valid=len(postings), rejected=rejected, candidates=len(candidates),
                      selected=len(selected), coverage=coverage, attempts=attempts), selected, error + skipped_note
    if not postings and rejected:
        return record(source_id, "failed", stamp, error="invalid_items_quarantined", http=200, listed=total,
                      valid=0, rejected=rejected, candidates=0, coverage=coverage), [], "invalid_items" + skipped_note
    status = "OK" if selected else "OK-zero-jobs"
    return record(source_id, status, stamp, http=200, listed=total, valid=len(postings), rejected=rejected,
                  candidates=len(candidates), selected=len(selected), coverage=coverage, attempts=attempts), selected, "ok" + skipped_note


def fair_order(items):
    """Round-robin (posting, note) pairs by source, keeping each source's own order.

    The Sheet writer takes at most TOTAL_LIMIT jobs per run. Without this, sources early in the
    registry fill the cap and later ones (for example the keyed APIs) never deliver anything.
    """
    queues = {}
    for item in items:
        queues.setdefault(item[0].source_id, []).append(item)
    ordered, depth = [], 0
    while len(ordered) < len(items):
        for queue in queues.values():
            if depth < len(queue):
                ordered.append(queue[depth])
        depth += 1
    return ordered


def entries(registry):
    for kind, boards in registry["boards"].items():
        for board in boards:
            yield {"id": f"{kind}:{board['board']}", "kind": kind, "url": URLS[kind].format(board=board["board"]),
                   **board}
    for group in ("aggregators", "keyed_apis", "detail_sources", "listing_only"):
        yield from registry.get(group, [])


def run(registry, client, *, delay=1.0, sleep=time.sleep, environ=None,
        now=lambda: datetime.now(timezone.utc).isoformat()):
    environ = os.environ if environ is None else environ
    stamp = now()
    sources, jobs, notes = [], [], {}
    for entry in entries(registry):
        record_, selected, note = probe_source(client, entry, stamp, delay=delay, sleep=sleep,
                                                    environ=environ)
        notes[entry["id"]] = note
        if record_ is not None:
            sources.append(record_)
            jobs.extend(selected)
        sleep(delay)
    for item in registry["needs_setup"]:
        missing = [name for name in item["env"] if not environ.get(name)]
        sources.append(record(item["id"], "needs setup", stamp, attempts=0))
        notes[item["id"]] = ("keys_missing:" + ",".join(missing) if missing else "setup_or_collector_pending")
    unique = dedupe(jobs)
    duplicates = len(jobs) - len(unique)
    unique = fair_order(unique)  # the writer accepts at most TOTAL_LIMIT jobs; share them across sources
    rows, kept = [], {}
    for posting, note in unique:
        if len(rows) >= TOTAL_LIMIT:
            break
        rows.append(to_row(posting, note))
        kept[posting.source_id] = kept.get(posting.source_id, 0) + 1
    notes["duplicates_merged"] = duplicates
    omitted = {}
    for posting, _ in unique[len(rows):]:
        omitted[posting.source_id] = omitted.get(posting.source_id, 0) + 1
    notes['total_limit_skipped'] = sum(omitted.values())
    for source_id, count in omitted.items():
        notes[source_id] += f'; total_limit_skipped={count}'
    for source in sources:  # a capped or merged source must report what was actually delivered
        source["selected_for_m0"] = kept.get(source["source_id"], 0)
        if source["status"] == "OK" and not source["selected_for_m0"]:
            source["status"] = "OK-zero-jobs"
    return {"schema_version": 2, "sources": sources, "jobs": rows,
            "extraction": {"selected": len(rows), "validated": len(rows),
                           "status": "complete" if rows else "partial-or-empty"},
            "probe": {"notes": notes}}


def summary(payload):
    lines = [f"{'source':<28}{'status':<14}{'fetched':>8}{'PM':>5}{'delivered':>10}  note"]
    for source in payload["sources"]:
        lines.append(f"{source['source_id']:<28}{source['status']:<14}{str(source['jobs_fetched'] or '-'):>8}"
                     f"{str(source['pm_candidates'] if source['pm_candidates'] is not None else '-'):>5}"
                     f"{source['selected_for_m0']:>10}  {payload['probe']['notes'][source['source_id']]}")
    lines.append(f"duplicates_merged={payload['probe']['notes']['duplicates_merged']}")
    return "\n".join(lines)


def main(argv=None, *, client=None, sleep=time.sleep) -> int:
    parser = argparse.ArgumentParser(description="Probe all V0 sources once; never writes a Sheet.")
    parser.add_argument("--config", default="sources/v0_sources.yaml")
    parser.add_argument("--output", required=True, help="New artifact path outside the checkout")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    args = parser.parse_args(argv)
    owned = client is None
    client = client or httpx.Client()
    try:
        registry = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        payload = run(registry, client, delay=args.delay, sleep=sleep)
        print(summary(payload))
        failed = sum(s["status"] in {"failed", "blocked"} for s in payload["sources"])
        digest = write_artifact(args.output, payload)
        print(f"sources={len(payload['sources'])} delivered_jobs={len(payload['jobs'])} failed_or_blocked={failed}")
        print(f"probe_sha256={digest}")
        return 0
    except (ValueError, TypeError, KeyError, OSError, yaml.YAMLError) as exc:
        print(f"probe_failed: {safe_error_code(exc)}")
        return 2
    finally:
        if owned:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
