"""Synthetic messages only: Gmail intake must never widen to unrelated mail."""
from dataclasses import replace

import pytest

from jobhunter import gmail_alerts as g


BODY = ('<article><p>Acme</p><p>Product Manager</p><p>Remote - Colombia</p>'
        '<p>USD 80,000 annually</p><p>Build billing products.</p>'
        '<a href="https://jobs.lever.co/acme/1">Apply</a></article>')
FACTS = [{'title': 'Product Manager', 'company': 'Acme', 'location': 'Remote - Colombia',
          'salary': 'USD 80,000 annually', 'description_quote': 'Build billing products.',
          'apply_url': 'https://jobs.lever.co/acme/1'}]
RULE = {'sender': 'jobs@alerts.example', 'subject_pattern': r'^Your daily job alert$'}
META = {'message_id': 'synthetic1', 'label_ids': ['label1'], 'from': 'Jobs <jobs@alerts.example>',
        'to': 'dedicated@example.test', 'subject': 'Your daily job alert'}


class Mailbox:
    def __init__(self, *, labels=None, messages=None, body=BODY):
        self.labels = [{'name': 'JobHunter', 'id': 'label1'}] if labels is None else labels
        self.messages = [META] if messages is None else messages
        self.body = body
        self.reads = []
        self.searches = []

    def list_labels(self):
        return self.labels

    def list_message_metadata(self, *, label_id, limit):
        self.searches.append((label_id, limit))
        return self.messages

    def read_message(self, message_id):
        self.reads.append(message_id)
        return self.body


def collect(mailbox, extractor=lambda body: FACTS):
    return g.collect_alerts(mailbox, extractor, dedicated_recipient='dedicated@example.test',
                            rules=[RULE], captured_at='2026-10-18T00:00:00+00:00')


def test_missing_label_stops_before_search_or_body_reads():
    mailbox = Mailbox(labels=[{'name': 'Other', 'id': 'label2'}])
    result = collect(mailbox)
    assert result['source']['status'] == 'needs setup'
    assert not mailbox.searches and not mailbox.reads and not result['postings']


def test_empty_label_stops_without_inbox_fallback():
    mailbox = Mailbox(messages=[])
    result = collect(mailbox)
    assert result['source']['status'] == 'OK-zero-jobs'
    assert mailbox.searches == [('label1', 50)] and not mailbox.reads


@pytest.mark.parametrize('change', [
    {'label_ids': ['unrelated']}, {'from': 'jobs@evil.example'}, {'to': 'main@example.test'},
    {'subject': 'Your daily job alert password reset'}, {'subject': 'Login verification code'},
    {'subject': 'Your daily job alert security notice'}, {'subject': 'Other newsletter'},
])
def test_unlabeled_unforwarded_unapproved_and_security_metadata_never_fetch_bodies(change):
    mailbox = Mailbox(messages=[META | change])
    result = collect(mailbox)
    assert not mailbox.reads and not result['postings']
    assert result['source']['rejected_items'] == 1


def test_only_exact_message_ids_are_read_and_raw_email_is_not_returned():
    mailbox = Mailbox(messages=[META, META | {'message_id': 'unrelated', 'label_ids': []}])
    result = collect(mailbox)
    assert mailbox.reads == ['synthetic1']
    assert len(result['postings']) == 1
    posting = result['postings'][0]
    assert posting.source_id == 'gmail-job-alerts' and posting.title == 'Product Manager'
    assert posting.salary == 'USD 80,000 annually'
    assert posting.text == 'Build billing products.' and posting.remote is False
    assert BODY not in repr(result) and 'synthetic1' not in posting.job_id


@pytest.mark.parametrize('field,value', [('salary', 'USD 150,000 annually'), ('location', 'United States'),
    ('title', 'Chief of Staff'), ('company', 'Invented'), ('apply_url', 'https://evil.example/apply'),
    ('description_quote', 'Invented description')])
def test_model_facts_must_be_exact_message_evidence(field, value):
    result = collect(Mailbox(), lambda body: [FACTS[0] | {field: value}])
    assert result['postings'] == [] and result['source']['rejected_items'] == 1


def test_unknown_salary_stays_unresolved_and_below_floor_is_filtered():
    for salary, count in [('', 1), ('USD 60,000 annually', 0)]:
        mailbox = Mailbox(body=BODY.replace('USD 80,000 annually', salary))
        result = collect(mailbox, lambda body: [FACTS[0] | {'salary': salary}])
        assert len(result['postings']) == count


def test_connector_and_extractor_errors_keep_only_safe_diagnostics():
    def fail(body):
        raise RuntimeError('secret raw message')
    result = collect(Mailbox(), fail)
    assert result['source']['status'] == 'failed'
    assert result['source']['error'] == 'gmail_extraction_failed' and 'secret' not in repr(result)


def test_partial_metadata_page_is_reported_and_never_claims_complete_mailbox():
    result = collect(Mailbox())
    assert result['source']['coverage'] == 'partial-response'


