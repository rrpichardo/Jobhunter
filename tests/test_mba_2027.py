"""Only roles meant for MBA graduates of 2027 are collected; seniority and "MBA preferred" do not decide it."""
from dataclasses import replace

import pytest

from jobhunter import postings as p
from mba_fixtures import MBA_2027, mba


def job(**changes):
    base = p.Posting('greenhouse:acme:1', 'greenhouse:acme', 'Acme', 'Product Manager', 'United States',
                     mba('Own the roadmap.'), 'https://boards.greenhouse.io/acme/jobs/1', '2026-10-21T00:00:00+00:00',
                     salary='USD 150,000 - 190,000 year')
    return replace(base, **changes)


# Sentences copied from real postings (October 2026) that ARE meant for MBA graduates of 2027.
MEANT_FOR_MBA_2027 = [
    'This role is open to MBA students graduating in spring 2027.',
    'We are recruiting MBA candidates who graduate in May 2027 for our leadership program.',
    'Join our 2027 MBA Leadership Development Program.',
    'Open to recent MBA graduates starting full time in summer 2027.',
    'MBA Class of 2027 only: this rotational program places MBAs in product teams.',
    'Post-MBA product role for the class graduating in 2027.',
]


@pytest.mark.parametrize('sentence', MEANT_FOR_MBA_2027)
def test_a_role_meant_for_mba_graduates_is_collected_and_the_row_quotes_the_words_that_say_so(sentence):
    posting = job(text=f'Build products. {sentence}')
    assert p.collection_reason(posting) == '' and p.collection_match(posting)
    row = p.to_row(posting)
    assert 'MBA 2027 evidence:' in row['More details']
    assert row['Brief description'].startswith('Build products.')  # the excerpt column is unaffected by the evidence line


@pytest.mark.parametrize('title', ['Senior Product Manager', 'Staff Product Manager', 'Director of Product',
                                   'Senior Product Manager, Vehicle Software (MBA Class of 2027)'])
def test_seniority_does_not_matter_when_the_role_is_meant_for_mba_graduates(title):
    assert p.collection_match(job(title=title, text=mba('Lead the roadmap.')))


# Qualification wording copied from real postings: a preference for an MBA is not a role meant for MBA graduates.
MBA_ONLY_AS_A_QUALIFICATION = [
    'MBA or other advanced degree in finance, economics, or business',
    'Bachelor\'s degree required; MBA or advanced degree preferred',
    'MBA is a strong plus',
    'MBA or equivalent professional experience at the intersection of technology and operations',
    'Hold a JD, MBA, or equivalent experience is preferred but not required.',
    'An MBA, JD, or technical degree from a top program',
]


@pytest.mark.parametrize('sentence', MBA_ONLY_AS_A_QUALIFICATION)
def test_an_mba_that_is_only_a_preferred_qualification_does_not_count(sentence):
    posting = job(text=f'Own the roadmap. {sentence}')
    assert p.collection_reason(posting) == 'not_mba_2027' and not p.collection_match(posting)


def test_a_plain_product_manager_posting_is_not_collected():
    assert p.collection_reason(job(text='Own the roadmap for billing.')) == 'not_mba_2027'


@pytest.mark.parametrize('text', ['New Grad (2027 Start). You will graduate in Fall 2026 or Spring 2027 with a bachelors or masters degree in computer science.',
                                  'Early Career, Associate Product Manager (2027)', 'Open to the class of 2027.'])
def test_a_2027_graduating_class_role_without_an_mba_is_dropped_with_its_own_reason(text):
    assert p.collection_reason(job(text=text)) == 'class_2027_without_mba'


def test_an_mba_program_for_another_graduating_year_is_dropped_with_its_own_reason():
    assert p.collection_reason(job(text='Open to MBA students graduating in spring 2026 (class of 2026).')) == 'mba_other_class_year'


def test_an_mba_internship_is_not_a_full_time_role():
    assert p.collection_reason(job(title='Strategic Finance & Analytics Intern (MBA)', text=mba('Finance.'))) == 'role_not_in_scope'


