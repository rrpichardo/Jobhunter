"""A model comparison must not score items nobody read as an agreement."""

import pytest

from scripts import eval_reading as ev

STAMP = '2026-10-19T16:00:00+00:00'


@pytest.mark.parametrize('processed', [[], ['1'], ['1', '1'], ['1', '2', 'unknown']])
def test_model_comparison_refuses_incomplete_or_unrecognized_reading(processed):
    items = [{'item_id': str(n), 'text': 'No roles here.', 'url': f'https://x.com/example/status/{n}',
              'links': [], 'created_at': STAMP} for n in (1, 2)]
    with pytest.raises(ValueError, match='incomplete_eval_reading'):
        ev.compare(items, 'item_id', {'processed': processed, 'facts': []},
                   {'processed': ['1', '2'], 'facts': []}, ('sonnet', 'haiku'))
