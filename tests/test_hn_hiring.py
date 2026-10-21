"""Hacker News hiring comments: window, candidate filter, fact validation and delivery."""

from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest

from jobhunter import hn_hiring as hn
from jobhunter import postings as p
from scripts import hn_hiring as cli
from scripts import source_probe as probe

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
CAPTURED = NOW.isoformat()


def epoch(days_ago):
    return int((NOW - timedelta(days=days_ago)).timestamp())


def search(*titles_and_days):
    return {'hits': [{'objectID': str(1000 + i), 'title': title, 'created_at_i': epoch(days)}
                     for i, (title, days) in enumerate(titles_and_days)]}


def comment(number, text, days_ago=3):
    return {'id': number, 'created_at_i': epoch(days_ago), 'text': text, 'children': [{'id': number + 1, 'text': 'reply'}]}


def item(story, children):
    return {'id': story, 'children': children}


THREAD = {'story_id': '1000', 'title': 'Ask HN: Who is hiring? (October 2026)', 'created_at': '2026-10-01T00:00:00+00:00'}
PM_TEXT = ('Acme (Remote US) | Senior Product Manager, AI | $170k-$210k<p>We build agents. Apply at '
           '<a href="https:&#x2F;&#x2F;acme.example&#x2F;jobs&#x2F;pm" rel="nofollow">https:&#x2F;&#x2F;acme.example&#x2F;jobs&#x2F;pm</a>')


def test_only_monthly_hiring_threads_inside_the_reach_are_selected():
    data = search(('Ask HN: Who is hiring? (October 2026)', 17), ('Ask HN: Who wants to be hired? (October 2026)', 17),
                  ('Ask HN: Who is hiring? (September 2026)', 47), ('Ask HN: Who is hiring? (June 2026)', 120),
                  ('Ask HN: Freelancer? Seeking freelancer? (October 2026)', 17), ('Show HN: whatever', 1))
    threads = hn.select_threads(data, NOW, 28)
    assert [t['title'] for t in threads] == ['Ask HN: Who is hiring? (October 2026)', 'Ask HN: Who is hiring? (September 2026)']
    with pytest.raises(ValueError):
        hn.select_threads({'oops': 1}, NOW, 28)


def test_candidates_are_top_level_in_window_role_mentions_with_exact_text_and_links():
    cutoff = NOW - timedelta(days=28)
    data = item(1000, [comment(2001, PM_TEXT),
                       comment(2003, 'Beta | Backend Engineer | NYC', 3),                     # no collected role
                       comment(2005, 'Gamma | Product Manager | Remote', 40),                 # outside the window
                       {'id': 2007, 'created_at_i': epoch(2), 'text': None},                  # deleted
                       {'id': 'x', 'created_at_i': epoch(2), 'text': 'Chief of Staff'},       # unreadable id
                       comment(2009, 'Delta | Chief of Staff | Remote US', 5)])
    found, stats = hn.candidate_comments(THREAD, data, cutoff)
    assert [c['comment_id'] for c in found] == ['2001', '2009']
    assert stats == {'top_level': 6, 'in_window': 3, 'role_mentions': 2, 'unreadable': 2}
    assert found[0]['links'] == ['https://acme.example/jobs/pm']
    assert 'Senior Product Manager, AI' in found[0]['text'] and '<' not in found[0]['text']
    assert found[0]['created_at'].endswith('+00:00')


def test_a_response_for_a_different_story_is_rejected():
    with pytest.raises(ValueError):
        hn.candidate_comments(THREAD, item(999, []), NOW)


def candidate():
    found, _ = hn.candidate_comments(THREAD, item(1000, [comment(2001, PM_TEXT)]), NOW - timedelta(days=28))
    return found


def fact(**changes):
    base = {'comment_id': '2001', 'title': 'Senior Product Manager, AI', 'company': 'Acme',
            'location': 'Remote US', 'salary': '$170k-$210k', 'description_quote': 'We build agents.',
            'apply_url': 'https://acme.example/jobs/pm'}
    return base | changes


def result(facts, **kwargs):
    return hn.build_result(candidate(), facts, CAPTURED, listed=1, stats={'unreadable': 0}, threads=[THREAD], **kwargs)


