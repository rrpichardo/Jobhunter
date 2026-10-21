"""Build JobHunter_Parameters.xlsx from the real code. Run from the repo root with the repo on PYTHONPATH.

Every number in the 'Today' column that exists as a constant is read from the code and compared with the text written
here; the script stops if they ever disagree. The 'Try it' sheet runs example inputs through the real functions.
"""
import sys
from datetime import date, datetime, timezone

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from jobhunter import (ai_queue, allowance, artifacts, gmail_alerts, hn_hiring, linkedin_cards, newsletter, post_facts,
                       postings, run_window, sheet_journal, sheet_records, social_collect)
from scripts import field_audit, linkedin_collect, sheets_sync, source_probe, x_collect

OUT = sys.argv[1]
TODAY = date.today().isoformat()
F = 'Arial'

H = Font(name=F, bold=True, color='FFFFFF', size=10)
HF = PatternFill('solid', fgColor='1F3864')
B = Font(name=F, size=10)
BB = Font(name=F, size=10, bold=True)
YEL = PatternFill('solid', fgColor='FFFF00')
RISK = {'Low': PatternFill('solid', fgColor='E2EFDA'), 'Medium': PatternFill('solid', fgColor='FFF2CC'),
        'High': PatternFill('solid', fgColor='F8CBAD')}
thin = Side(style='thin', color='BFBFBF')
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical='top')

COLS = ['Group', 'Setting', 'Today', 'In plain words', 'If you change it', 'Risk', 'Who changes it', 'Where (for Claude)',
        'Checked in the code', 'YOUR DECISION', 'New value / your note']
WIDTHS = [18, 30, 26, 56, 44, 9, 22, 36, 26, 15, 30]

SHEETS = []   # (title, intro, rows)
CHECKS = []   # (description, ok)


def row(group, setting, today, plain, change, risk, who, where, check=None):
    """check = (actual_value_from_code, token_that_must_appear_in_today)."""
    checked = ''
    if check is not None:
        actual, token = check
        assert str(actual) == str(token) or str(token) in str(actual), f'{setting}: code says {actual!r}, expected {token!r}'
        checked = f'OK: code says {actual}'
        CHECKS.append((setting, True))
    return [group, setting, today, plain, change, risk, who, where, checked]


EDIT_FILE = 'You, in a text file'
ASK = 'Ask Claude (then Codex reviews)'
CODE = 'Fixed in the program; ask Claude'
YOU_SHEET = 'You, in the Sheet'


# ------------------------------------------------------------------------------------------------ 1 Runs
runs = [
    row('Look-back window', 'Manual run look-back', f'{run_window.MANUAL_DAYS} days',
        'A run you start by hand looks back this far for jobs. Used for the first big pull and for catch-ups.',
        'Higher: more (older) jobs and a longer run. Lower: fewer old jobs.', 'Low', ASK,
        '`MANUAL_DAYS` in jobhunter/run_window.py', (run_window.MANUAL_DAYS, 28)),
    row('Look-back window', 'Daily run look-back', f'{run_window.DAILY_DAYS} days',
        'The scheduled daily routine looks back this far. It overlaps the days already covered on purpose, so a missed day is not lost.',
        'Higher: more overlap and slightly more work. Lower: a missed day could lose jobs. Must stay larger than the longest accepted gap below.',
        'Medium', ASK, '`DAILY_DAYS` in jobhunter/run_window.py', (run_window.DAILY_DAYS, 3)),
    row('Look-back window', 'Longest gap a daily run accepts', '2 days 6 hours since the last complete run started',
        'If the last complete run started longer ago than this (or there never was one), the daily run refuses to run and asks for a manual run, so nothing is skipped silently.',
        'Higher: tolerates longer outages but risks jobs falling between runs. Lower: refuses more often.', 'Medium', ASK,
        '`MAX_GAP` in jobhunter/run_window.py', (str(run_window.MAX_GAP), '2 days')),
    row('Look-back window', 'Which runs count for that gap rule', ' / '.join(sorted(run_window.COMPLETE)),
        'Only runs that finished with these statuses count. A run that failed or stopped halfway does not.',
        'Rarely changed.', 'Low', CODE, '`COMPLETE` in jobhunter/run_window.py', (' / '.join(sorted(run_window.COMPLETE)), 'complete')),
    row('Look-back window', 'Default window for individual tools', f'{source_probe.LOOKBACK_DAYS} days',
        'What the collectors use when no window is given. The routine always passes the window, so this matters only for runs started by hand.',
        'Several tools carry their own copy; change them together.', 'Low', ASK, '`LOOKBACK_DAYS` in scripts/source_probe.py and scripts/hn_hiring.py',
        (source_probe.LOOKBACK_DAYS, 28)),
    row('Look-back window', 'A job with no posting date', 'Kept',
        'If a source gives no usable date, the job is kept (and the date shows as "not provided by source"). It is never dropped just because the date is missing.',
        'Not adjustable.', 'Low', CODE, '`within_lookback` in jobhunter/postings.py'),
    row('Schedule', 'Daily routine time', '06:07 New York time (not created yet)',
        'The plan for the daily routine called "JobHunter Daily". It does not exist until you approve it (decision A3).',
        'Tell Claude the time you want.', 'Low', 'Ask Claude', 'docs/ROUTINE_PROMPT.md'),
    row('X / LinkedIn allowance', 'Live sessions per source per day', '1 per New York calendar day',
        'X and LinkedIn are each read once per New York day. The day is reserved in the Sheet before any request and is spent even if the run fails, so a failed run is never retried the same day.',
        'This protects the accounts. Do not raise it.', 'High', CODE, 'jobhunter/allowance.py'),
    row('Hacker News', 'Monthly "Who is hiring?" threads read', 'Threads that can still hold comments inside the window (look-back + 32 days)',
        'The tool reads the current and, if needed, the previous month\'s thread.', 'Not adjustable except through the window.', 'Low', CODE,
        '`select_threads` in jobhunter/hn_hiring.py'),
    row('Hacker News', 'Threads listed per search', '12',
        'How many recent "Who is hiring?" posts the search asks for.', 'Rarely changed.', 'Low', CODE, '`SEARCH_URL` in jobhunter/hn_hiring.py',
        ('hitsPerPage=12' in hn_hiring.SEARCH_URL, 'True') if False else None),
]

