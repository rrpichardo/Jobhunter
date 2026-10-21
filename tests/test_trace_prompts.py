"""The run report can only copy the trace lines if validation prints them and the prompts say to copy them.

This replays, offline, the October 19 situation (an X post that names no company) through the same commands the live
run used, and checks the printed words against what the prompts and docs promise.
"""
import json
from pathlib import Path

from jobhunter import post_facts as pf
from jobhunter.artifacts import write_artifact
from jobhunter.social_collect import candidate_artifact
from jobhunter import postings as p
from scripts import ai_queue as queue_cli
from scripts import social_posts
from sheet_fakes import MemoryStore

ROOT = Path(__file__).resolve().parent.parent
POST_ID = '1850000000000000001'
TEXT = 'We are hiring a Product Manager (Remote US), open to MBA students graduating in spring 2027, DM me.'


def test_validation_prints_the_trace_lines_with_the_empty_company_reason(tmp_path, capsys):
    candidates = tmp_path / 'cand.json'
    items = [{'url': f'https://x.com/someone/status/{POST_ID}', 'created_at': '2026-10-20T12:00:00+00:00', 'text': TEXT,
              'links': []}]
    digest = write_artifact(candidates, candidate_artifact('x-twscrape', items, '2026-10-21T12:00:00+00:00',
                                                           queries_run=1, error=''))
    work = tmp_path / 'work.json'
    assert queue_cli.main(['pull', '--source', 'x-twscrape', '--candidates', str(candidates), '--candidates-sha256', digest,
                           '--output', str(work), '--id-field', 'item_id'], store=MemoryStore()) == 0
    work_digest = capsys.readouterr().out.split('work_sha256=')[1].split()[0]
    facts = tmp_path / 'facts.json'
    facts.write_text(json.dumps({'processed': [POST_ID], 'facts': [{
        'item_id': POST_ID, 'title': 'Product Manager', 'company': '', 'location': 'Remote US', 'salary': '',
        'description_quote': 'We are hiring a Product Manager (Remote US), open to MBA students graduating in spring 2027',
        'apply_url': ''}]}))
    result = tmp_path / 'result.json'
    assert social_posts.main(['validate', '--source', 'x-twscrape', '--candidates', str(work), '--candidates-sha256',
                              work_digest, '--extractions', str(facts), '--output', str(result)]) == 0
    lines = capsys.readouterr().out.splitlines()
    trace = [line for line in lines if line.startswith('trace:')]
    rejected = [line for line in lines if line.startswith('trace_rejected:')]
    assert len(trace) == 1 and 'rejected_facts=1[empty:company=1]' in trace[0]
    assert rejected == [f'trace_rejected: {POST_ID}:empty:company']
    assert 'held_for_retry=1' in lines[0] and 'DM me' not in '\n'.join(lines)   # post text never reaches the report


def test_both_run_prompts_tell_the_reporter_to_copy_the_exact_line_names_validation_prints():
    for name in ('ROUTINE_PROMPT.md', 'LIVE_RUN_PROMPT.md'):
        text = (ROOT / 'docs' / name).read_text()
        assert '`trace:`' in text and '`trace_rejected:`' in text and 'unchanged' in text, name
    # and the words the docs promise are the words the code prints
    rendered = pf.format_trace({'trace': {'facts_read': 1, 'valid': 0, 'duplicates': 0, 'rejected_facts': {'empty:company': 1},
                                          'unreadable_posts': 0, 'dropped_by_filter': {}, 'delivered': 0, 'held_items': 1,
                                          'held_every_read_item': False},
                                'rejections': [{'item_id': POST_ID, 'reason': 'empty:company'}]})
    assert [line.split(':')[0] for line in rendered.splitlines()] == ['trace', 'trace_rejected']


def test_every_reason_code_the_code_can_print_is_explained_in_the_traceability_doc():
    doc = (ROOT / 'docs' / 'TRACEABILITY.md').read_text()
    for code in ('invalid_post_facts', 'unknown_post', 'link_not_in_post_links', 'link_not_https', 'malformed_fact',
                 'role_not_in_scope', 'place_excluded', 'pay_below_floor', 'not_mba_2027', 'class_2027_without_mba',
                 'mba_other_class_year'):
        assert f'`{code}`' in doc, code
    for template in ('not_text', 'too_long', 'empty', 'not_in_post'):
        assert f'`{template}:<field>`' in doc, template
    assert {reason.split(':')[0] for reason in pf.REASONS} >= {'not_text', 'too_long', 'empty', 'not_in_post'}


def test_every_drop_code_collection_reason_can_return_is_named_in_the_routine_prompt():
    prompt = (ROOT / 'docs' / 'ROUTINE_PROMPT.md').read_text()
    source = (ROOT / 'jobhunter' / 'postings.py').read_text()
    start = source.index('def collection_reason')
    codes = {'role_not_in_scope', 'place_excluded', 'pay_below_floor', 'not_mba_2027', 'class_2027_without_mba',
             'mba_other_class_year'}
    body = source[start:source.index('def collection_match')]
    assert all(code in body for code in codes) and all(code in prompt for code in codes)