def test_a_verified_fact_becomes_a_posting_with_code_derived_identity_date_and_link():
    out = result([fact()])
    assert out['source']['status'] == 'OK' and out['source']['selected_for_m0'] == 1
    source, postings = hn.postings_from_result(out)
    posting = postings[0]
    assert posting.job_id.startswith('hn:2001:') and posting.source_id == 'hn-who-is-hiring'
    assert posting.apply_url == 'https://acme.example/jobs/pm'
    assert posting.posted_at == candidate()[0]['created_at']
    assert source['coverage'] == 'partial-response'


def test_without_an_application_link_the_comment_permalink_is_the_lead():
    out = result([fact(apply_url='')])
    assert hn.postings_from_result(out)[1][0].apply_url == 'https://news.ycombinator.com/item?id=2001'


@pytest.mark.parametrize('changes', [
    {'title': 'Product Manager, Robots'},              # not in the comment
    {'company': 'Not Acme'},
    {'description_quote': 'x' * 301},
    {'description_quote': 'We build robots.'},
    {'apply_url': 'https://evil.example/jobs/pm'},   # a link the comment does not contain
    {'apply_url': 'http://acme.example/jobs/pm'},
    {'comment_id': '9999'},
    {'location': 5},
    {'salary': '$999k'},
])
def test_unsupported_facts_are_rejected_and_counted_not_delivered(changes):
    out = result([fact(**changes)])
    assert out['postings'] == [] and out['source']['rejected_items'] == 1
    assert out['source']['status'] == 'OK-zero-jobs'


def test_extra_or_missing_fact_fields_and_non_list_payloads_are_rejected():
    assert result([fact() | {'extra': 'x'}])['postings'] == []
    bad = fact()
    del bad['salary']
    assert result([bad])['postings'] == []
    with pytest.raises(ValueError):
        result({'comment_id': '2001'})


def test_two_roles_in_one_comment_get_distinct_ids_and_an_exact_repeat_collapses():
    out = result([fact(), fact(), fact(title='Product Manager')])  # both titles appear in the comment text
    ids = [row['job_id'] for row in out['postings']]
    assert len(ids) == len(set(ids)) == 2
    assert out['source']['valid_jobs'] == 2  # the exact repeat is not counted twice


def test_an_ineligible_location_or_salary_is_not_delivered():
    text = 'Acme (Berlin, Germany) | Product Manager | EUR 80k<p>Come work in Berlin'
    found, _ = hn.candidate_comments(THREAD, item(1000, [comment(2001, text)]), NOW - timedelta(days=28))
    out = hn.build_result(found, [fact(title='Product Manager', location='Berlin, Germany', salary='EUR 80k',
                                       description_quote='Come work in Berlin', apply_url='')],
                          CAPTURED, listed=1, stats={}, threads=[THREAD])
    assert out['postings'] == [] and out['source']['valid_jobs'] == 1 and out['source']['selected_for_m0'] == 0


# ---- CLI and delivery through the shared probe -------------------------------------------------

def hn_client(story_item):
    def serve(request):
        if 'search_by_date' in str(request.url):
            return httpx.Response(200, json=search(('Ask HN: Who is hiring? (October 2026)', 17)))
        return httpx.Response(200, json=story_item)
    return httpx.Client(transport=httpx.MockTransport(serve))