# ------------------------------------------------------------------------------------------------ 2 Roles
fam = [(name, pat.pattern) for name, pat in postings.ROLE_FAMILIES]
roles = [
    row('Roles collected', 'Product management', 'Product manager, product lead, group product manager, head of product, director of product, VP of product (also "VP, Product" and a bare "PM")',
        'A job title must match one of the families to be considered at all.', 'Add or remove titles: tell Claude the exact words.', 'Medium', ASK,
        '`PM_TITLE_TERMS` in jobhunter/postings.py'),
    row('Roles collected', 'Chief of Staff', 'Chief of staff', 'Counts as a role we collect.', 'As above.', 'Medium', ASK, '`ROLE_FAMILIES` in jobhunter/postings.py'),
    row('Roles collected', 'Leadership program', 'Leadership (development) program; MBA or management development / rotation program',
        'Includes MBA rotational programs. Still has to pass the MBA 2027 rule.', 'As above.', 'Medium', ASK, '`ROLE_FAMILIES`'),
    row('Roles collected', 'Strategy', 'Strategy manager / lead / director; manager, director, head or VP of (corporate or business) strategy',
        'Counts as a role we collect.', 'As above.', 'Medium', ASK, '`ROLE_FAMILIES`'),
    row('Roles collected', 'Entrepreneurship', 'Entrepreneur in residence; founder in residence', 'Counts as a role we collect.', 'As above.', 'Medium', ASK, '`ROLE_FAMILIES`'),
    row('Roles collected', 'Project management', 'Project manager; project management lead; project director', 'Counts as a role we collect.', 'As above.', 'Medium', ASK, '`ROLE_FAMILIES`'),
    row('Roles collected', 'Forward-deployed strategy', 'Forward-Deployed AI Strategist and name variants; AI Deployment Strategist; AI Implementation Strategist; Deployment Strategist',
        'Any title naming an engineer or developer (Engineer, Eng., Dev, SDE, SWE, "Software Development") is never accepted in this family.',
        'As above.', 'Medium', ASK, '`ROLE_FAMILIES`, `FORWARD_DEPLOYED_ENGINEER`'),
    row('Roles dropped', 'Always dropped', 'Intern, internship, summer associate, product marketing, product designer, product communications',
        'These titles are thrown out even if they contain a word from the list above. "BizOps" is out of scope (your decision).',
        'Add or remove words: tell Claude.', 'Medium', ASK, '`ROLE_EXCLUSIONS` in jobhunter/postings.py'),
    row('Roles dropped', 'Plain "program manager"', 'Not collected', 'Program manager is not one of the families.', 'Tell Claude if you want it.', 'Medium', ASK, '`EXCLUDED_TITLE`'),
    row('Roles dropped', 'Plural titles ("Product Managers")', 'Not matched (your decision A13 is open)',
        'The singular is matched, the plural is not. This also keeps such posts from being sent to the AI reader on Hacker News.',
        'Decision A13: recommended yes, accept plurals.', 'Medium', ASK, '`PM_TITLE` in jobhunter/postings.py'),
    row('Roles dropped', 'AI wording in the title or text', 'Used only to order jobs, not to filter',
        'Words such as AI, ML, LLM, GenAI, agents move a product-manager job earlier in the list. A job without them is still collected.',
        'Not a filter.', 'Low', CODE, '`AI_TERMS`, `collection_title_priority` in jobhunter/postings.py'),
]

# ------------------------------------------------------------------------------------------------ 3 MBA 2027
mba = [
    row('The rule', 'Collect only roles meant for MBA graduates of 2027', 'On (your decision, October 21). There is no switch.',
        'A job is kept only if its own text says who may apply: MBA students or graduates of 2027. The rule is applied after the role and place checks and before the pay check.',
        'To turn it off or loosen it, tell Claude; it needs a code change and a Codex review.', 'High', ASK, '`mba_class_evidence`, `collection_reason` in jobhunter/postings.py'),
    row('The rule', 'Job seniority', 'Ignored', 'A Senior Product Manager role open to MBAs graduating in 2027 passes; a plain one does not. Years of experience do not matter.',
        'Not adjustable.', 'Low', CODE, '`mba_class_evidence`'),
    row('What counts', 'Applicant statements', 'e.g. "open to MBA students graduating in spring 2027", "we are recruiting MBA candidates", "this role is for MBA graduates", "applicants must be current MBA students"',
        'Words like open to / role is for / recruiting / hiring / seeking, followed by only applicant words (current, recent, graduating, a year, and/or), then MBA students / graduates / candidates / hires / associates.',
        'More lead words or wordings: tell Claude with an example.', 'Medium', ASK, '`MBA_APPLICANT`, `_APPLICANT_LEAD`, `_APPLICANT_WORDS`'),
    row('What counts', 'Noun-first eligibility', 'e.g. "MBA students graduating in May 2027 are eligible / encouraged / welcome to apply", "... should apply"',
        'Also counts. Customer wording ("MBA students use our app and are eligible for a discount") does not.', 'As above.', 'Medium', ASK, '`MBA_SUBJECT_FIRST`'),
    row('What counts', 'Named MBA programs and classes', 'e.g. "MBA Leadership Development Program", "MBA Class of 2027", "MBA Grad 2027", "MBA campus recruiting", "post-MBA role"',
        'A named program or class counts without a lead word.', 'As above.', 'Medium', ASK, '`MBA_STANDALONE`'),
    row('What counts', 'MBA marker in a job title', '"(MBA)" or "(Full-Time MBA)" in the TITLE; "MBA graduates" etc. in the title',
        'In a title, "(MBA)" marks the program. In a description the same words are usually a degree requirement ("Master of Business Administration (MBA) or JD"), so it is read in titles only.',
        'As above.', 'Medium', ASK, '`MBA_TITLE_MARKER`, `MBA_PEOPLE_IN_TITLE`'),
    row('What does NOT count', 'MBA as a qualification', '"MBA preferred", "MBA or equivalent experience", "MBA or advanced degree", "MBA is a plus"',
        'These describe what the employer likes, not who the job is for. Nearly every MBA mention on the company boards is one of these.', 'Not adjustable.', 'Low', CODE, '`mba_class_evidence`'),
    row('What does NOT count', 'MBA students as customers', '"products for MBA students", "tools for MBA candidates"',
        'A verb phrase between the lead word and the MBA words (for example "a PM to build products for") means the MBA students are the users, not the applicants.',
        'Not adjustable.', 'Low', CODE, '`_APPLICANT_WORDS`'),
    row('What does NOT count', 'A denied statement', '"This role is NOT open to MBA students ...", "we do not recruit MBA candidates", "open to all except MBA students"',
        'A denial in the same clause cancels the statement. A "not" in an earlier clause ("Experience is not required, open to MBA students ...") does not.',
        'Not adjustable.', 'Low', CODE, '`_negated`, `_CLAUSE_BREAK`'),
    row('Which year', 'The class year', '2027',
        'The year must come from the same statement: graduating in / class of / cohort / program year / start year. A launch date, application window or fiscal year in the same sentence is ignored. A list or range counts every year in it ("May 2026 or May 2027", "2026 to 2028"). In a title every year is the program year.',
        'The year 2027 is written in the code; tell Claude to change it.', 'Medium', ASK, '`_class_years`, `_graduation_years`'),
    row('Which year', 'MBA wording with another class year', 'Dropped as "mba_other_class_year"', 'For example "graduating in spring 2028 only".', 'Not adjustable.', 'Low', CODE, '`collection_reason`'),
    row('Which year', 'Posting for the 2027 graduating class but no MBA', 'Dropped as "class_2027_without_mba" (decision A23 is open)',
        'For example Databricks "Associate Product Manager, New Grad (2027 Start)": it asks for a bachelor\'s or master\'s in computer science. The number dropped is shown in every run.',
        'Decision A23: recommended keep these out.', 'Medium', ASK, '`CLASS_2027_ONLY`'),
    row('What you see', 'Evidence in the Sheet', 'Row detail "MBA 2027 evidence: ..."', 'A kept row quotes the words that qualified it, so you can check it.', 'Not adjustable.', 'Low', CODE, '`to_row` in jobhunter/postings.py'),
    row('What you see', 'Roles outside the title list that are clearly for MBA 2027', 'Dropped today (decision A24 is open)',
        'Example: Sierra "Strategist, Agent Development (MBA Grad 2027)". The role-title check comes first, so it is dropped.', 'Decision A24: recommended accept any business role that clearly says MBA 2027.', 'Medium', ASK, '`collection_reason`'),
    row('What you see', 'Sources that show only a short snippet', 'Mostly dropped',
        'Job-site search results, LinkedIn job cards and plain newsletter lines rarely contain the MBA wording, so they will mostly be dropped until their reader quotes the sentence that says who the role is for.',
        'See decision A25: add company MBA programs and school sites as sources.', 'Medium', 'You decide (A25)', 'docs/PARAMETERS.md'),
]