def test_the_mba_check_comes_after_role_and_place_and_before_pay():
    assert p.collection_reason(job(title='Software Engineer')) == 'role_not_in_scope'
    assert p.collection_reason(job(location='Berlin, Germany', text='Own it.')) == 'place_excluded'
    assert p.collection_reason(job(text='Own it.', salary='USD 50,000 per year')) == 'not_mba_2027'
    assert p.collection_reason(job(salary='USD 50,000 per year')) == 'pay_below_floor'


def test_the_shared_sample_sentence_is_itself_recognised():
    assert p.mba_class_evidence('Product Manager', MBA_2027)[0] == 'mba'


def test_the_probe_says_how_many_approved_roles_were_dropped_and_why():
    import httpx
    from scripts import source_probe
    data = [{'id': '1', 'text': 'Product Manager', 'categories': {'location': 'United States'},
             'descriptionPlain': mba('Build.'), 'hostedUrl': 'https://jobs.lever.co/acme/1'},
            {'id': '2', 'text': 'Senior Product Manager', 'categories': {'location': 'United States'},
             'descriptionPlain': 'Build billing. MBA preferred.', 'hostedUrl': 'https://jobs.lever.co/acme/2'},
            {'id': '3', 'text': 'Chief of Staff', 'categories': {'location': 'Berlin, Germany'},
             'descriptionPlain': mba('Chief of staff.'), 'hostedUrl': 'https://jobs.lever.co/acme/3'},
            {'id': '4', 'text': 'Engineer', 'categories': {'location': 'United States'},
             'descriptionPlain': mba('Code.'), 'hostedUrl': 'https://jobs.lever.co/acme/4'}]
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=data)))
    entry = {'id': 'lever:acme', 'kind': 'lever', 'board': 'acme', 'company': 'Acme', 'url': 'https://test.example/jobs'}
    record, jobs, note = source_probe.probe_source(client, entry, '2026-10-21T00:00:00+00:00')
    assert [job.title for job in jobs] == ['Product Manager']
    assert 'dropped=not_mba_2027:1,place_excluded:1' in note  # the engineer is not an approved role, so it is not counted


# Codex review of PR 52 (October 21): wording that mentions MBAs without saying who may apply must not qualify.
@pytest.mark.parametrize('text', [
    'Build learning products for MBA students graduating in spring 2027. Applicants must have 10 years of product experience.',
    'MBA preferred for this senior role supporting our 2027 launch.',
    'We make software that MBA students graduating in 2027 use to plan their careers.',
    'Our customers include MBA candidates; the product launches in 2027.',
])
def test_incidental_mba_wording_is_not_an_applicant_statement(text):
    assert p.collection_reason(job(text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('text', [
    'Open to MBA students graduating in spring 2028 only. Our new platform launches in 2027.',
    'This role is open to MBA students graduating in 2026. Our fiscal year 2027 starts in July.',
])
def test_an_unrelated_2027_cannot_override_an_explicit_other_class(text):
    assert p.collection_reason(job(text=text)) == 'mba_other_class_year'


def test_a_second_statement_for_2027_still_qualifies_a_posting_that_also_names_another_class():
    text = 'Open to MBA students graduating in spring 2026. Also open to MBA students graduating in spring 2027.'
    assert p.collection_reason(job(text=text)) == ''


def test_a_title_naming_the_applicants_qualifies():
    posting = job(title='Strategist, Agent Development (MBA Grad 2027)', text='Own it.')
    assert p.mba_class_evidence(posting.title, posting.text)[0] == 'mba'


def test_the_real_sierra_posting_wording_qualifies_and_the_real_qualification_wordings_do_not():
    assert p.mba_class_evidence('Strategist', 'ABOUT US ... This role is open to MBA students graduating in spring 2027. WHAT YOU DO')[0] == 'mba'
    for qualification in ('MBA or equivalent professional experience at the intersection of technology and operations',
                          "Bachelor's degree required; MBA or advanced degree preferred", 'MBA is a strong plus'):
        assert p.mba_class_evidence('Product Manager', qualification)[0] == ''