def test_missing_sender_rules_never_reads_mail():
    mailbox = Mailbox()
    with pytest.raises(ValueError, match='gmail_rules_required'):
        g.collect_alerts(mailbox, lambda body: FACTS, dedicated_recipient='dedicated@example.test',
                         rules=[], captured_at='2026-10-18T00:00:00+00:00')
    assert not mailbox.searches and not mailbox.reads


def test_validated_gmail_results_join_probe_and_writer_preserves_user_fields():
    from scripts import source_probe, sheets_sync
    from jobhunter.artifacts import write_artifact
    from sheet_fakes import MemoryStore
    import tempfile
    from pathlib import Path
    import httpx
    result = collect(Mailbox())
    registry = {'boards': {}, 'needs_setup': [{'id': 'gmail-job-alerts', 'env': [], 'action': 'route'}]}
    with httpx.Client() as client:
        payload = source_probe.run(registry, client, delay=0, gmail_result=result,
                                   now=lambda: '2026-10-18T00:00:00+00:00')
    assert len(payload['jobs']) == len(payload['sources']) == 1
    assert payload['sources'][0]['status'] == 'OK'
    with tempfile.TemporaryDirectory() as directory:
        artifact = Path(directory) / 'normalized.json'
        write_artifact(artifact, payload)
        store = MemoryStore()
        assert sheets_sync.main(['--input', str(artifact), '--run-id', 'gmail-test1'], store=store) == 0
        headers, row = store.tables['Jobs'][:2]
        for field, value in [('Status', 'Applied'), ('Notes', 'Keep my note'), ('My rating', '5')]:
            row[headers.index(field)] = value
        assert sheets_sync.main(['--input', str(artifact), '--run-id', 'gmail-test2'], store=store) == 0
        assert len(store.tables['Jobs']) == 2
        assert [store.tables['Jobs'][1][headers.index(field)] for field in ['Status', 'Notes', 'My rating']] == [
            'Applied', 'Keep my note', '5']


def test_duplicate_extractions_cannot_duplicate_one_message_requisition():
    result = collect(Mailbox(), lambda body: FACTS + FACTS)
    assert len(result['postings']) == 1 and result['source']['selected_for_m0'] == 1


def test_security_body_is_not_extracted_even_with_job_like_subject():
    called = []
    result = collect(Mailbox(body='Use this verification code to sign in.'),
                     lambda body: called.append(True) or FACTS)
    assert not called and not result['postings']


def test_repeated_daily_alerts_have_stable_identity_despite_linkedin_tracking():
    urls = ['https://www.linkedin.com/jobs/view/12345/?refId=day1&midToken=secret1',
            'https://www.linkedin.com/comm/jobs/view/12345/?refId=day2&midToken=secret2&lipi=mail']
    postings = []
    for index, url in enumerate(urls):
        body = BODY.replace(FACTS[0]['apply_url'], url)
        mailbox = Mailbox(messages=[META | {'message_id':f'daily{index}'}], body=body)
        result = collect(mailbox, lambda text: [FACTS[0] | {'apply_url':url}])
        postings.append(result['postings'][0])
    assert postings[0].job_id == postings[1].job_id
    assert postings[0].apply_url == 'https://www.linkedin.com/jobs/view/12345'


def test_verified_linkedin_requisition_identity_survives_title_update():
    url = 'https://www.linkedin.com/jobs/view/12345'
    ids = []
    for title in ['Product Manager', 'Senior Product Manager']:
        body = BODY.replace(FACTS[0]['apply_url'], url).replace('Product Manager', title)
        result = collect(Mailbox(body=body), lambda block: [FACTS[0] | {'title': title, 'apply_url': url}])
        ids.append(result['postings'][0].job_id)
    assert ids[0] == ids[1]


def test_partial_connector_failure_still_caps_postings_and_reports_selected_count():
    class PartialMailbox(Mailbox):
        def read_message(self, message_id):
            if message_id == 'later':
                raise RuntimeError('do not expose mailbox error')
            return '\n\n'.join(BODY.replace('/acme/1',f'/acme/{i}') for i in range(12))
    mailbox = PartialMailbox(messages=[META, META | {'message_id':'later'}])
    def extract(block):
        import re
        url = re.search(r'https://[^"<\s]+', block).group()
        return [FACTS[0] | {'apply_url': url}]
    result = collect(mailbox, extract)
    assert result['source']['status'] == 'failed'
    assert len(result['postings']) == result['source']['selected_for_m0'] == 8


def test_facts_cannot_mix_between_separate_job_cards_or_footer():
    first = '<article><p>Acme Product Manager Remote - Colombia Build billing products.</p><a href="https://jobs.lever.co/acme/1">Apply</a></article>'
    second = '<article><p>Beta Director USD 150,000 annually</p><a href="https://jobs.lever.co/beta/2">Apply</a></article>'
    body = first + second + '<footer>United States</footer>'
    result = collect(Mailbox(body=body), lambda block: [FACTS[0] | {'salary':'USD 150,000 annually'}])
    assert not result['postings']


def test_hidden_apply_link_is_not_valid_evidence():
    body = BODY.replace(FACTS[0]['apply_url'], '') + '<div hidden><a href="https://jobs.lever.co/acme/1">Apply</a></div>'
    assert not collect(Mailbox(body=body))['postings']
