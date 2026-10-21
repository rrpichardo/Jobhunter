"""The trace may print only fixed reason codes and item ids the run itself supplied."""

from jobhunter import post_facts as pf
from test_social_posts import build, fact


def test_unknown_fact_id_cannot_copy_a_name_into_the_trace():
    result = build([fact(item_id='example_person_name')])
    assert result['rejections'] == [{'item_id': '', 'reason': 'unknown_post'}]
    assert 'example_person_name' not in pf.format_trace(result)


def test_reason_codes_are_an_allowlist_not_arbitrary_lowercase_text():
    assert pf._reason(ValueError('example_person_name')) == 'malformed_fact'
    assert pf._reason(ValueError('empty:company')) == 'empty:company'