# ------------------------------------------------------------------------------------------------ 4 Places
places = [
    row('Accepted', 'United States', 'Accepted', 'A US city, state or "United States / USA" in the location. A US city plus a foreign country on the same line also counts as US.',
        'Not adjustable except through the word lists.', 'Medium', ASK, '`US_TERMS`, `LOCATION_US_CODE`, `US_STATE_NAME` in jobhunter/postings.py'),
    row('Accepted', 'Latin America: remote jobs', 'Accepted with the lower pay floor ($70,000)', 'If the source says the job is remote (or the place text says remote) and the place is Latin American.',
        'Tell Claude to add or remove countries.', 'Medium', ASK, '`LATIN_AMERICA`, `collection_region`'),
    row('Accepted', 'Latin America: on-site jobs', 'Only Colombia and the Dominican Republic', 'An on-site job in another Latin American country (Brazil, Argentina, Mexico ...) is dropped.',
        'As above.', 'Medium', ASK, '`ONSITE_COUNTRIES`'),
    row('Kept and flagged', 'Place unclear', 'Kept, flagged "verify permitted work location"', 'Text like "Remote", a city name with no country, or "Sao Paulo, Brazil" (a city plus country) is unclear. The row says to check the place and which pay floor applies.',
        'Not adjustable.', 'Low', CODE, '`collection_region` returns "unresolved"'),
    row('Dropped', 'Clearly elsewhere', 'Dropped', 'Canada, Europe, India, Singapore, Australia, etc. (about 100 country and city words).', 'Tell Claude to move a place.', 'Medium', ASK, '`NON_US`'),
    row('Detail', 'Short codes that clash', ', '.join(sorted(postings.AMBIGUOUS_REGIONAL_CODES)), '"CO" is Colorado or Colombia, "PA" Pennsylvania or Panama, "AR" Arkansas or Argentina, "DC" Washington DC or Bogotá D.C. (Colombia). They are not treated as proof of a country on their own.',
        'Not adjustable.', 'Low', CODE, '`AMBIGUOUS_REGIONAL_CODES`', (', '.join(sorted(postings.AMBIGUOUS_REGIONAL_CODES)), 'AR, CO, DC, PA')),
    row('Detail', '"Remote" alone', 'Does not prove a country', 'A job that only says "Remote" is treated as unclear, not as US.', 'Not adjustable.', 'Low', CODE, '`REMOTE_TERMS`'),
]

# ------------------------------------------------------------------------------------------------ 5 Pay
us_floor = postings.salary_preference(postings.Posting('x:1', 'x', 'A', 'Product Manager', 'United States', 't', 'https://a.example/1',
                                                       '2026-10-21T00:00:00+00:00', salary='USD 140,000 per year'))
assert us_floor == ('satisfied', 140000), us_floor
below = postings.salary_preference(postings.Posting('x:1', 'x', 'A', 'Product Manager', 'United States', 't', 'https://a.example/1',
                                                    '2026-10-21T00:00:00+00:00', salary='USD 139,999 per year'))
assert below == ('below floor', 140000), below
latam = postings.salary_preference(postings.Posting('x:1', 'x', 'A', 'Product Manager', 'Colombia', 't', 'https://a.example/1',
                                                    '2026-10-21T00:00:00+00:00', salary='USD 70,000 per year'))
assert latam == ('satisfied', 70000), latam
pay = [
    row('Floors', 'Pay floor, United States jobs', '$140,000 a year', 'A job whose TOP pay is below this is dropped. A range counts if its top reaches the floor.',
        'Lower the floor: more jobs. Raise it: fewer.', 'Medium', ASK, 'the number 140,000 in `salary_preference` / `collection_stub_match`, jobhunter/postings.py', (us_floor[1], '140')),
    row('Floors', 'Pay floor, Latin America jobs', '$70,000 a year', 'Same rule for Latin American jobs.', 'As above.', 'Medium', ASK, 'the number 70,000 in the same functions', (latam[1], '70')),
    row('Floors', 'Absolute minimum when the place is unclear', f'${postings.MIN_REGIONAL_ANNUAL_USD:,} a year', 'Anything clearly under this is dropped whatever the place.',
        'As above.', 'Medium', ASK, '`MIN_REGIONAL_ANNUAL_USD` in jobhunter/postings.py', (postings.MIN_REGIONAL_ANNUAL_USD, '70,000') if False else (f'{postings.MIN_REGIONAL_ANNUAL_USD:,}', '70,000')),
    row('Floors', 'Pay missing or not clearly yearly US dollars', 'Kept', 'Hourly, monthly, another currency, on-target earnings, total compensation, bonus or equity-only pay is NOT compared with the floor. The row is kept and says "Check first: verify annual USD base salary reaches ...".',
        'Not adjustable.', 'Low', CODE, '`annual_usd_salary_ceiling`'),
    row('Where pay comes from', 'Greenhouse and Ashby pay fields', 'Read (fixed October 21)', 'Greenhouse (`pay_input_ranges`) and Ashby (`compensation`) publish pay separately from the description. It was never asked for, so these rows had a blank Salary. Tiers of one posting (zones, states) become one range.',
        'Not adjustable.', 'Low', CODE, '`greenhouse_pay`, `ashby_pay`; URLs in scripts/source_probe.py'),
    row('Where pay comes from', 'A pay label that is not yearly base pay', 'Kept with its own unit word, treated as unresolved',
        'Labels like "Monthly Salary", "Annual Bonus", "Annual Total Compensation", "Hourly Rate", "OTE Range" are written as "month", "bonus", "total compensation", "hour", "OTE" and are not compared with the floor. A blurb that says "per month / paid monthly" also sets the unit; the generic sales sentence in Anthropic\'s blurb does not.',
        'Not adjustable.', 'Low', CODE, '`_pay_unit`, `_blurb_period`'),
    row('Where pay comes from', 'A range written in the posting text', 'Read only when clearly yearly US base pay',
        'Needs two amounts of at least $30,000; a base-pay word (salary, base pay, pay range) in the same sentence; and nothing in that sentence that makes it total compensation, OTE, bonus, equity, commission, monthly/weekly/daily/hourly, or another currency (before or after the range, e.g. "(CAD)"). "Plus bonus" on top of base is fine. Several location tiers are merged.',
        'Tell Claude to adjust, with an example.', 'Medium', ASK, '`salary_from_text`'),
    row('Open decision', 'Pay written like $190k-$220k in X and Hacker News posts', 'Not read (decision A17 open)', 'Job boards are handled; social posts are not. They are kept as "pay unresolved".',
        'Decision A17: recommended yes.', 'Medium', ASK, '`annual_usd_salary_ceiling`'),
]

# ------------------------------------------------------------------------------------------------ 6 Sources
reg = yaml.safe_load(open('sources/v0_sources.yaml', encoding='utf-8'))
src = []
for kind, boards in reg['boards'].items():
    for b in boards:
        src.append(row('Company boards read directly (24)', f'{b["company"]} ({kind})', f'{kind}: {b["board"]}',
                       f'Registry tag: {b["tag"]} (sets the "Rank (prelim)" in the Sheet: ai = 1, big tech = 2, other = 3).',
                       'Remove or add a company: edit sources/v0_sources.yaml yourself, or tell Claude.', 'Low', EDIT_FILE, 'sources/v0_sources.yaml'))