def test_cli_candidates_then_validate_then_probe_delivers_a_row(tmp_path, capsys):
    story = item(1000, [comment(2001, PM_TEXT)])
    candidates = tmp_path.parent / (tmp_path.name + '_cand.json')
    assert cli.main(['candidates', '--output', str(candidates)], client=hn_client(story), sleep=lambda s: None,
                    now=lambda: NOW) == 0
    out = capsys.readouterr().out
    assert 'candidates=1' in out and 'truncated=False' in out
    digest = out.split('candidates_sha256=')[1].split()[0]
    extractions = tmp_path.parent / (tmp_path.name + '_facts.json')
    extractions.write_text(json.dumps({'processed': ['2001'], 'facts': [fact()]}))
    validated = tmp_path.parent / (tmp_path.name + '_hn.json')
    assert cli.main(['validate', '--candidates', str(candidates), '--candidates-sha256', digest,
                     '--extractions', str(extractions), '--output', str(validated)]) == 0
    out = capsys.readouterr().out
    result_digest = out.split('hn_result_sha256=')[1].split()[0]
    assert 'delivered=1' in out
    assert json.loads(validated.read_text())['processed_ids'] == ['2001']
    # the probe replaces the listing-only count with the validated comments
    config = tmp_path / 'registry.yaml'
    import yaml
    config.write_text(yaml.safe_dump({'boards': {}, 'listing_only': [{'id': 'hn-who-is-hiring', 'kind': 'hn',
                                      'url': 'https://hn.test/x'}], 'needs_setup': []}))
    artifact = tmp_path.parent / (tmp_path.name + '_probe.json')
    assert probe.main(['--config', str(config), '--output', str(artifact), '--delay', '0',
                       '--hn-result', str(validated), '--hn-result-sha256', result_digest],
                      client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))),
                      sleep=lambda s: None) == 0
    payload = json.loads(artifact.read_text())
    assert [row['Source'] for row in payload['jobs']] == ['hn-who-is-hiring']
    assert [s['source_id'] for s in payload['sources']] == ['hn-who-is-hiring']  # no duplicate listing-only record
    assert 'Posted: 2026-10-15' in payload['jobs'][0]['More details']


def test_cli_rejects_a_candidates_file_that_does_not_match_its_digest(tmp_path, capsys):
    candidates = tmp_path.parent / (tmp_path.name + '_cand2.json')
    cli.main(['candidates', '--output', str(candidates)], client=hn_client(item(1000, [comment(2001, PM_TEXT)])),
             sleep=lambda s: None, now=lambda: NOW)
    capsys.readouterr()
    extractions = tmp_path.parent / (tmp_path.name + '_facts2.json')
    extractions.write_text(json.dumps({'processed': [], 'facts': []}))
    assert cli.main(['validate', '--candidates', str(candidates), '--candidates-sha256', '0' * 64,
                     '--extractions', str(extractions), '--output', str(tmp_path.parent / 'never.json')]) == 2
    assert 'artifact_digest_mismatch' in capsys.readouterr().out


def test_cli_reports_a_failed_fetch_without_writing_an_artifact(tmp_path, capsys):
    out = tmp_path.parent / (tmp_path.name + '_none.json')
    failing = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    assert cli.main(['candidates', '--output', str(out)], client=failing, sleep=lambda s: None, now=lambda: NOW) == 2
    assert 'hn_failed: http_404' in capsys.readouterr().out and not out.exists()


def test_candidate_safety_stop_is_reported_as_truncated(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, 'CANDIDATE_SAFETY_STOP', 2)
    story = item(1000, [comment(2001 + 2 * i, f'Co{i} | Product Manager | Remote US') for i in range(5)])
    out = tmp_path.parent / (tmp_path.name + '_trunc.json')
    assert cli.main(['candidates', '--output', str(out)], client=hn_client(story), sleep=lambda s: None,
                    now=lambda: NOW) == 0
    assert 'candidates=2' in capsys.readouterr().out and json.loads(out.read_text())['truncated'] is True


def validate_with(tmp_path, capsys, extractions):
    story = item(1000, [comment(2001, PM_TEXT), comment(2003, 'Delta | Chief of Staff | Remote US', 5)])
    candidates = tmp_path.parent / (tmp_path.name + '_c.json')
    cli.main(['candidates', '--output', str(candidates)], client=hn_client(story), sleep=lambda s: None, now=lambda: NOW)
    digest = capsys.readouterr().out.split('candidates_sha256=')[1].split()[0]
    facts = tmp_path.parent / (tmp_path.name + '_f.json')
    facts.write_text(json.dumps(extractions))
    out = tmp_path.parent / (tmp_path.name + '_o.json')
    code = cli.main(['validate', '--candidates', str(candidates), '--candidates-sha256', digest,
                     '--extractions', str(facts), '--output', str(out)])
    return code, out


