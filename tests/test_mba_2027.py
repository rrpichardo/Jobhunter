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


@pytest.mark.parametrize('title', ['2027 North America Business Leadership Development Program (Full-Time MBA)',
                                   'Rotational Product Manager (MBA)'])
def test_a_title_that_marks_the_program_as_mba_qualifies(title):
    assert p.mba_class_evidence(title, 'Join us.')[0] == 'mba'


def test_mba_in_parentheses_as_a_preference_does_not_qualify():
    assert p.mba_class_evidence('Product Manager', 'Experience (MBA preferred) in payments.')[0] == ''


# Codex re-review of PR 52 (October 21, cycle 2): ordinary wording variants of the same defects.
@pytest.mark.parametrize('text', [
    'We are hiring a PM to build products for MBA students graduating in spring 2027.',
    'We are hiring a product manager to build tools for MBA candidates graduating in 2027.',
    'We are seeking engineers to support recruiting for MBA graduates in 2027.',
])
def test_a_hiring_verb_does_not_make_the_products_users_the_applicants(text):
    assert p.collection_reason(job(text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('text', [
    'We are hiring MBA students graduating in spring 2027.',
    'We are recruiting talented recent MBA graduates for summer 2027.',
    'We are seeking current MBA candidates, class of 2027.',
])
def test_a_hiring_verb_directly_followed_by_the_applicants_still_qualifies(text):
    assert p.collection_reason(job(text=text)) == ''


def test_the_program_year_anywhere_in_the_title_counts():
    posting = job(title='2028 North America Business Leadership Development Program (Full-Time MBA)', text='Join our program.')
    assert p.mba_class_evidence(posting.title, posting.text)[0] == 'other_year'
    ok = job(title='2027 North America Business Leadership Development Program (Full-Time MBA)', text='Join our program.')
    assert p.mba_class_evidence(ok.title, ok.text)[0] == 'mba'


def test_an_unqualified_title_match_cannot_hide_an_explicit_other_class_in_the_description():
    assert p.mba_class_evidence('Product Manager (MBA)', 'Open to MBA students graduating in spring 2028 only.')[0] == 'other_year'
    assert p.mba_class_evidence('Product Manager (MBA)', 'Open to MBA students graduating in spring 2027.')[0] == 'mba'
    assert p.mba_class_evidence('Product Manager (MBA)', 'Join us.')[0] == 'mba'
    # a posting for both classes qualifies through the 2027 statement
    assert p.mba_class_evidence('Associate', 'Open to MBA students graduating in 2026. Also open to MBA students graduating in 2027.')[0] == 'mba'


@pytest.mark.parametrize('text', [
    'Education: Master of Business Administration (MBA) or Juris Doctor (JD) degree, with preference of JD.',
    "Bachelor's degree; Master of Business Administration (MBA) strongly preferred.",
    'A graduate degree (MBA) is helpful.',
])
def test_a_degree_requirement_in_parentheses_in_the_description_does_not_qualify(text):
    assert p.mba_class_evidence('Deal Team - Business Affairs', text)[0] == ''


# Codex re-review of PR 52 (October 21, cycle 3): negation, noun-first eligibility, unrelated years, positive and negative.
@pytest.mark.parametrize('text', [
    'This role is not open to MBA students graduating in spring 2027.',
    'This role is NOT open to MBA students graduating in spring 2027.',
    'We do not recruit MBA candidates graduating in 2027.',
    'This position is not for MBA students graduating in 2027.',
    'Not open to MBA students graduating in 2027.',
    'Open to all except MBA students graduating in 2027.',
    'MBA students graduating in 2027 are not eligible to apply.',
    'MBA students graduating in 2027 should not apply.',
])
def test_a_denied_applicant_statement_is_not_evidence(text):
    assert p.collection_reason(job(text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('text', [
    'This role is open to MBA students graduating in spring 2027, not undergraduates.',
    'No experience required. This role is open to MBA students graduating in spring 2027.',
    'A role with no travel, open to MBA students graduating in spring 2027.',
])
def test_a_negative_word_elsewhere_does_not_cancel_an_applicant_statement(text):
    assert p.collection_reason(job(text=text)) == ''


@pytest.mark.parametrize('text', [
    'MBA students graduating in May 2027 are eligible to apply.',
    'MBA students graduating in May 2027 are encouraged to apply.',
    'MBA candidates graduating in 2027 should apply.',
    'Recent MBA graduates (class of 2027) are welcome to apply.',
])
def test_noun_first_eligibility_wording_qualifies(text):
    assert p.collection_reason(job(text=text)) == ''


@pytest.mark.parametrize('text', [
    'MBA students graduating in 2027 use our app and are eligible for a discount.',
    'Our customers, MBA students graduating in 2027, are eligible for free shipping.',
])
def test_noun_first_wording_about_customers_does_not_qualify(text):
    assert p.collection_reason(job(text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('text,expected', [
    ('Open to MBA students graduating in spring 2028 only, with applications opening in 2027.', 'mba_other_class_year'),
    ('Open to MBA students graduating in 2028. Applications open in 2027.', 'mba_other_class_year'),
    ('Open to recent MBA graduates starting in 2028.', 'mba_other_class_year'),
    ('Open to MBA students graduating in spring 2027, with applications opening in 2026.', ''),
    ('Open to MBA students graduating in 2027; applications close in 2028.', ''),
    ('This role is open to MBA students graduating in 2027 and starting in 2028.', ''),
    ('Open to MBA students, applications open in 2027.', ''),
    ('Open to recent MBA graduates starting full time in summer 2027.', ''),
])
def test_only_the_class_or_program_year_counts_not_an_application_or_launch_year(text, expected):
    assert p.collection_reason(job(text=text)) == expected


# Codex re-review of PR 52 (review 5601000995, cycle 4). Defect 1: a negation that belongs to another clause ("Experience is
# not required") must not cancel the applicant statement after it; a denial of the applicants themselves still does.
@pytest.mark.parametrize('text', [
    'Experience is not required, open to MBA students graduating in May 2027.',
    'No prior product experience is required, open to MBA students graduating in May 2027.',
    'Relocation is not provided; this role is open to MBA students graduating in May 2027.',
    "Experience isn't needed, we are recruiting MBA students graduating in May 2027.",
])
def test_a_negation_in_an_unrelated_clause_does_not_cancel_the_applicant_statement(text):
    assert p.collection_reason(job(text=text)) == ''


@pytest.mark.parametrize('text', [
    'This role is not open to MBA students graduating in May 2027.',
    'We are not recruiting MBA students graduating in May 2027.',
    'We are not recruiting MBA students.',
    'MBA students graduating in May 2027 are not eligible to apply.',
    'MBA graduates 2027 should not apply.',
    'MBA students graduating in May 2027 are ineligible.',
    "This role isn't for MBA students graduating in 2027.",
    'We are not currently recruiting MBA students graduating in 2027.',
    'We never hire MBA graduates of the class of 2027.',
    'Our 2027 MBA Associate Program is not open to MBA students graduating in 2027.',
])
def test_an_explicit_denial_of_the_applicants_is_never_evidence(text):
    assert p.collection_reason(job(text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('title,text', [
    ('Product Manager (MBA)', 'MBA students graduating in May 2027 are not eligible to apply.'),
    ('Associate (MBA Grad 2027)', 'MBA graduates 2027 should not apply.'),
    ('Product Manager', 'MBA Class of 2027 students are not eligible to apply.'),
    ('Rotational Product Manager (MBA)', 'This program is not open to MBA students.'),
])
def test_a_title_or_standalone_match_cannot_resurrect_eligibility_the_posting_denies(title, text):
    assert p.mba_class_evidence(title, text)[0] != 'mba'


# Defect 2: every graduation alternative and range is read, so a statement that also names 2027 qualifies.
@pytest.mark.parametrize('text', [
    'Open to MBA students graduating in May 2026 or May 2027.',
    'Open to MBA students graduating in December 2026 or May 2027.',
    'Open to MBA students graduating between December 2026 and June 2027.',
    'Open to MBA students graduating from December 2026 to June 2027.',
    'Open to MBA students graduating in 2026-2028.',
    'Open to MBA students graduating in 2026, 2027 or 2028.',
    'Open to MBA candidates in the classes of 2026 and 2027.',
    'MBA students graduating in May 2026 or May 2027 are eligible to apply.',
    'Open to MBA students graduating Dec 2026 - May 2027.',
    'Open to MBA students (class of 2026 or 2027).',
    'Not open to MBA students graduating in 2026; open to MBA students graduating in 2027.',
    'We are not only hiring MBA students graduating in 2027 but also undergraduates.',
])
def test_every_graduation_alternative_and_range_that_includes_2027_qualifies(text):
    assert p.collection_reason(job(text=text)) == ''


@pytest.mark.parametrize('text', [
    'Open to MBA students graduating in May 2026 or May 2028.',
    'Open to MBA students graduating between 2028 and 2029.',
    'Open to MBA students graduating in 2028 only, with applications opening in 2027.',
    'Open to MBA students graduating in 2028; our fiscal year 2027 starts in July.',
    'Open to MBA students graduating in 2028. Start date in 2027 is flexible for others.',
    'Open to MBA students graduating in 2025 to 2026, starting in 2027.',
])
def test_alternatives_and_ranges_without_2027_and_unrelated_2027s_stay_wrong_class(text):
    assert p.collection_reason(job(text=text)) == 'mba_other_class_year'


# Codex review 5606618473 of PR 53 (cycle 5): denial binding and bare MBAs.
@pytest.mark.parametrize('text', [
    'Not open to MBA students graduating in 2026, but open to MBA students graduating in 2027.',
    'Not open to MBA students graduating in 2026, however open to MBA students graduating in 2027.',
    'Not open to MBA students graduating in May 2026, while open to MBA students graduating in May 2027.',
    'Open to MBA students graduating in May 2027. MBA students graduating in May 2027 are not eligible for relocation assistance but may apply.',
    'Open to MBA students graduating in May 2027. MBA students graduating in May 2027 are not eligible for the signing bonus.',
    'Open to MBA students graduating in May 2027. MBA students are ineligible for relocation support.',
])
def test_a_denial_binds_to_its_own_clause_and_a_benefit_is_not_the_application(text):
    assert p.collection_reason(job(text=text)) == ''


@pytest.mark.parametrize('text', [
    'Not open to MBA students graduating in 2027, but open to MBA students graduating in 2026.',
    'MBA students graduating in May 2027 are not eligible to apply.',
    'MBA students graduating in May 2027 are not eligible for this role.',
    'MBA students graduating in May 2027 are not eligible for the position.',
    'MBA students graduating in May 2027 are not eligible for consideration.',
    'MBA students graduating in May 2027 are not eligible.',
    'MBA students graduating in May 2027 are ineligible to apply.',
])
def test_a_denial_of_the_application_itself_still_cancels_the_statement(text):
    assert p.collection_reason(job(text=f'Open to MBA students graduating in May 2027. {text}')) == 'not_mba_2027'


@pytest.mark.parametrize('text', [
    'We cannot hire MBAs.',
    'We do not hire MBAs.',
    'We are not able to recruit any MBAs.',
    "We won't accept MBAs.",
    'MBAs are not eligible to apply.',
    'MBAs should not apply.',
])
def test_an_explicit_denial_of_bare_mbas_beats_a_title_marker(text):
    assert p.collection_reason(job(title='Product Manager (MBA)', text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('text', [
    'We are not only hiring MBAs but also undergraduates. Open to MBA students graduating in 2027.',
    'A degree is not required; an MBA is preferred. Open to MBA students graduating in 2027.',
    'We do not require an MBA degree. Open to MBA students graduating in 2027.',
])
def test_not_only_and_degree_wording_are_not_denials_of_mbas(text):
    assert p.collection_reason(job(text=text)) == ''


@pytest.mark.parametrize('text,expected', [
    ('Not open to MBA students, but MBA students graduating in 2027 are welcome to apply.', ''),
    ('Not open to MBA students graduating in 2026, but open to MBA students graduating in 2026.', 'mba_other_class_year'),
    ('Not open to MBA students.', 'not_mba_2027'),
])
def test_contrast_neighbors_of_the_denial_binding(text, expected):
    assert p.collection_reason(job(text=text)) == expected


# Codex follow-up review 5608956351 of PR 53 (cycle 6).
@pytest.mark.parametrize('text', [
    'Open to MBA students graduating in 2027. For the class of 2026, MBA students are not eligible to apply.',
    'Open to MBA students graduating in 2027. Class of 2026 MBA students are not eligible to apply.',
    'Open to MBA students graduating in 2027. MBA students graduating in 2026 are not eligible to apply.',
    'Open to MBA students graduating in 2027, but for the class of 2026, MBA students are not eligible to apply.',
])
def test_a_denial_keeps_its_leading_class_qualifier_and_does_not_veto_another_class(text):
    assert p.collection_reason(job(text=text)) == ''


@pytest.mark.parametrize('text', [
    'Open to MBA students graduating in 2027. For the class of 2027, MBA students are not eligible to apply.',
    'Open to MBA students graduating in 2027. Class of 2027 MBA students are not eligible to apply.',
])
def test_a_denial_with_a_leading_qualifier_naming_2027_still_denies_2027(text):
    assert p.collection_reason(job(text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('text', [
    'We cannot hire MBAs, but MBA students graduating in 2027 can subscribe to our newsletter.',
    'We do not hire MBAs, but MBA candidates can join our networking events.',
    'We cannot hire MBAs, but MBA students are welcome to follow us on social media.',
])
def test_a_contrast_that_does_not_admit_applicants_keeps_a_global_mba_denial_active(text):
    assert p.collection_reason(job(title='Product Manager (MBA)', text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('text', [
    'Not open to MBA students, but MBA students graduating in 2027 are welcome to apply.',
    'Not open to MBA students, but open to MBA students graduating in 2027.',
    'We cannot hire MBAs, but MBA students graduating in 2027 may apply.',
])
def test_a_contrast_that_admits_the_2027_class_still_relaxes_a_yearless_denial(text):
    assert p.collection_reason(job(title='Product Manager (MBA)', text=text)) == ''


# Codex follow-up review 5622469373 of PR 53 (cycle 7).
@pytest.mark.parametrize('text', [
    'Open to MBA students graduating in 2027. For the class of 2026, this role is not open to MBA students.',
    'Open to MBA students graduating in 2027. For the class of 2026, we are not recruiting MBA students.',
    'Open to MBA students graduating in 2027. For the class of 2026, MBA students are not eligible to apply.',
    'For our 2027 program, MBA students graduating in 2026 are not eligible to apply. Open to MBA students graduating in 2027.',
    'For our 2027 program, this role is not open to MBA students graduating in 2026. Open to MBA students graduating in 2027.',
    'Open to MBA students graduating in 2027 and not open to MBA students graduating in 2026.',
])
def test_a_denial_is_bound_to_its_own_class_in_either_word_order(text):
    assert p.collection_reason(job(text=text)) == ''


@pytest.mark.parametrize('text', [
    'Open to MBA students graduating in 2027. For the class of 2027, this role is not open to MBA students.',
    'Open to MBA students graduating in 2027. For the class of 2027, we are not recruiting MBA students.',
    'For our 2027 program, MBA students graduating in 2027 are not eligible to apply. Open to MBA students graduating in 2027.',
])
def test_a_leading_qualifier_naming_2027_still_denies_2027_in_either_word_order(text):
    assert p.collection_reason(job(text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('text', [
    'We cannot hire MBAs, but we are not recruiting MBA students graduating in 2026.',
    'We cannot hire MBAs, but we are not recruiting MBA students.',
    'We do not hire MBAs, but MBA students are not welcome to apply.',
])
def test_a_negative_or_other_class_contrast_does_not_lift_a_global_denial(text):
    assert p.collection_reason(job(title='Product Manager (MBA)', text=text)) == 'not_mba_2027'


def test_the_valid_welcome_to_apply_contrast_still_lifts_a_yearless_denial():
    text = 'We cannot hire MBAs, but MBA students graduating in 2027 are welcome to apply.'
    assert p.collection_reason(job(title='Product Manager (MBA)', text=text)) == ''


def test_a_contrast_that_admits_only_another_class_is_dropped_as_the_wrong_class():
    text = 'We cannot hire MBAs, but MBA students graduating in 2026 are welcome to apply.'
    assert p.collection_reason(job(title='Product Manager (MBA)', text=text)) == 'mba_other_class_year'


# Codex follow-up review 5622912780 of PR 53 (cycle 8).
@pytest.mark.parametrize('text', [
    'Open to MBA students graduating in 2027. For 2026 MBA graduates, this role is not open to MBA students.',
    'Open to MBA students graduating in 2027. For the MBA class of 2026, this role is not open to MBA students.',
    'Open to MBA students graduating in 2027. For 2026 MBA graduates, MBA students are not eligible to apply.',
    'MBA students graduating in 2026 are not eligible to apply for the 2027 program. Open to MBA students graduating in 2027.',
    'MBA students graduating in 2026 are not eligible to apply for the 2027 cohort. Open to MBA students graduating in 2027.',
])
def test_a_class_qualifier_that_names_mbas_or_follows_the_subject_is_still_the_denied_class(text):
    assert p.collection_reason(job(text=text)) == ''


@pytest.mark.parametrize('text', [
    'Open to MBA students graduating in 2027. For 2027 MBA graduates, this role is not open to MBA students.',
    'Open to MBA students graduating in 2027. For the MBA class of 2027, this role is not open to MBA students.',
    'MBA students graduating in 2027 are not eligible to apply for the 2026 program. Open to MBA students graduating in 2027.',
])
def test_the_same_shapes_naming_2027_as_the_class_still_deny_2027(text):
    assert p.collection_reason(job(text=text)) == 'not_mba_2027'


@pytest.mark.parametrize('text,expected', [
    ('We cannot hire MBAs, but MBA students graduating in 2026 are welcome to apply for the 2027 program.', 'mba_other_class_year'),
    ('We cannot hire MBAs, but MBA students graduating in 2027 are welcome to apply for the 2026 program.', ''),
    ('Open to MBA students graduating in 2026 for the 2027 program.', 'mba_other_class_year'),
    ('Open to MBA students graduating in 2026 or 2027 for the 2028 program.', ''),
    ('Join our 2027 program, open to MBA students.', ''),
])
def test_an_explicit_graduating_class_keeps_the_program_date_out_of_the_applicant_years(text, expected):
    assert p.collection_reason(job(title='Product Manager (MBA)', text=text)) == expected
