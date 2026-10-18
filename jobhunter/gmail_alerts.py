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

from jobhunter.postings import Posting, clean_html, collection_match
from jobhunter.records import https_url

SECURITY_SUBJECT = re.compile(r'\b(?:security|verification|verify|password|reset|login|log[- ]?in|'
                              r'sign[- ]?in|one[- ]time|authentication|code|2fa|two[- ]factor)\b', re.I)
SECURITY_BODY = re.compile(r'\b(?:verification code|reset (?:your )?password|password reset|'
                           r'one[- ]time (?:code|password)|security (?:alert|notice)|confirm your (?:account|identity))\b', re.I)
FACT_FIELDS = frozenset({'title', 'company', 'location', 'salary', 'description_quote', 'apply_url'})


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


def _posting(fact, body, message_id, captured_at):
    if not isinstance(fact, dict) or set(fact) != FACT_FIELDS:
        raise ValueError('invalid_gmail_facts')
    text = clean_html(body)
    for field, value in fact.items():
        if (not isinstance(value, str) or len(value) > (300 if field == 'description_quote' else 1000)
                or (not value.strip() and field not in {'location', 'salary'})
                or (value and value not in text and not (field == 'apply_url' and value in body))):
            raise ValueError('unsupported_gmail_fact')
    if not https_url(fact['apply_url']):
        raise ValueError('invalid_gmail_link')
    # IDs and source attribution come from code; Claude cannot select Sheet rows.
    identity = hashlib.sha256((message_id + '\0' + fact['apply_url']).encode()).hexdigest()[:32]
    return Posting('gmail:' + identity, 'gmail-job-alerts', fact['company'], fact['title'],
                   fact['location'], fact['description_quote'], fact['apply_url'], captured_at,
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
        seen, posting_ids = set(), set()
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
            try:
                facts = extractor(body)
                if not isinstance(facts, list) or len(facts) > 150:
                    raise ValueError('invalid_gmail_facts')
            except Exception:
                source['status'], source['error'] = 'failed', 'gmail_extraction_failed'
                continue
            for fact in facts:
                try:
                    posting = _posting(fact, body, message_id, captured_at)
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
        # Current source cap is unchanged. Never silently claim complete coverage.
        output['postings'] = output['postings'][:8]
        source['selected_for_m0'] = len(output['postings'])
        if source['status'] != 'failed':
            source['status'] = 'OK' if output['postings'] else 'OK-zero-jobs'
    except Exception:
        source['status'], source['error'] = 'failed', 'gmail_connector_failed'
    return output
