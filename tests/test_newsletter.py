"""Job newsletter feed (Ali Rohde Jobs): editions become candidates; facts are checked like any social post."""

from datetime import datetime, timezone
import hashlib
import json

import pytest

from jobhunter import newsletter as nl
from scripts import ai_queue as queue_cli
from scripts import newsletter_collect as collect
from scripts import social_posts
from sheet_fakes import MemoryStore

NOW = datetime(2026, 10, 19, 16, tzinfo=timezone.utc)
SOURCE = 'alirohde-rss'
BODY = ('<p>Welcome to Edition 275! <a href="https://alirohdejobs.substack.com/subscribe?">Subscribe now</a></p>'
        '<h3>Chief of Staff roles</h3><p><a href="https://jobs.ashbyhq.com/acme/1234-abcd">Chief of Staff to the CEO</a>, '
        'Acme (AI, Series B), Remote</p><p><a href="https://boards.greenhouse.io/beta/jobs/55">Associate Chief of Staff</a>, '
        'Beta (Health, Series A), NYC</p>')


def item(title, published, link, content=BODY):
    return (f'<item><title>{title}</title><link>{link}</link><guid>{link}</guid><pubDate>{published}</pubDate>'
            f'<content:encoded><![CDATA[{content}]]></content:encoded></item>')


def feed(*items):
    return ('<?xml version="1.0"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">'
            f'<channel><title>Ali Rohde Jobs</title>{"".join(items)}</channel></rss>')


NEW = item('Edition 275', 'Fri, 16 Oct 2026 15:17:32 GMT', 'https://alirohdejobs.substack.com/p/edition-275-ali-rohde-jobs')
OLD = item('Edition 200', 'Fri, 01 May 2026 15:17:32 GMT', 'https://alirohdejobs.substack.com/p/edition-200-ali-rohde-jobs')
ELSEWHERE = item('Fake', 'Fri, 16 Oct 2026 15:17:32 GMT', 'https://evil.example/p/edition-1')


def test_an_edition_inside_the_window_becomes_a_candidate_with_each_link_beside_its_text():
    candidates, stats = nl.edition_candidates(SOURCE, feed(NEW, OLD), NOW, 28)
    assert stats == {'editions': 2, 'in_window': 1, 'unreadable': 0} and len(candidates) == 1
    edition = candidates[0]
    assert edition['url'] == 'https://alirohdejobs.substack.com/p/edition-275-ali-rohde-jobs'
    assert 'Chief of Staff to the CEO [https://jobs.ashbyhq.com/acme/1234-abcd]' in edition['text']
    assert edition['links'] == ['https://jobs.ashbyhq.com/acme/1234-abcd', 'https://boards.greenhouse.io/beta/jobs/55']
    assert 'substack.com/subscribe' not in edition['text']  # its own subscribe link is not a job link


def test_an_entry_on_another_host_or_without_content_is_counted_not_kept():
    empty = item('Empty', 'Fri, 16 Oct 2026 15:17:32 GMT', 'https://alirohdejobs.substack.com/p/empty-one', content='')
    candidates, stats = nl.edition_candidates(SOURCE, feed(ELSEWHERE, empty), NOW, 28)
    assert candidates == [] and stats['unreadable'] == 2


def test_a_page_that_is_not_a_feed_is_refused():
    with pytest.raises(ValueError, match='invalid_board_response'):
        nl.edition_candidates(SOURCE, '<html><body>Just a moment...</body></html>', NOW, 28)


def run(tmp_path, text, status=200, extra=()):
    out = tmp_path.parent / (tmp_path.name + '_nl.json')
    code = collect.main(['--source', SOURCE, '--output', str(out), *extra], fetch=lambda url: (status, text), now=lambda: NOW)
    return code, out


def test_the_collector_writes_candidates_and_prints_numbers(tmp_path, capsys):
    code, out = run(tmp_path, feed(NEW, OLD))
    payload = json.loads(out.read_text())
    assert code == 0 and [c['item_id'] for c in payload['candidates']] == ['edition-275-ali-rohde-jobs']
    assert payload['stats']['in_window'] == 1 and 'newsletter_candidates_sha256=' in capsys.readouterr().out


