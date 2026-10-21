"""Two spellings of one output file must be refused before the day's allowance is used."""

from pathlib import Path

from scripts import linkedin_collect as li
from sheet_fakes import MemoryStore
from test_linkedin_collect import COOKIES, fetcher, ok

STAMP = '2026-10-19T16:00:00+00:00'


def test_linkedin_output_alias_is_rejected_before_any_allowance_or_request(tmp_path):
    output = str(tmp_path.parent / (tmp_path.name + '-alias.json'))
    alias = str(tmp_path.parent) + '/./' + Path(output).name
    store = MemoryStore()
    session = fetcher(ok())
    code = li.main(['--run-id', 'alias-check', '--output', output, '--jobs-output', alias],
                   store=store, fetcher=session, environ=COOKIES, now=lambda: STAMP, sleep=lambda _: None)
    assert code == 2
    assert '_State' not in store.tables and not Path(output).exists()
    assert session.session.urls == []
