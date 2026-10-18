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
    extractions.write_text(json.dumps([fact()]))
    validated = tmp_path.parent / (tmp_path.name + '_hn.json')
    assert cli.main(['validate', '--candidates', str(candidates), '--candidates-sha256', digest,
                     '--extractions', str(extractions), '--output', str(validated)]) == 0
    out = capsys.readouterr().out
    result_digest = out.split('hn_result_sha256=')[1].split()[0]
    assert 'delivered=1' in out
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
    extractions.write_text('[]')
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