def test_a_fact_for_a_comment_the_ai_did_not_report_reading_is_rejected(tmp_path, capsys):
    code, out = validate_with(tmp_path, capsys, {'processed': ['2003'], 'facts': [fact()]})  # reads 2003, cites 2001
    result = json.loads(out.read_text())
    assert code == 0 and result['postings'] == [] and result['source']['rejected_items'] == 1
    assert result['processed_ids'] == ['2003']  # 2001 stays unread, so it stays queued


@pytest.mark.parametrize('extractions', [
    [fact()],                                              # the old bare list is no longer accepted
    {'processed': ['9999'], 'facts': []},                  # not a candidate
    {'processed': ['2001', '2001'], 'facts': []},          # repeated
    {'processed': [2001], 'facts': []},
    {'processed': [], 'facts': [], 'extra': 1},
])
def test_malformed_extractions_fail_closed_and_write_nothing(tmp_path, capsys, extractions):
    code, out = validate_with(tmp_path, capsys, extractions)
    assert code == 2 and not out.exists()
    assert 'hn_failed: invalid_extractions' in capsys.readouterr().out


def test_a_comment_with_a_rejected_fact_is_not_marked_read(tmp_path, capsys):
    # 2001 gets an invented company (rejected); 2003 is read cleanly with no matching role.
    code, out = validate_with(tmp_path, capsys, {'processed': ['2001', '2003'], 'facts': [fact(company='Not Acme')]})
    result = json.loads(out.read_text())
    assert code == 0 and result['postings'] == [] and result['source']['rejected_items'] == 1
    assert result['rejected_item_ids'] == ['2001']
    assert result['processed_ids'] == ['2003']  # 2001 stays queued, so the job is retried tomorrow
    assert 'held_for_retry=1' in capsys.readouterr().out


def test_validate_prints_why_the_fact_was_rejected_and_keeps_it_in_the_result(tmp_path, capsys):
    code, out = validate_with(tmp_path, capsys, {'processed': ['2001'], 'facts': [fact(company='Not Acme')]})
    printed = capsys.readouterr().out
    assert code == 0 and 'rejected_facts=1[not_in_post:company=1]' in printed
    assert 'trace_rejected: 2001:not_in_post:company' in printed
    saved = json.loads(out.read_text())
    assert saved['trace']['rejected_facts'] == {'not_in_post:company': 1}
    assert saved['rejections'] == [{'item_id': '2001', 'reason': 'not_in_post:company'}]


def test_one_rejected_fact_holds_a_comment_even_when_another_fact_in_it_was_accepted(tmp_path, capsys):
    good = fact()
    bad = fact(title='Product Manager, Robots')  # same comment, second role not in its text
    code, out = validate_with(tmp_path, capsys, {'processed': ['2001'], 'facts': [good, bad]})
    result = json.loads(out.read_text())
    assert code == 0 and len(result['postings']) == 1  # the supported role is still delivered
    assert result['processed_ids'] == []  # but the comment is read again until every fact in it validates


def test_a_fact_for_a_real_comment_not_reported_as_read_holds_nothing(tmp_path, capsys):
    code, out = validate_with(tmp_path, capsys, {'processed': ['2001'], 'facts': [fact(comment_id='2003'), fact(comment_id=2003)]})
    result = json.loads(out.read_text())
    assert code == 0 and result['rejected_item_ids'] == [] and result['processed_ids'] == ['2001']


@pytest.mark.parametrize('claimed', ['200l', '9999', 9999, '', ' 2001'])
def test_a_mistyped_or_invented_comment_id_holds_every_comment_that_was_read(tmp_path, capsys, claimed):
    code, out = validate_with(tmp_path, capsys, {'processed': ['2001'], 'facts': [fact(comment_id=claimed)]})
    assert code == 0 and json.loads(out.read_text())['processed_ids'] == []


def test_a_numeric_comment_id_in_a_rejected_fact_still_holds_its_comment(tmp_path, capsys):
    code, out = validate_with(tmp_path, capsys, {'processed': ['2001', '2003'], 'facts': [fact(comment_id=2001)]})
    result = json.loads(out.read_text())
    assert code == 0 and result['postings'] == [] and result['rejected_item_ids'] == ['2001']
    assert result['processed_ids'] == ['2003']


