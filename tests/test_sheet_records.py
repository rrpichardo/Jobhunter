from copy import deepcopy

import pytest

from test_m0_records import source
from jobhunter.records import validate_extractions


def job(n=1, **changes):
    row = validate_extractions([source()], [{'job_id': source().job_id,
                                             'description_quote': 'Build safe AI'}])[0]
    return row | {'Job ID': f'greenhouse:example:{n}'} | changes


def test_upserts_preserve_user_cells_and_first_seen_with_reordered_headers():
    from jobhunter.sheet_records import JOB_HEADERS, plan_jobs
    headers = list(reversed(JOB_HEADERS)) + ['My extra column']
    old = job(**{'Status': 'Applied', 'Notes': 'keep', 'My rating': '5',
                 'Date found': '2020-01-01', 'Job title': 'old'})
    rows = [headers, [old.get(h, 'extra') for h in headers]]
    plan = plan_jobs(rows, [job(**{'Job title': 'updated', 'Date found': '2026-10-17'})])
    assert plan
    excluded = {headers.index(h) + 1 for h in ('Status', 'Notes', 'My rating', 'Date found', 'My extra column')}
    assert all(update.row == 2 and update.column not in excluded for update in plan)
    assert any(update.values == [['updated']] for update in plan)
    assert rows[1] == [old.get(h, 'extra') for h in headers]


def test_new_jobs_are_deduped_last_wins_and_initialize_only_new_user_fields():
    from jobhunter.sheet_records import JOB_HEADERS, plan_jobs
    incoming = [job(**{'Job title': 'old'}), job(**{'Job title': '=literal', 'Status': 'Applied', 'Notes': 'ignored'})]
    plan = plan_jobs([list(JOB_HEADERS)], incoming)
    assert len(plan) == 1
    assert plan[0].row == 2 and plan[0].column == 1
    values = dict(zip(JOB_HEADERS, plan[0].values[0]))
    assert values['Job title'] == '=literal'
    assert values['Status'] == 'New' and values['Notes'] == '' and values['My rating'] == ''


def test_repeated_sync_and_sorting_between_syncs_rebuilds_identity_mapping():
    from jobhunter.sheet_records import JOB_HEADERS, plan_jobs
    a, b = job(1), job(2)
    rows = [list(JOB_HEADERS), list(b.values()), list(a.values())]
    assert plan_jobs(rows, [a, b]) == []
    plan = plan_jobs(rows, [a | {'Job title': 'changed'}])
    assert len(plan) == 1 and plan[0].row == 3


@pytest.mark.parametrize('damage', ['duplicate_id', 'duplicate_header', 'missing_header', 'unkeyed_data'])
def test_ambiguous_existing_sheet_aborts_before_a_write_plan(damage):
    from jobhunter.sheet_records import JOB_HEADERS, plan_jobs
    rows = [list(JOB_HEADERS), list(job().values())]
    if damage == 'duplicate_id': rows.append(deepcopy(rows[1]))
    if damage == 'duplicate_header': rows[0][1] = rows[0][0]
    if damage == 'missing_header': rows[0][1] = 'Unknown'
    if damage == 'unkeyed_data': rows[1][0] = ''
    with pytest.raises(ValueError): plan_jobs(rows, [job(2)])


def test_oversized_or_untyped_values_are_rejected():
    from jobhunter.sheet_records import JOB_HEADERS, plan_jobs
    for bad in (job(**{'Notes': {'bad': 'type'}}), job(**{'Job title': 'x' * 40001}),
                job(**{'Rank (prelim)': float('nan')}), job(**{'Job ID': ''})):
        with pytest.raises(ValueError): plan_jobs([list(JOB_HEADERS)], [bad])
