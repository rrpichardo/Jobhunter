"""When two sources find the same job ID, the earliest discovery time of each source is kept."""
import pytest

from jobhunter import postings as p

STAMP = '2026-10-19T16:00:00+00:00'


@pytest.mark.parametrize('prefix,sources', [('waas', ('waas-product', 'waas-operations')),
                                          ('a16z', ('a16z-product', 'a16z-strategy'))])
def test_same_id_discoveries_keep_each_sources_earliest_time(prefix, sources):
    def posting(source, stamp):
        return p.Posting(prefix + ':11', source, 'Acme', 'Product Manager', 'Remote', 'text',
                         'https://acme.example/careers', stamp)
    kept = p.dedupe([posting(sources[0], STAMP), posting(sources[1], STAMP),
                     posting(sources[1], '2026-10-18T10:00:00+00:00')])
    assert len(kept) == 1
    assert f'First seen by {sources[1]}: 2026-10-18T10:00:00+00:00' in kept[0][1]
