"""Message-scoped Gmail intake boundary; no Gmail mutations or raw-email artifacts.

The caller supplies the existing Claude cloud connector adapter and a fact
extractor. This module does not authenticate Gmail or replace that connector.
Adapter methods must return message metadata and individual message bodies only,
never expand a matching thread. A real adapter binding remains a cloud integration
step; synthetic tests do not prove the connector's concrete payload shape.
"""
from email.utils import getaddresses, parseaddr
import hashlib
import re

from bs4 import BeautifulSoup

from jobhunter.postings import Posting, clean_html, collection_match, collection_priority
from jobhunter.job_identity import canonical_key, verified_requisition
from jobhunter.records import https_url

SECURITY_SUBJECT = re.compile(r'\b(?:security|verification|verify|password|reset|login|log[- ]?in|'
                              r'sign[- ]?in|one[- ]time|authentication|code|2fa|two[- ]factor)\b', re.I)
SECURITY_BODY = re.compile(r'\b(?:verification code|reset (?:your )?password|password reset|'
                           r'one[- ]time (?:code|password)|security (?:alert|notice)|confirm your (?:account|identity))\b', re.I)
FACT_FIELDS = frozenset({'title', 'company', 'location', 'salary', 'description_quote', 'apply_url'})


def _job_blocks(body):
    """Only isolated visible job cards with one application link are supported.

    Unknown email layouts stay unsupported until a real adapter's layout is
    verified. A whole-message fallback would allow cross-job fact mixing.
    """
    soup = BeautifulSoup(body, 'html.parser')
    for node in list(soup.find_all()):
        if node.attrs is None:
            continue
        style = re.sub(r'\s+', '', str(node.get('style', ''))).lower()
        if (node.name in {'script', 'style', 'template', 'noscript', 'footer'}
                or node.has_attr('hidden') or node.get('aria-hidden') == 'true'
                or 'display:none' in style or 'visibility:hidden' in style):
            node.decompose()
    blocks = []
    for node in soup.find_all(['article', 'li', 'tr']):
        if node.find(['article', 'li', 'tr']):
            continue
        links = {anchor.get('href') for anchor in node.find_all('a', href=True)
                 if https_url(anchor.get('href'))}
        if len(links) == 1:
            blocks.append((str(node), links))
    return blocks


def _eligible_metadata(message, label_id, recipient, rules):
    if not isinstance(message, dict) or label_id not in message.get('label_ids', []):
        return False
    if not isinstance(message.get('message_id'), str) or not message['message_id'].strip():
        return False
    sender = parseaddr(message.get('from', ''))[1].casefold()
    recipients = {address.casefold() for _, address in getaddresses([message.get('to', '')])}
    subject = message.get('subject', '')
    return bool(recipient.casefold() in recipients and not SECURITY_SUBJECT.search(subject)
                and any(sender == rule['sender'].casefold()
                        and re.fullmatch(rule['subject_pattern'], subject) for rule in rules))


def _posting(fact, body, links, captured_at):
    if not isinstance(fact, dict) or set(fact) != FACT_FIELDS:
        raise ValueError('invalid_gmail_facts')
    text = clean_html(body)
    for field, value in fact.items():
        if (not isinstance(value, str) or len(value) > (300 if field == 'description_quote' else 1000)
                or (not value.strip() and field not in {'location', 'salary'})
                or (value and value not in text and not (field == 'apply_url' and value in links))):
            raise ValueError('unsupported_gmail_fact')
    if not https_url(fact['apply_url']) or fact['apply_url'] not in links:
        raise ValueError('invalid_gmail_link')
    # IDs and source attribution come from code; Claude cannot select Sheet rows.
    key = canonical_key(fact['apply_url'])
    # Stable across daily alerts. Generic URLs retain company/title context;
    # known canonical links preserve the requisition embedded in the path/query.
    known_requisition = verified_requisition(key) or bool(
        re.fullmatch(r'https://www\.linkedin\.com/jobs/view/[0-9]+', key))
    identity_key = key if known_requisition else key + '\0' + fact['company'].casefold() + '\0' + fact['title'].casefold()
    identity = hashlib.sha256(identity_key.encode()).hexdigest()[:32]
    apply_url = key if key.startswith('https://www.linkedin.com/jobs/view/') else fact['apply_url']
    return Posting('gmail:' + identity, 'gmail-job-alerts', fact['company'], fact['title'],
                   fact['location'], fact['description_quote'], apply_url, captured_at,
                   salary=fact['salary'])


