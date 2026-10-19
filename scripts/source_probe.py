"""Probe every V0 source once and build one combined delivery artifact; no Sheet writes.

Run with `uv run --locked python -m scripts.source_probe --output <new file outside checkout>`.
One bounded GET per source, no retries, no login, no social access, no secrets.
Keys, accounts and mailboxes that are not
set up are recorded `needs setup` without any request. Keyed APIs (JSearch, Jooble) get exactly one
request each and their keys are never recorded, printed or put in an error. The artifact is delivered
separately with `scripts.sheets_sync`.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import time
import re
from urllib.parse import quote

import httpx
import yaml

from jobhunter.artifacts import SYNC_MAX_BYTES, read_artifact, safe_error_code, write_artifact
from jobhunter.post_facts import SOCIAL, postings_from_result
from jobhunter.postings import (AI_TERMS, DETAIL_SOURCES, LISTING_ONLY, PARSERS, Posting, collection_match,
                                collection_stub_match, collection_priority, collection_title_priority,
                                dedupe, parse_posted, role_family, to_row, within_lookback)

USER_AGENT = "JobHunterBot/0.1 (personal job search; polite single requests)"
MAX_BYTES = 40 * 1024 * 1024
# Safety stop, not a target: at most this many job pages are opened per detail source per run (one polite request
# each). Candidates beyond it are reported as details_skipped so a large source is visible, never silently cut.
DETAIL_SAFETY_STOP = 300
# Safety stop on extra pages fetched from one paged public API per run (reported in the source note).
PAGE_SAFETY_STOP = 100
PAGED_KINDS = {"themuse", "jobicy"}
LOOKBACK_DAYS = 28  # first-run backfill and the default daily window; repeats are harmless (upsert by Job ID)
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


def jsearch_date_posted(days):
    """JSearch accepts only today, 3days, week, month: use the smallest bucket that covers the window."""
    return "today" if days <= 1 else "3days" if days <= 3 else "week" if days <= 7 else "month"


def keyed_request(entry, environ, lookback_days=None):
    """(missing env names, request kwargs). The kwargs hold the secret; never record or print them."""
    values = {name: (environ.get(name) or "").strip() for name in entry["env"]}
    missing = [name for name, value in values.items() if not value]
    if missing:
        return missing, None
    base = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if entry["kind"] == "jsearch":
        params = dict(entry["params"])
        if lookback_days is not None:
            params["date_posted"] = jsearch_date_posted(lookback_days)
        return [], {"method": "GET", "url": entry["url"], "params": params,
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


def page_through(client, kind, url, first, cutoff, *, delay, sleep, page_stop):
    """(merged data, pages fetched, stop reason) for the public APIs that page.

    The Muse numbers pages from 0 and is not date ordered, so every page up to page_count is read. Jobicy is
    newest first and pages by an opaque cursor, so paging stops once a page reaches the window edge. A failed
    later page keeps what was already read and says why it stopped; it never fails the whole source.
    """
    pages, reason = 1, ""
    if kind == "themuse":
        total, key = first.get("page_count"), "results"
        wanted = min(total, page_stop) if type(total) is int and total > 0 else 1
        if type(total) is int and total > page_stop:
            reason = "page_safety_stop"
        for number in range(1, wanted):
            sleep(delay)
            status, body, error = fetch_once(client, re.sub(r"page=\d+", f"page={number}", url))
            if error or status != 200:
                return first, pages, error or f"http_{status}"
            try:
                more = json.loads(body)[key]
                if not isinstance(more, list) or not isinstance(first[key], list):
                    raise ValueError("invalid_page")
                first[key].extend(more)
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                return first, pages, "invalid_json"
            pages += 1
        return first, pages, reason
    # Jobicy
    while first.get("hasMore") is True and pages < page_stop:
        cursor = first.get("nextCursor")
        if not isinstance(cursor, str) or not re.fullmatch(r"[A-Za-z0-9_=+/-]{1,500}", cursor):
            return first, pages, "invalid_cursor"
        jobs = first.get("jobs")
        if not isinstance(jobs, list):
            return first, pages, "invalid_page"
        newest_stub = jobs[-1] if jobs else None  # a malformed item is the parser's to quarantine, not ours to trip on
        last = newest_stub.get("pubDate") if isinstance(newest_stub, dict) else None
        if cutoff is not None and parse_posted(last) and datetime.fromisoformat(parse_posted(last)) < cutoff:
            return first, pages, ""  # the window edge is behind us
        sleep(delay)
        status, body, error = fetch_once(client, f"{url}&cursor={quote(cursor, safe='')}")
        if error or status != 200:
            return first, pages, error or f"http_{status}"
        try:
            more = json.loads(body)
            if not isinstance(more["jobs"], list):
                raise ValueError("invalid_page")
            first["jobs"].extend(more["jobs"])
            first["hasMore"], first["nextCursor"] = more.get("hasMore"), more.get("nextCursor")
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            return first, pages, "invalid_json"
        pages += 1
    return first, pages, "page_safety_stop" if first.get("hasMore") is True else ""


def fetch_details(client, entry, stubs, stamp, *, delay, sleep):
    """Fetch shortlisted job pages and retain per-source response evidence."""
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
                break
            if problem is None:
                problem = ('failed', error or f'http_{status}', status)
            continue
        try:
            found = detail(body)
            postings.append(Posting(stub["job_id"], entry["id"], found.get("company") or stub["company"], stub["title"],
                                    found.get("location") or stub["location"], found["text"], stub["url"], stamp,
                                    salary=found.get("salary") or stub["salary"], tag="other",
                                    posted_at=found.get("posted_at") or stub.get("posted_at", "")))
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            rejected += 1
    return postings, rejected, problem, attempts


def probe_source(client, entry, stamp, *, delay=0, sleep=time.sleep, environ=None, lookback_days=None,
                 detail_stop=None, page_stop=None, known_ids=frozenset()):
    """Returns (source record or None for an unresponsive candidate, postings, note).

    lookback_days keeps postings whose source date is inside the window; a posting with no usable date is
    kept and counted as date_unknown, never dropped on missing data. None disables the window.
    """
    kind, source_id = entry["kind"], entry["id"]
    url = entry["url"]
    if kind in KEYED_KINDS:
        missing, request = keyed_request(entry, os.environ if environ is None else environ, lookback_days)
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
    problem, attempts, detail_skipped, outside, delivered_before = None, 1, 0, 0, []
    cutoff = None if lookback_days is None else datetime.fromisoformat(stamp) - timedelta(days=lookback_days)
    paging_note = ''
    if kind in PAGED_KINDS and isinstance(data, dict):
        try:
            data, pages, stopped = page_through(client, kind, url, data, cutoff, delay=delay, sleep=sleep,
                                                page_stop=PAGE_SAFETY_STOP if page_stop is None else page_stop)
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            pages, stopped = 1, "invalid_page"  # contained per source; what was read so far is kept
        attempts += pages - 1
        paging_note = f'; pages_fetched={pages}' + (f'; paging_stopped={stopped}' if stopped else '')
        if stopped not in ("", "page_safety_stop"):
            # A real later-page failure is durable evidence in Sources and Run Log, not only a probe note.
            # Jobs from the pages already read are still delivered (a failed source may carry partial jobs).
            code = stopped if re.fullmatch(r"http_[1-5][0-9]{2}|timeout|transport_error|invalid_json", stopped) \
                else "invalid_board_response"
            http = int(code[5:]) if code.startswith("http_") else None
            attempts += stopped not in ("invalid_cursor", "invalid_page")  # the failed request was an attempt too
            problem = ("blocked" if http in BLOCKED else "failed", code, http if http is not None else 200)
    try:
        if kind in LISTING_ONLY:
            counts = LISTING_ONLY[kind](data, ctx)
            return record(source_id, "OK-zero-jobs", stamp, http=200, listed=counts["listed"],
                          valid=counts["listed"], rejected=0, candidates=counts["pm_titles"],
                          coverage="partial-response"), [], "listing_only"
        if kind in DETAIL_SOURCES:
            stubs, rejected = DETAIL_SOURCES[kind][0](data, {**ctx, "url": url})
            shortlist = [s for s in stubs if collection_stub_match(s["title"], s["location"], s["salary"])]
            delivered_before = [s for s in shortlist if s["job_id"] in known_ids]  # already in the Sheet: skip the page
            shortlist = [s for s in shortlist if s["job_id"] not in known_ids]
            # No listing-date prefilter: listing dates are unverified, and a wrong one would silently drop a job.
            # The window is applied after each page's own posting date is read.
            shortlist.sort(key=lambda stub: collection_title_priority(stub['title'], entry.get('tag', 'other')))
            stop = DETAIL_SAFETY_STOP if detail_stop is None else detail_stop
            detail_skipped = max(0, len(shortlist) - stop)
            if detail_skipped:
                # Jobs inspected but not delivered (outside the window, rejected) are never in the Sheet, so
                # skipping delivered IDs alone cannot move past them. Start each day's window where the last
                # one ended: the whole shortlist is reached within ceil(N / stop) days, with no stored cursor.
                start = (datetime.fromisoformat(stamp).date().toordinal() * stop) % len(shortlist)
                shortlist = shortlist[start:] + shortlist[:start]
            postings, failed, problem, detail_attempts = fetch_details(
                client, entry, shortlist[:stop], stamp, delay=delay, sleep=sleep)
            attempts += detail_attempts
            rejected += failed
            total = len(stubs)
        else:
            postings, rejected, total = PARSERS[kind](data, ctx)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        code = "duplicate_source_id" if str(exc) == "duplicate_source_id" else "invalid_board_response"
        return record(source_id, "failed", stamp, error=code, http=200), [], code
    if cutoff is not None:
        inside = [p for p in postings if within_lookback(p, datetime.fromisoformat(stamp), lookback_days)]
        outside += len(postings) - len(inside)
        postings = inside
    undated = sum(not p.posted_at for p in postings)
    candidates = [p for p in postings if role_family(p.title)]
    selected = sorted((p for p in postings if collection_match(p)), key=collection_priority)
    # A paged source is complete only when every page it offered (or every page inside the window) was read.
    coverage = ("complete-response" if entry.get("board") or (paging_note and "paging_stopped" not in paging_note)
                else "partial-response")
    if kind in DETAIL_SOURCES:
        candidates = shortlist
    if rejected:
        coverage += "-with-rejections"
    skipped_note = ((f'; details_skipped={detail_skipped}' if detail_skipped else '') + paging_note
                    + (f'; already_delivered={len(delivered_before)}' if kind in DETAIL_SOURCES and known_ids else ''))
    if cutoff is not None:
        skipped_note += f'; outside_window={outside}; date_unknown={undated}'
    if problem is not None:
        status, error, http = problem
        return record(source_id, status, stamp, error=error, http=http, listed=total,
                      valid=len(postings), rejected=rejected, candidates=len(candidates),
                      selected=len(selected), coverage=coverage, attempts=attempts), selected, error + skipped_note
    # Jobs skipped because they are already in the Sheet prove the listing was readable, so a stray malformed
    # stub beside them is not an invalid source (found by the first real pull: getro-accel).
    if not postings and rejected and not delivered_before:
        return record(source_id, "failed", stamp, error="invalid_items_quarantined", http=200, listed=total,
                      valid=0, rejected=rejected, candidates=0, coverage=coverage), [], "invalid_items" + skipped_note
    status = "OK" if selected else "OK-zero-jobs"
    return record(source_id, status, stamp, http=200, listed=total, valid=len(postings), rejected=rejected,
                  candidates=len(candidates), selected=len(selected), coverage=coverage, attempts=attempts), selected, "ok" + skipped_note


def fair_order(items):
    """Round-robin (posting, note) pairs by source, keeping each source's own order.

    Delivery is split into recoverable writer batches in registry order. Interleaving the sources means
    a run that stops partway has still delivered every source's best jobs, not just the first sources'.
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