@pytest.mark.parametrize('status', [403, 500])
def test_a_refused_feed_collects_nothing(tmp_path, capsys, status):
    code, out = run(tmp_path, '', status=status)
    assert code == 2 and not out.exists() and f'http_{status}' in capsys.readouterr().out


def test_the_edition_flows_through_the_queue_and_the_validator_and_pairs_a_role_with_its_link(tmp_path, capsys):
    code, out = run(tmp_path, feed(NEW))
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    work = tmp_path.parent / (tmp_path.name + '_work.json')
    assert queue_cli.main(['pull', '--source', SOURCE, '--candidates', str(out), '--candidates-sha256', digest,
                           '--output', str(work), '--id-field', 'item_id'], store=MemoryStore()) == 0
    work_digest = capsys.readouterr().out.split('work_sha256=')[1].split()[0]
    facts = tmp_path.parent / (tmp_path.name + '_facts.json')
    edition = 'edition-275-ali-rohde-jobs'
    facts.write_text(json.dumps({'processed': [edition], 'facts': [
        {'item_id': edition, 'title': 'Chief of Staff to the CEO', 'company': 'Acme', 'location': 'Remote', 'salary': '',
         'description_quote': 'Chief of Staff to the CEO [https://jobs.ashbyhq.com/acme/1234-abcd] , Acme (AI, Series B), Remote',
         'apply_url': 'https://jobs.ashbyhq.com/acme/1234-abcd'},
        {'item_id': edition, 'title': 'Associate Chief of Staff', 'company': 'Beta', 'location': 'NYC', 'salary': '',
         'description_quote': 'Associate Chief of Staff [https://boards.greenhouse.io/beta/jobs/55] , Beta (Health, Series A), NYC',
         'apply_url': 'https://boards.greenhouse.io/beta/jobs/55'}]}))
    result = tmp_path.parent / (tmp_path.name + '_result.json')
    assert social_posts.main(['validate', '--source', SOURCE, '--candidates', str(work), '--candidates-sha256', work_digest,
                              '--extractions', str(facts), '--output', str(result)]) == 0
    data = json.loads(result.read_text())
    assert data['source']['source_id'] == SOURCE and data['source']['status'] == 'OK'
    assert {p['title']: p['apply_url'] for p in data['postings']} == {
        'Chief of Staff to the CEO': 'https://jobs.ashbyhq.com/acme/1234-abcd',
        'Associate Chief of Staff': 'https://boards.greenhouse.io/beta/jobs/55'}
    assert all(p['job_id'].startswith('alirohde:edition-275-ali-rohde-jobs:') and p['posted_at'].startswith('2026-10-16')
               for p in data['postings'])


def test_an_invented_value_or_a_link_the_edition_does_not_contain_is_rejected(tmp_path, capsys):
    code, out = run(tmp_path, feed(NEW))
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    facts = tmp_path.parent / (tmp_path.name + '_facts.json')
    edition = 'edition-275-ali-rohde-jobs'
    good = {'item_id': edition, 'title': 'Associate Chief of Staff', 'company': 'Beta', 'location': 'NYC', 'salary': '',
            'description_quote': 'Beta (Health, Series A), NYC', 'apply_url': ''}
    facts.write_text(json.dumps({'processed': [edition], 'facts': [
        {**good, 'company': 'Gamma'}, {**good, 'apply_url': 'https://evil.example/apply'}]}))
    result = tmp_path.parent / (tmp_path.name + '_result.json')
    assert social_posts.main(['validate', '--source', SOURCE, '--candidates', str(out), '--candidates-sha256', digest,
                              '--extractions', str(facts), '--output', str(result)]) == 0
    data = json.loads(result.read_text())
    assert data['postings'] == [] and data['source']['rejected_items'] == 2 and data['processed_ids'] == []  # held for retry