assert sum(len(v) for v in reg['boards'].values()) == 24
for a in reg['aggregators']:
    src.append(row('Public job sites (6)', a['id'], a['kind'], 'Public job site read once per run.', 'Edit sources/v0_sources.yaml.', 'Low', EDIT_FILE, 'sources/v0_sources.yaml'))
for a in reg['keyed_apis']:
    src.append(row('Keyed services (2)', a['id'], 'needs a key in the environment', 'One request per run. The free plan allows about 200 requests a month for JSearch; no new spending is authorised, so no extra pages.',
                   'More pages use more of the monthly quota (decided: none).', 'Medium', ASK, 'sources/v0_sources.yaml'))
for a in reg['detail_sources']:
    src.append(row('Pages opened one by one (10)', a['id'], a['kind'], 'A listing page, then each shortlisted job\'s own page for its description (polite, capped).', 'Edit sources/v0_sources.yaml.', 'Low', EDIT_FILE, 'sources/v0_sources.yaml'))
src.append(row('Other', 'Hacker News "Who is hiring?"', 'monthly threads', 'Read by the AI, then checked by code.', '', 'Low', ASK, 'jobhunter/hn_hiring.py'))
src.append(row('Other', 'Ali Rohde Jobs newsletter', newsletter.FEEDS['alirohde-rss']['url'] + f' (first {newsletter.MAX_ENTRIES} entries)', f'Weekly; the first {newsletter.MAX_ENTRIES} entries of the feed are read.', '', 'Low', ASK, 'jobhunter/newsletter.py', (newsletter.MAX_ENTRIES, 12)))
for n in reg['needs_setup']:
    src.append(row('Waiting for something from you', n['id'], 'needs setup', n['action'], 'See your tasks (B1, B2, B3, B9, B10, B11) in START_HERE.', 'Low', 'You', 'sources/v0_sources.yaml'))