def collect_alerts(connector, extractor, *, dedicated_recipient, rules, captured_at):
    """Read at most one bounded label page, validate source facts, and return candidates.

    Rules are supplied only after verifying exact job-alert sender/subject examples
    during setup; no guessed provider allowlist and no account-wide search fallback.
    The adapter and extractor must not log payloads, exceptions or mailbox metadata.
    """
    if not rules or any(set(rule) != {'sender', 'subject_pattern'} for rule in rules):
        raise ValueError('gmail_rules_required')
    for rule in rules:
        if not rule['sender'] or not rule['subject_pattern']:
            raise ValueError('gmail_rules_required')
        re.compile(rule['subject_pattern'])
    if not dedicated_recipient or parseaddr(dedicated_recipient)[1] != dedicated_recipient:
        raise ValueError('gmail_recipient_required')
    source = {'source_id': 'gmail-job-alerts', 'status': 'needs setup', 'captured_at': captured_at,
              'jobs_fetched': 0, 'valid_jobs': 0, 'rejected_items': 0, 'pm_candidates': 0,
              'selected_for_m0': 0, 'attempts': 0, 'http_status': None, 'retry_after_seconds': None,
              'coverage': 'partial-response', 'error': ''}
    output = {'source': source, 'postings': []}
    try:
        labels = connector.list_labels()
        matches = [label['id'] for label in labels if label.get('name') == 'JobHunter']
        if len(matches) != 1:
            return output
        label_id = matches[0]
        source['attempts'] = 1
        messages = connector.list_message_metadata(label_id=label_id, limit=50)
        source['status'] = 'OK-zero-jobs'
        seen, posting_ids, extractions = set(), set(), 0
        for message in messages[:50]:
            if not _eligible_metadata(message, label_id, dedicated_recipient, rules):
                source['rejected_items'] += 1
                continue
            message_id = message['message_id']
            if message_id in seen:
                continue
            seen.add(message_id)
            body = connector.read_message(message_id)
            source['jobs_fetched'] += 1
            if SECURITY_BODY.search(clean_html(body)):
                source['rejected_items'] += 1
                continue
            blocks = _job_blocks(body)
            if not blocks:
                source['status'], source['error'] = 'failed', 'gmail_layout_unverified'
                continue
            for block, links in blocks:
                if extractions >= 150:
                    break  # bounded partial coverage, never a complete-mailbox claim
                extractions += 1
                try:
                    facts = extractor(block)
                    if (not isinstance(facts, list) or len(facts) > 150
                            or any(fact != facts[0] for fact in facts[1:])):
                        raise ValueError('invalid_gmail_facts')
                    facts = facts[:1]
                except Exception:
                    source['status'], source['error'] = 'failed', 'gmail_extraction_failed'
                    continue
                for fact in facts:
                    try:
                        posting = _posting(fact, block, links, captured_at)
                    except (ValueError, TypeError, AttributeError):
                        source['rejected_items'] += 1
                        continue
                    if posting.job_id in posting_ids:
                        continue
                    posting_ids.add(posting.job_id)
                    source['valid_jobs'] += 1
                    if collection_match(posting):
                        source['pm_candidates'] += 1
                        output['postings'].append(posting)
        if source['status'] != 'failed':
            source['status'] = 'OK' if output['postings'] else 'OK-zero-jobs'
    except Exception:
        source['status'], source['error'] = 'failed', 'gmail_connector_failed'
    finally:
        # Also reconcile successful earlier messages after a later connector error.
        output['postings'] = sorted(output['postings'], key=collection_priority)[:8]
        source['selected_for_m0'] = len(output['postings'])
    return output