def run(registry, client, *, delay=1.0, sleep=time.sleep, environ=None, gmail_result=None, hn_result=None, ai_results=(),
        now=lambda: datetime.now(timezone.utc).isoformat(), lookback_days=LOOKBACK_DAYS, detail_stop=None,
        page_stop=None, known_ids=frozenset()):
    environ = os.environ if environ is None else environ
    stamp = now()
    sources, jobs, notes = [], [], {}
    results = ([hn_result] if hn_result is not None else []) + list(ai_results)
    replaced = {r['source']['source_id'] for r in results}
    replaced |= {SOCIAL[i]['registry_id'] for i in replaced if i in SOCIAL}
    for entry in entries(registry):
        if entry['id'] in replaced:
            continue  # a validated AI extraction replaces the listing-only count or the needs-setup placeholder
        record_, selected, note = probe_source(client, entry, stamp, delay=delay, sleep=sleep,
                                                    environ=environ, lookback_days=lookback_days, detail_stop=detail_stop,
                                                    page_stop=page_stop, known_ids=known_ids)
        notes[entry["id"]] = note
        if record_ is not None:
            sources.append(record_)
            jobs.extend(selected)
        sleep(delay)
    for result in results:
        sources.append(result['source'])
        jobs.extend(result['postings'])
        notes[result['source']['source_id']] = result['source']['error'] or 'posts-in-window'
    if gmail_result is not None:
        sources.append(gmail_result['source'])
        jobs.extend(gmail_result['postings'])
        notes['gmail-job-alerts'] = gmail_result['source']['error'] or 'bounded-message-page'
    for item in registry["needs_setup"]:
        if (item['id'] == 'gmail-job-alerts' and gmail_result is not None) or item['id'] in replaced:
            continue
        missing = [name for name in item["env"] if not environ.get(name)]
        sources.append(record(item["id"], "needs setup", stamp, attempts=0))
        notes[item["id"]] = ("keys_missing:" + ",".join(missing) if missing else "setup_or_collector_pending")
    unique = dedupe(jobs)
    duplicates = len(jobs) - len(unique)
    unique = fair_order(unique)  # share each writer batch fairly across sources
    rows = [to_row(posting, note) for posting, note in unique]
    kept = {}
    for posting, _ in unique:
        kept[posting.source_id] = kept.get(posting.source_id, 0) + 1
    notes["duplicates_merged"] = duplicates
    for source in sources:  # a merged source must report what was actually delivered
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
    parser.add_argument("--lookback-days", type=int, default=LOOKBACK_DAYS,
                        help="keep postings dated inside this many days (first run = backfill); undated are kept")
    parser.add_argument("--detail-safety-stop", type=int, default=DETAIL_SAFETY_STOP,
                        help="job pages opened per detail source (a guard, reported as details_skipped); "
                             "raise it for the one-off first pull")
    parser.add_argument("--page-safety-stop", type=int, default=PAGE_SAFETY_STOP,
                        help="pages fetched from one paged public API (The Muse, Jobicy); a guard reported in the note")
    parser.add_argument("--known-ids", help="Job IDs already in the Sheet (scripts.known_ids); detail sources skip them")
    parser.add_argument("--known-ids-sha256", help="digest printed when that file was written")
    parser.add_argument("--social-result", action="append", default=[],
                        help="validated X or LinkedIn result from scripts.social_posts validate (repeatable)")
    parser.add_argument("--social-result-sha256", action="append", default=[],
                        help="digest printed for each --social-result, in the same order")
    parser.add_argument("--hn-result", help="validated Hacker News result from scripts.hn_hiring validate")
    parser.add_argument("--hn-result-sha256", help="digest printed when that result was written")
    args = parser.parse_args(argv)
    owned = client is None
    client = client or httpx.Client()
    try:
        registry = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        if not 1 <= args.lookback_days <= 365:
            raise ValueError('invalid_lookback_days')
        if not 1 <= args.page_safety_stop <= 1000:
            raise ValueError('invalid_safety_stop')
        if not 1 <= args.detail_safety_stop <= 100000:
            raise ValueError('invalid_safety_stop')
        print(f'limits: lookback_days={args.lookback_days} detail_safety_stop={args.detail_safety_stop} '
              f'page_safety_stop={args.page_safety_stop} delay={args.delay}')
        known = frozenset()
        if args.known_ids:
            listed = read_artifact(args.known_ids, expected_sha256=args.known_ids_sha256)
            if (not isinstance(listed, dict) or not isinstance(listed.get('job_ids'), list)
                    or any(not isinstance(i, str) for i in listed['job_ids'])):
                raise ValueError('invalid_known_ids')
            known = frozenset(listed['job_ids'])
        hn_result = None
        if args.hn_result:
            source, found = postings_from_result(read_artifact(args.hn_result, expected_sha256=args.hn_result_sha256))
            hn_result = {'source': source, 'postings': found}
        if len(args.social_result) != len(args.social_result_sha256):
            raise ValueError('invalid_ai_result')
        ai_results = []
        for path, digest in zip(args.social_result, args.social_result_sha256):
            source, found = postings_from_result(read_artifact(path, expected_sha256=digest))
            ai_results.append({'source': source, 'postings': found})
        payload = run(registry, client, delay=args.delay, sleep=sleep, lookback_days=args.lookback_days,
                      hn_result=hn_result, ai_results=ai_results, detail_stop=args.detail_safety_stop, page_stop=args.page_safety_stop, known_ids=known)
        print(summary(payload))
        failed = sum(s["status"] in {"failed", "blocked"} for s in payload["sources"])
        digest = write_artifact(args.output, payload, max_bytes=SYNC_MAX_BYTES)
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