src += [
    row('Politeness and safety', 'Job pages opened per page-source per run', str(source_probe.DETAIL_SAFETY_STOP), 'A safety stop. If hit, the run says "details_skipped".', 'Higher: more pages per run; lower: fewer. Keep modest.', 'Medium', ASK,
        '`DETAIL_SAFETY_STOP` in scripts/source_probe.py (or --detail-safety-stop)', (source_probe.DETAIL_SAFETY_STOP, 300)),
    row('Politeness and safety', 'Pages per paged service per run', str(source_probe.PAGE_SAFETY_STOP), 'A safety stop. Only The Muse and Jobicy are paged. If hit, the run says "paging_stopped".', 'As above.', 'Medium', ASK,
        '`PAGE_SAFETY_STOP` in scripts/source_probe.py', (source_probe.PAGE_SAFETY_STOP, 100)),
    row('Politeness and safety', 'Paged services', ', '.join(sorted(source_probe.PAGED_KINDS)), 'The only services read page after page.', 'As above.', 'Low', CODE, '`PAGED_KINDS`', (', '.join(sorted(source_probe.PAGED_KINDS)), 'jobicy, themuse')),
    row('Politeness and safety', 'Pause between ordinary requests', '1.0 second', 'Politeness toward each site.', 'Shorter: faster but ruder and more likely to be blocked.', 'Medium', ASK, '`--delay` in scripts/source_probe.py'),
    row('Politeness and safety', 'Time allowed for one request', '30 seconds (20 for the older company-board tool)', 'Then the request is recorded as a timeout.', 'Rarely changed.', 'Low', CODE, 'scripts/source_probe.py, jobhunter/fetch.py'),
    row('Politeness and safety', 'Retries', 'None in the probe (one attempt); 3 attempts in the older board tool', 'The probe never retries, so a blocked site is recorded, not hammered.', 'Not adjustable.', 'Low', CODE, 'scripts/source_probe.py'),
    row('Politeness and safety', 'Largest answer accepted', f'{source_probe.MAX_BYTES // (1024 * 1024)} MiB', 'Safety stop.', 'Rarely changed.', 'Low', CODE, '`MAX_BYTES` in scripts/source_probe.py', (source_probe.MAX_BYTES // (1024 * 1024), 40)),
    row('Politeness and safety', 'Replies treated as "blocked"', ', '.join(str(c) for c in sorted(source_probe.BLOCKED)), 'These HTTP codes mean the site refused us; the source is recorded as blocked.', 'Not adjustable.', 'Low', CODE, '`BLOCKED`', (', '.join(str(c) for c in sorted(source_probe.BLOCKED)), '401, 403, 406, 429')),
    row('Politeness and safety', 'Name we announce ourselves with', source_probe.USER_AGENT, 'Sent to job sites so they can see who is reading.', 'Not adjustable.', 'Low', CODE, '`USER_AGENT`'),
]

# ------------------------------------------------------------------------------------------------ 7 X and LinkedIn
sq = yaml.safe_load(open('sources/social_queries.yaml', encoding='utf-8'))
LX = social_collect.LIMITS
social = []
for key, label in (('x-twscrape', 'X search'), ('linkedin-login', 'LinkedIn hiring-post search'), ('linkedin-login-jobs', 'LinkedIn job-listing search')):
    for i, q in enumerate(sq[key], 1):
        social.append(row('Search wording (sources/social_queries.yaml)', f'{label} {i}', q,
                          'You can edit this line yourself. Every quoted phrase must be a role the program collects (a test checks it), so a search never wastes the daily allowance.',
                          'Change the words in the file; ask Claude to run the tests.', 'Medium', EDIT_FILE, 'sources/social_queries.yaml'))
social += [
    row('X limits', 'X searches per run', str(LX['x-twscrape']['queries']), 'The most X searches in the one daily session.', 'Raising raises the risk the account is restricted.', 'High', ASK, "`LIMITS['x-twscrape']['queries']` in jobhunter/social_collect.py", (LX['x-twscrape']['queries'], 10)),
    row('X limits', 'X posts kept per run', str(LX['x-twscrape']['posts']), 'Stops collecting at this many posts.', 'Higher: more to read, more risk.', 'High', ASK, "`LIMITS['x-twscrape']['posts']`", (LX['x-twscrape']['posts'], 200)),
    row('X limits', 'X posts kept per search', str(LX['x-twscrape']['per_query']), 'Stops one busy search using the whole 200.', 'As above.', 'High', ASK, "`LIMITS['x-twscrape']['per_query']`", (LX['x-twscrape']['per_query'], 40)),
    row('X limits', 'Result pages per X search', str(x_collect.MAX_PAGES), 'A hard stop on paging.', 'As above.', 'High', ASK, '`MAX_PAGES` in scripts/x_collect.py', (x_collect.MAX_PAGES, 10)),
    row('LinkedIn limits', 'Hiring-post searches per run', str(LX['linkedin-login']['post_searches']), 'In the one LinkedIn session.', 'Raising raises the risk the account is restricted.', 'High', ASK, "`LIMITS['linkedin-login']['post_searches']`", (LX['linkedin-login']['post_searches'], 5)),
    row('LinkedIn limits', 'Job-listing searches per run', str(LX['linkedin-login']['job_searches']), 'Same session and allowance as the posts.', 'As above.', 'High', ASK, "`LIMITS['linkedin-login']['job_searches']`", (LX['linkedin-login']['job_searches'], 5)),
    row('LinkedIn limits', 'Posts kept per run / per search', f"{LX['linkedin-login']['posts']} / {LX['linkedin-login']['per_query']}", 'Stops collecting at these numbers.', 'As above.', 'High', ASK, "`LIMITS['linkedin-login']['posts']`, `['per_query']`", (f"{LX['linkedin-login']['posts']} / {LX['linkedin-login']['per_query']}", '100 / 30')),
    row('LinkedIn limits', 'Job cards kept per run / per search', f"{LX['linkedin-login']['jobs']} / {LX['linkedin-login']['job_per_query']}", 'Stops collecting job cards at these numbers.', 'As above.', 'High', ASK, "`LIMITS['linkedin-login']['jobs']`, `['job_per_query']`", (f"{LX['linkedin-login']['jobs']} / {LX['linkedin-login']['job_per_query']}", '125 / 30')),
    row('LinkedIn limits', '"Detail views" per run', str(LX['linkedin-login']['detail_views']), 'NOT USED today: the number exists but no code opens detail pages. Changing it does nothing.', 'No effect until detail views are built.', 'Low', CODE, "`LIMITS['linkedin-login']['detail_views']`", (LX['linkedin-login']['detail_views'], 50)),
    row('Pace', 'Pause between searches', f'random {social_collect.DELAY_SECONDS[0]:.0f} to {social_collect.DELAY_SECONDS[1]:.0f} seconds', 'Makes the pace look human and gentle.', 'Shorter pauses raise the risk of a restriction.', 'High', ASK, '`DELAY_SECONDS` in jobhunter/social_collect.py', (social_collect.DELAY_SECONDS, '(3.0, 9.0)')),
    row('Pace', 'Page scrolls per LinkedIn results page', str(linkedin_collect.SCROLLS), 'How far the page is scrolled so more results load.', '', 'Medium', ASK, '`SCROLLS` in scripts/linkedin_collect.py', (linkedin_collect.SCROLLS, 4)),
    row('Pace', '"See more" expansions per LinkedIn page', f'up to {linkedin_collect.MAX_EXPANDS}', 'Opens cut-off posts to read their full text.', '', 'Medium', ASK, '`MAX_EXPANDS`', (linkedin_collect.MAX_EXPANDS, 40)),
    row('Pace', 'Wait for LinkedIn results to appear', f'{linkedin_collect.READY_SECONDS} seconds', 'Then the page is read as it is.', '', 'Low', ASK, '`READY_SECONDS`', (linkedin_collect.READY_SECONDS, 25)),
    row('Pace', 'Longest LinkedIn card read', f'{linkedin_cards.MAX_CARD_CHARS:,} characters', 'Longer cards are shortened before the AI reads them.', '', 'Low', CODE, '`MAX_CARD_CHARS` in jobhunter/linkedin_cards.py', (f'{linkedin_cards.MAX_CARD_CHARS:,}', '6,000')),
    row('What the program never does', 'Actions on X and LinkedIn', 'Read only', 'No login typing, posting, liking, following, messaging or applying. LinkedIn is on hold (decision A18).', 'Not adjustable.', 'High', CODE, 'docs/PLAN.md'),
]

# ------------------------------------------------------------------------------------------------ 8 AI reading
ai = [
    row('Model', 'Model that reads free text', 'Haiku (accepted October 19)', 'Copies title, company, place, pay and one short quote out of posts. Code then rejects any value that is not word for word in the post.', 'Switching to Sonnet costs more; a test showed 100 of 100 agreed.', 'Medium', 'Ask Claude', 'docs/ROUTINE_PROMPT.md'),
    row('Model', 'What the reader must quote', 'The sentence that says who the role is for', 'Because the MBA 2027 rule reads the quote and title, the reader is told to quote the sentence "open to MBA students graduating in ..." when the post has one. It must copy it exactly.', 'Not adjustable except by wording.', 'Medium', ASK, 'docs/ROUTINE_PROMPT.md'),
    row('Limits', 'Items handed to the AI per run', str(ai_queue.WORK_SAFETY_STOP), 'Safety stop; the rest wait for the next run.', '', 'Low', ASK, '`WORK_SAFETY_STOP` in jobhunter/ai_queue.py', (ai_queue.WORK_SAFETY_STOP, 1000)),
    row('Limits', 'Size of the file handed to the AI', f'{ai_queue.WORK_BYTE_STOP // (1024 * 1024)} MiB', 'The rest stays pending.', '', 'Low', ASK, '`WORK_BYTE_STOP`', (ai_queue.WORK_BYTE_STOP // (1024 * 1024), 3)),
    row('Limits', 'Longest post read', f'{post_facts.MAX_POST_CHARS:,} characters (24,000 for a newsletter edition)', 'A longer post is counted as unreadable, not read.', '', 'Low', ASK, '`MAX_POST_CHARS` in jobhunter/post_facts.py', (f'{post_facts.MAX_POST_CHARS:,}', '10,000')),
    row('Limits', 'Length of the quote kept for each job', '300 characters (other fields up to 1,000)', 'A longer quote makes the fact rejected (it is not cut).', '', 'Low', CODE, 'jobhunter/post_facts.py'),
    row('Limits', 'Hacker News comments collected per run', f'{hn_hiring.CANDIDATE_SAFETY_STOP:,}', 'Safety stop.', '', 'Low', ASK, '`CANDIDATE_SAFETY_STOP` in jobhunter/hn_hiring.py', (f'{hn_hiring.CANDIDATE_SAFETY_STOP:,}', '1,500')),
    row('Limits', 'Hacker News comment length', f'{hn_hiring.MAX_COMMENT_CHARS:,} characters', 'Longer comments are counted but not read.', '', 'Low', ASK, '`MAX_COMMENT_CHARS`', (f'{hn_hiring.MAX_COMMENT_CHARS:,}', '20,000')),
    row('Limits', 'Newsletter editions read', str(newsletter.MAX_ENTRIES), 'The first entries of the feed (newest first).', '', 'Low', ASK, '`MAX_ENTRIES` in jobhunter/newsletter.py', (newsletter.MAX_ENTRIES, 12)),
    row('Limits', 'Gmail extractions per run', f'{gmail_alerts.EXTRACTION_SAFETY_STOP:,} (Gmail is not live yet)', 'Safety stop.', '', 'Low', ASK, '`EXTRACTION_SAFETY_STOP` in jobhunter/gmail_alerts.py', (f'{gmail_alerts.EXTRACTION_SAFETY_STOP:,}', '1,000')),
    row('Rules', 'A rejected fact holds its post', 'The post is read again next run', 'If a fact is rejected, the post it came from is not marked read.', 'Not adjustable.', 'Low', CODE, 'jobhunter/post_facts.py'),
    row('Rules', 'An unread item that leaves the window', 'Cleared and reported', 'The run says how many were dropped.', 'Not adjustable.', 'Low', CODE, 'jobhunter/ai_queue.py'),
    row('Rules', 'Reasons a fact is rejected (shown in `trace:` lines)', ', '.join(sorted({r.split(':')[0] for r in post_facts.REASONS})), 'Fixed words only; never post text.', 'Not adjustable.', 'Low', CODE, '`REASONS` in jobhunter/post_facts.py'),
]

# ------------------------------------------------------------------------------------------------ 9 Sheet
sheet = [
    row('Writing', 'Jobs per writing batch', str(sheet_records.JOB_BATCH_SIZE), 'A bigger run is split into numbered batches. Not a limit on jobs delivered.', '', 'Low', ASK, '`JOB_BATCH_SIZE` in jobhunter/sheet_records.py', (sheet_records.JOB_BATCH_SIZE, 150)),
    row('Writing', 'Pause between batches', f'{sheets_sync.BATCH_PAUSE_SECONDS:.0f} seconds', 'Keeps under Google\'s per-minute quota.', 'Shorter risks Google quota errors.', 'Medium', ASK, '`BATCH_PAUSE_SECONDS` in scripts/sheets_sync.py (0 to 60 allowed)', (f'{sheets_sync.BATCH_PAUSE_SECONDS:.0f}', '45')),
    row('Writing', 'Writes per request', 'up to 100', 'Also kept near 1 MB.', '', 'Low', CODE, '`--chunk-size` in scripts/sheets_sync.py'),
    row('Writing', 'Retries on a temporary Google error', '3 attempts; waits up to 60 seconds; a quota error waits 20 then 40 seconds', 'Protects against quota errors.', '', 'Low', CODE, '`_retry` in jobhunter/sheets.py'),
    row('Safety', 'Duplicates', 'Never added', 'A job already in the Sheet is recognised by its Job ID and not added again. Its program-written columns may be refreshed.', 'Not adjustable.', 'Low', CODE, '`plan_jobs` in jobhunter/sheet_records.py'),
    row('Safety', 'Your columns', 'Status, Notes, My rating, Date found are never touched', 'The program never overwrites what you write there.', 'Not adjustable.', 'Low', CODE, 'jobhunter/sheet_records.py'),
    row('Safety', 'New row defaults', 'Status = New; Fit, Next step, Notes, My rating blank', 'Fit and Next step are not built yet (the plan scores fit 0 to 100 later).', '', 'Low', CODE, '`to_row` in jobhunter/postings.py'),
    row('Safety', 'Brief description', 'First 300 characters of the posting', 'An exact excerpt, never rewritten.', '', 'Low', CODE, '`to_row`'),
    row('Safety', 'Only one writer at a time', 'A lock tab named _JobHunterLock', 'Stops two runs writing together.', 'Not adjustable.', 'Low', CODE, '`LOCK_TITLE` in jobhunter/sheet_io.py'),
    row('Columns', 'Jobs tab columns', ' | '.join(sheet_records.JOB_HEADERS), 'The columns the program writes.', 'Adding a column needs a code change.', 'Medium', ASK, '`JOB_HEADERS`'),
    row('File sizes', 'Hand-off file between steps', f'{artifacts.DEFAULT_MAX_BYTES // (1024 * 1024)} MiB (final writer input {artifacts.SYNC_MAX_BYTES // (1024 * 1024)} MiB)', 'Safety limit on the files passed between steps.', '', 'Low', ASK, '`DEFAULT_MAX_BYTES`, `SYNC_MAX_BYTES` in jobhunter/artifacts.py', (f'{artifacts.DEFAULT_MAX_BYTES // (1024 * 1024)} MiB (final writer input {artifacts.SYNC_MAX_BYTES // (1024 * 1024)} MiB)', '5 MiB')),
]

# ------------------------------------------------------------------------------------------------ 10 Order and duplicates
order = [
    row('Rank column', 'Rank (prelim)', '1 = AI company, 2 = big tech, 3 = other', 'Taken from the company\'s tag in sources/v0_sources.yaml. It is a first guess, not a score. Most rows show 3 because most companies are tagged "other".', 'Change a company\'s tag in the file.', 'Low', EDIT_FILE, 'sources/v0_sources.yaml, `to_row`'),
    row('Order of delivery', 'Which jobs go first', 'Product-manager jobs with AI words first, then other product managers, then Chief of Staff, leadership programs, strategy, entrepreneurship, project management', 'Matters when a run stops partway; the best jobs are delivered first. Within that, AI companies, then big tech, then others.', 'Tell Claude.', 'Low', ASK, '`collection_title_priority`, `collection_priority`'),
    row('Duplicates', 'When two sources list the same job', 'Merged only when the employer link or requisition number is identical', 'The company\'s own board wins over a job site; the row says which other sources also listed it and when each first saw it.', 'Not adjustable.', 'Low', CODE, '`dedupe` in jobhunter/postings.py'),
    row('Duplicates', 'Same company and title, different link', 'NOT merged; flagged "possible duplicate"', 'The program never merges by name alone, so no real job is lost.', 'Not adjustable.', 'Low', CODE, '`dedupe`'),
    row('Duplicates', 'Source priority when merging', 'Company boards 0, page sources 1, everything else 2', 'Lower number wins.', '', 'Low', CODE, '`SOURCE_PRIORITY`'),
]

# ------------------------------------------------------------------------------------------------ 11 Checks
chk = [
    row('Blank-cell checker (scripts.field_audit)', 'Columns that must never be blank', ', '.join(field_audit.ALWAYS), 'A blank in any of these is flagged for every source.', 'Tell Claude.', 'Low', ASK, '`ALWAYS` in scripts/field_audit.py'),
]
for fam_name, cols in field_audit.EXPECTED.items():
    for col, minimum in cols.items():
        chk.append(row('Blank-cell checker (scripts.field_audit)', f'{fam_name}: {col} filled at least', f'{int(minimum * 100)}%',
                       'Measured on real boards on October 21 and then lowered. A source below this is flagged as a gap in our reader.', 'Tell Claude.', 'Low', ASK, '`EXPECTED` in scripts/field_audit.py'))
chk.append(row('Blank-cell checker (scripts.field_audit)', 'Pay expected in CA / NY / CO / WA places', f'at least {int(field_audit.PAY_TRANSPARENCY_MIN * 100)}%', 'Employers must publish a pay range in these places, so very few blanks are expected.', 'Tell Claude.', 'Low', ASK, '`PAY_TRANSPARENCY_MIN`', (int(field_audit.PAY_TRANSPARENCY_MIN * 100), 50)))
chk.append(row('Blank-cell checker (scripts.field_audit)', 'What it prints', 'Counts and fixed words only', 'Never a cell value. A Source it does not know is shown as "unknown".', 'Not adjustable.', 'Low', CODE, 'scripts/field_audit.py'))

# ------------------------------------------------------------------------------------------------ 12 Secrets
sec = [
    row('Names only (never paste a value)', 'X_AUTH_TOKEN and X_CT0', 'the two X cookies', 'For the dedicated X account.', 'You re-copy a cookie only if X reports it logged out.', 'High', YOU_SHEET.replace('Sheet', 'environment settings'), 'JobHunterEnv settings'),
    row('Names only (never paste a value)', 'LINKEDIN_LI_AT (or LI_AT)', 'the LinkedIn cookie', 'LinkedIn is on hold (A18); remove this setting until you decide.', '', 'High', 'You, in the environment settings', 'JobHunterEnv settings'),
    row('Names only (never paste a value)', 'JSEARCH_API_KEY and JOOBLE_API_KEY', 'the two keyed job services', 'Without them those two sources show "needs setup".', '', 'Medium', 'You, in the environment settings', 'JobHunterEnv settings'),
    row('Names only (never paste a value)', 'JOBHUNTER_SPREADSHEET_ID', 'which Google Sheet is written', 'A copy has a different ID; a backup copy does not redirect the run.', '', 'High', 'You, in the environment settings', 'JobHunterEnv settings'),
    row('Names only (never paste a value)', 'JOBHUNTER_GOOGLE_AUTH_MODE', 'how the program signs in to Google', '', '', 'High', 'You, in the environment settings', 'JobHunterEnv settings'),
    row('Names only (never paste a value)', 'WAAS_SESSION_COOKIE', 'reserved; no code reads it today', 'For a future logged-in Work at a Startup reader (task B10).', '', 'Low', 'You', 'JobHunterEnv settings'),
]

SHEETS += [
    ('1 Runs and schedule', 'How far back a run looks and when it runs.', runs),
    ('2 Which jobs count', 'The job titles the program collects, and the ones it always throws out.', roles),
    ('3 MBA 2027 rule', 'The rule you asked for on October 21: only roles meant for MBA graduates of 2027.', mba),
    ('4 Places', 'Which locations are accepted, flagged or dropped.', places),
    ('5 Pay', 'Salary floors, where pay comes from, and when pay is treated as unresolved.', pay),
    ('6 Sources', 'Every place jobs come from, plus the politeness and safety limits for reading them.', src),
    ('7 X and LinkedIn', 'The searches and the strict limits that protect the accounts.', social),
    ('8 AI reading step', 'What the AI reads, what it must quote, and the size limits.', ai),
    ('9 Google Sheet', 'How and how gently results are written to your Sheet.', sheet),
    ('10 Order and duplicates', 'Rank, delivery order and how duplicates are handled.', order),
    ('11 Checks', 'The blank-cell checker thresholds.', chk),
    ('12 Connections', 'The names of the secrets and connections (never their values).', sec),
]

# ------------------------------------------------------------------------------------------------ 13 Try it (live)
def collected(title, text, location='United States', salary='USD 150,000 per year'):
    posting = postings.Posting('x:1', 'x', 'Acme', title, location, text, 'https://acme.example/1', '2026-10-21T00:00:00+00:00', salary=salary)
    return postings.collection_reason(posting) or 'COLLECTED'


try_roles = ['Product Manager, Billing', 'Senior Product Manager', 'Group Product Manager', 'Chief of Staff', 'MBA Leadership Development Program',
             'Strategy Manager', 'Entrepreneur in Residence', 'Project Manager', 'Forward-Deployed AI Strategist', 'Forward-Deployed Engineer - AI Strategy',
             'Product Marketing Manager', 'Product Manager Intern', 'Software Engineer', 'Program Manager', 'Product Managers']
try_places = [('United States', False), ('San Francisco, CA', False), ('Remote', False), ('Remote - US', True), ('Colombia', False),
              ('Bogotá, CO', False), ('Brazil', False), ('Remote - Brazil', True), ('Sao Paulo, Brazil', False), ('London, UK', False),
              ('Berlin, Germany', False), ('Toronto, Canada', False)]
try_mba = [
    'This role is open to MBA students graduating in spring 2027.', 'We are recruiting MBA candidates who graduate in May 2027.',
    'MBA students graduating in May 2027 are eligible to apply.', 'Open to MBA students graduating in May 2026 or May 2027.',
    'Join our 2027 MBA Leadership Development Program.', 'Experience is not required, open to MBA students graduating in May 2027.',
    'MBA preferred.', 'MBA or equivalent professional experience.', 'Bachelor\'s degree required; MBA or advanced degree preferred.',
    'Build learning products for MBA students graduating in spring 2027.', 'We are hiring a PM to build products for MBA students graduating in spring 2027.',
    'This role is not open to MBA students graduating in spring 2027.', 'Open to MBA students graduating in spring 2028 only, with applications opening in 2027.',
    'Open to MBA students graduating in spring 2026.', 'New Grad (2027 Start). You will graduate in Spring 2027 with a bachelor\'s degree.',
    'Education: Master of Business Administration (MBA) or Juris Doctor (JD) degree.', 'A plain product manager job with no mention of MBA.',
]
try_salary_texts = [
    'The salary range is $160,000 - $200,000 per year.', 'Estimated base salary $161,000 - $221,000.', 'The annual base pay range is $160K to $200K plus bonus.',
    'The annual base salary range is $90,000 - $120,000 CAD.', 'Annual base salary range (CAD): $90,000-$120,000 per year.', 'Total compensation is $100,000 - $120,000 per year.',
    'The monthly salary range is $40,000 - $50,000.', 'Salary range: $90,000 - $120,000 including bonus and equity.', 'The salary range is $40,000 - $50,000, paid monthly.',
    'Target bonus of $20,000 - $40,000 on top of salary.', 'Hourly pay: $40 - $60 per hour.', 'We offer a $5,000 - $10,000 relocation allowance and a competitive salary.',
]
try_gh = [('Annual Salary:', 'USD', 30500000, 38500000), ('Zone 1 Pay Range', 'USD', 12800000, 17600000), ('Monthly Salary', 'USD', 1000000, 1500000),
          ('Annual Bonus', 'USD', 1000000, 1500000), ('Annual Total Compensation', 'USD', 1000000, 1500000), ('Hourly Rate:', 'USD', 4000, 6000),
          ('Canada Pay Range', 'CAD', 8500000, 10000000), ('OTE Range', 'USD', 9000000, 12000000)]
try_floor = [('USD 140,000 per year', 'United States'), ('USD 139,999 per year', 'United States'), ('USD 120,000 - 145,000 per year', 'United States'),
             ('USD 70,000 per year', 'Colombia'), ('USD 69,999 per year', 'Colombia'), ('USD 100,000 per year', 'Remote'), ('USD 60,000 per year', 'Remote'),
             ('', 'United States'), ('EUR 150,000 per year', 'United States'), ('$190k-$220k', 'United States')]

tries = []
tries.append(('A. Job titles', 'Title', 'What the program does', [(t, postings.role_family(t) or 'DROPPED (not a collected role)') for t in try_roles]))
tries.append(('B. Places', 'Place (remote?)', 'What the program does', [
    (f'{p}  ({"remote" if r else "not marked remote"})', {None: 'DROPPED (clearly outside)', 'US': 'US: pay floor $140,000', 'LATAM': 'Latin America: pay floor $70,000',
                                                         'unresolved': 'KEPT and flagged (unclear place)'}[postings.collection_region(p, remote=r)]) for p, r in try_places]))
tries.append(('C. MBA 2027 rule', 'Sentence in a job posting', 'What the program does', [
    (t, {'mba': 'COLLECTED', 'other_year': 'DROPPED: another class year', 'class_only': 'DROPPED: 2027 class but no MBA', '': 'DROPPED: not for MBA 2027'}[postings.mba_class_evidence('Product Manager', t)[0]]) for t in try_mba]))
tries.append(('D. Pay written in a posting', 'Sentence', 'Salary cell the program writes', [
    (t, postings.salary_from_text(t) or '(blank = unresolved)') for t in try_salary_texts]))
tries.append(('E. Greenhouse pay labels', 'Label, currency, amount', 'Salary cell the program writes', [
    (f'{label} / {cur} / {lo // 100:,} - {hi // 100:,}', postings.greenhouse_pay([{'title': label, 'currency_type': cur, 'min_cents': lo, 'max_cents': hi}])) for label, cur, lo, hi in try_gh]))
tries.append(('F. Pay against the floor', 'Pay text / place', 'Result', [
    (f'{s or "(no pay given)"}  /  {pl}', '{} (floor {:,})'.format(*postings.salary_preference(postings.Posting('x:1', 'x', 'A', 'Product Manager', pl, 't', 'https://a.example/1', '2026-10-21T00:00:00+00:00', salary=s)))) for s, pl in try_floor]))

# ------------------------------------------------------------------------------------------------ write workbook
wb = Workbook()
ws0 = wb.active
ws0.title = 'Read me'
ws0.column_dimensions['A'].width = 30
ws0.column_dimensions['B'].width = 100
ws0['A1'] = 'JobHunter: every setting, in plain language'
ws0['A1'].font = Font(name=F, size=14, bold=True)
ws0['A2'] = f'Generated {TODAY} from the real code (branch claude/jobhunter-continuation-d35nmm). Numbers that exist as constants were read from the code and compared with the text; the build stops if they disagree.'
ws0['A2'].font = Font(name=F, size=10, italic=True)
ws0['A2'].alignment = WRAP
ws0.merge_cells('A2:B2')
ws0.row_dimensions[2].height = 32
guide = [
    ('What this file is', 'One place to see everything the platform decides with: how far back it looks, which job titles and places count, the MBA 2027 rule, pay floors, every source, the limits that protect the X and LinkedIn accounts, and how it writes to your Sheet.'),
    ('How to read a sheet', 'Each row is one setting. "Today" is the current value. "In plain words" says what it does. "If you change it" says what moves. "Risk": Low = safe, Medium = changes which jobs you get, High = could get an account restricted or hurt the Sheet.'),
    ('How to change something', 'In the yellow YOUR DECISION column choose Keep or Change, and in the last column write the new value (for example "daily look-back: 4 days"). Then tell Claude "parameters are in". NOTHING in this file changes the program by itself.'),
    ('Who changes what', '"You, in a text file": the search wording and the company/site lists are plain text files you can edit yourself. "Ask Claude": the number is inside the program; Claude changes it, runs the tests and opens a PR, and Codex reviews it before it is merged. "Fixed in the program": a rule, not a number; ask Claude if you want it different.'),
    ('The "Try it" sheet', 'Sheet "13 Try it (live)" runs example titles, places, sentences and pay texts through the REAL program and shows what it does. Use it to check a rule by example. If an example surprises you, write it in the yellow cell: that is the most useful thing you can tell Claude.'),
    ('Safety rule above all', 'LinkedIn and X can restrict an account that looks like a robot. The program reads each once per New York day with random 3 to 9 second pauses and never types, likes, follows or messages. Raising any X or LinkedIn number raises that risk; there is no guarantee an account stays safe.'),
    ('Open decisions that touch these settings', 'A13 plural titles, A17 pay like $190k-$220k in posts, A23 new-grad 2027 roles without an MBA, A24 roles outside the title list that are clearly for MBA 2027, A25 where MBA 2027 jobs come from, A18 LinkedIn. All are in the questions Excel and docs/START_HERE.md.'),
    ('If this file and the code disagree', 'The code wins. Tell Claude and the file is regenerated.'),
]
for i, (a, b) in enumerate(guide, 4):
    ws0.cell(row=i, column=1, value=a).font = BB
    c = ws0.cell(row=i, column=2, value=b)
    c.font = B
    c.alignment = WRAP
    ws0.cell(row=i, column=1).alignment = WRAP
    ws0.row_dimensions[i].height = 46 if len(b) > 190 else 32
r0 = 4 + len(guide) + 1
ws0.cell(row=r0, column=1, value='Progress').font = BB
ws0.cell(row=r0 + 1, column=1, value='Settings marked Keep or Change').font = B
ws0.cell(row=r0 + 2, column=1, value='Settings you want changed').font = B
ws0.cell(row=r0 + 3, column=1, value='Settings in this file').font = B
ws0.cell(row=r0 + 4, column=1, value='Checks against the code that passed').font = B

total, decided_terms, change_terms = 0, [], []
for title, intro, rows in SHEETS:
    ws = wb.create_sheet(title)
    ws['A1'] = title[title.index(' ') + 1:]
    ws['A1'].font = Font(name=F, size=14, bold=True)
    ws['A2'] = intro
    ws['A2'].font = Font(name=F, size=10, italic=True)
    for c, h in enumerate(COLS, 1):
        cell = ws.cell(row=4, column=c, value=h)
        cell.font, cell.fill, cell.border = H, HF, BOX
        cell.alignment = Alignment(wrap_text=True, vertical='center')
    for r, data in enumerate(rows, 5):
        for c, v in enumerate(data, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font = BB if c == 2 else B
            cell.alignment, cell.border = WRAP, BOX
        ws.cell(row=r, column=6).fill = RISK.get(data[5], PatternFill())
        for c in (10, 11):
            cell = ws.cell(row=r, column=c)
            cell.fill, cell.border, cell.font, cell.alignment = YEL, BOX, B, WRAP
        longest = max(len(str(data[2])) / 26, len(str(data[3])) / 56, len(str(data[4])) / 44, len(str(data[1])) / 30, 1)
        ws.row_dimensions[r].height = min(max(30, 13.5 * (int(longest) + 1)), 190)
    for c, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[get_column_letter(c)].width = w
    ws.freeze_panes = 'C5'
    last = 4 + len(rows)
    dv = DataValidation(type='list', formula1='"Keep,Change"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f'J5:J{last}')
    total += len(rows)
    decided_terms.append(f"COUNTA('{title}'!J5:J{last})")
    change_terms.append(f"COUNTIF('{title}'!J5:J{last},\"Change\")")

ws0.cell(row=r0 + 1, column=2, value='=' + '+'.join(decided_terms))
ws0.cell(row=r0 + 2, column=2, value='=' + '+'.join(change_terms))
ws0.cell(row=r0 + 3, column=2, value=total)
ws0.cell(row=r0 + 4, column=2, value=len(CHECKS))
for k in range(1, 5):
    ws0.cell(row=r0 + k, column=2).font = B
    ws0.cell(row=r0 + k, column=2).alignment = Alignment(horizontal='left')

wt = wb.create_sheet('13 Try it (live)')
wt['A1'] = 'Try it: examples run through the real program'
wt['A1'].font = Font(name=F, size=14, bold=True)
wt['A2'] = f'Computed from the code on {TODAY}. If a result surprises you, write what you expected in the yellow cell.'
wt['A2'].font = Font(name=F, size=10, italic=True)
wt.column_dimensions['A'].width = 78
wt.column_dimensions['B'].width = 46
wt.column_dimensions['C'].width = 40
r = 4
for heading, c1, c2, items in tries:
    wt.cell(row=r, column=1, value=heading).font = Font(name=F, size=11, bold=True)
    r += 1
    for c, h in enumerate((c1, c2, 'What you expected (optional)'), 1):
        cell = wt.cell(row=r, column=c, value=h)
        cell.font, cell.fill, cell.border = H, HF, BOX
    r += 1
    for a, b in items:
        for c, v in enumerate((a, b, None), 1):
            cell = wt.cell(row=r, column=c, value=v)
            cell.font, cell.alignment, cell.border = B, WRAP, BOX
        wt.cell(row=r, column=3).fill = YEL
        wt.row_dimensions[r].height = 28 if len(a) > 70 else 18
        r += 1
    r += 1

wb.save(OUT)
print('saved', OUT, 'settings:', total, 'code checks passed:', len(CHECKS))