@pytest.mark.parametrize('junk', ['not a fact', {'title': 'no id at all'}, {'comment_id': None}, {'comment_id': True},
                                  {'comment_id': ['2001']}])
def test_a_rejected_fact_that_names_no_comment_holds_every_comment_that_was_read(tmp_path, capsys, junk):
    code, out = validate_with(tmp_path, capsys, {'processed': ['2001', '2003'], 'facts': [junk]})
    assert code == 0 and json.loads(out.read_text())['processed_ids'] == []


def test_business_operations_comments_are_not_candidates_because_delivery_cannot_collect_them():
    data = item(1000, [comment(2001, 'Acme | Business Operations Manager | Remote US'),
                       comment(2003, 'Beta | BizOps Lead | NYC'),
                       comment(2005, 'Gamma | Chief of Staff | Remote US')])
    found, _ = hn.candidate_comments(THREAD, data, NOW - timedelta(days=28))
    assert [c['comment_id'] for c in found] == ['2005']


def test_a_candidate_file_over_the_default_limit_is_written_with_its_digest_and_drains_through_the_queue(tmp_path, capsys):
    from scripts import ai_queue as queue_cli
    from sheet_fakes import MemoryStore
    big = 'Acme | Product Manager | Remote US ' + 'y' * 14000
    story = item(1000, [comment(2001 + 2 * i, big) for i in range(400)])  # about 5.6 MB of role comments
    candidates = tmp_path.parent / (tmp_path.name + '_big.json')
    assert cli.main(['candidates', '--output', str(candidates)], client=hn_client(story), sleep=lambda s: None,
                    now=lambda: NOW) == 0
    out = capsys.readouterr().out
    assert candidates.stat().st_size > 5 * 1024 * 1024 and 'candidates=400' in out and 'truncated=False' in out
    digest = out.split('candidates_sha256=')[1].split()[0]
    store, seen = MemoryStore(), set()
    for round_number in range(1, 10):
        work = tmp_path.parent / (tmp_path.name + f'_work{round_number}.json')
        assert queue_cli.main(['pull', '--source', 'hn-who-is-hiring', '--candidates', str(candidates),
                               '--candidates-sha256', digest, '--output', str(work)], store=store) == 0
        capsys.readouterr()
        handed = json.loads(work.read_text())['candidates']
        if not handed:
            break
        assert work.stat().st_size < 5 * 1024 * 1024  # what Claude is handed always fits the default limit
        seen |= {c['comment_id'] for c in handed}
        assert queue_cli.main(['commit', '--source', 'hn-who-is-hiring', '--result', str(_result_with(tmp_path, handed, round_number)),
                               '--result-sha256', _digest_of(tmp_path, round_number)], store=store) == 0
        capsys.readouterr()
    assert len(seen) == 400  # nothing was cut off: the tail waited its turn instead of being dropped


def _result_with(tmp_path, handed, number):
    from jobhunter.artifacts import write_artifact
    path = tmp_path.parent / (tmp_path.name + f'_res{number}.json')
    _DIGESTS[number] = write_artifact(path, {'processed_ids': [c['comment_id'] for c in handed]})
    return path


def _digest_of(tmp_path, number):
    return _DIGESTS[number]


_DIGESTS = {}


@pytest.mark.parametrize('title', ['Product Manager', 'Group Product Manager', 'Head of Product', 'VP of Product',
                                   'Chief of Staff', 'Leadership Development Program', 'MBA rotational program',
                                   'management development program', 'Strategy Manager', 'Head of Strategy',
                                   'Entrepreneur in Residence', 'Founder in Residence', 'Project Manager',
                                   'Project Management Lead'])
def test_every_role_the_delivery_filter_collects_is_a_candidate(title):
    assert hn.ROLE_WORDS.search(f'Acme | {title} | Remote US')
    assert p.role_family(title)  # and delivery really does collect it


@pytest.mark.parametrize('text', ['Acme | Business Operations Manager | NYC', 'Call me at 5 PM', 'Backend Engineer | strategy game studio',
                                  'Product Owner'])
def test_things_delivery_cannot_collect_are_not_candidates(text):
    assert not hn.ROLE_WORDS.search(text)
